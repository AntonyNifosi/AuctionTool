"""
Gestionnaire de mise à jour en arrière-plan
"""
import threading
import time
import queue
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
import traceback
import json
import os

from .blizzard_api import get_api, BlizzardAPIError
from .data_manager import get_data_manager

class UpdateManager:
    """
    Gère les mises à jour de la base de données en arrière-plan.
    Pattern Singleton via st.cache_resource dans l'app principale.
    """
    
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._stop_event = threading.Event()
        
        # État observable
        self.progress = 0.0
        self.status_message = ""
        self.last_update_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.total_steps = 0
        self.current_step = 0
        
    def is_running(self) -> bool:
        return self._is_running and self._thread and self._thread.is_alive()
        
    def start_background_update(self, force: bool = False, priority_realm_id: int = None):
        """Lance la mise à jour en arrière-plan si elle ne tourne pas déjà"""
        if self.is_running():
            return
            
        self._stop_event.clear()
        self._is_running = True
        self.progress = 0.0
        self.last_error = None
        self.status_message = "Démarrage de la mise à jour..."
        
        self._thread = threading.Thread(target=self._run_process, args=(priority_realm_id,))
        self._thread.daemon = True # Le thread s'arrête si le programme principal s'arrête
        self._thread.start()
        
    def stop_update(self):
        """Demande l'arrêt de la mise à jour"""
        if self.is_running():
            self._stop_event.set()
    
    def _run_process(self, priority_realm_id: int = None):
        """Processus principal de mise à jour"""
        try:
            api = get_api()
            dm = get_data_manager()
            
            self.status_message = "Chargement du catalogue d'items..."
            self.progress = 0.05
            
            # === PHASE 1: CATALOGUE SYNC (housing, pets, recipes) ===
            
            # 1a. Charger/Mettre à jour les items de housing
            housing_items = self._sync_housing_items(api, dm)
            if self._stop_event.is_set(): return
            housing_item_ids = {item["item_id"] for item in housing_items}
            
            # 1b. Sync pets (doit être fait AVANT le scan pour avoir les pet_ids)
            if dm.should_resync_pets(max_age_days=30):
                self.status_message = "Synchronisation des pets..."
                self._sync_pets(api, dm)
                if self._stop_event.is_set(): return
            
            # 1c. Sync recipes (AVANT le scan pour que les reagent_ids soient trackés)
            if dm.should_resync_recipes(max_age_days=30):
                self.status_message = "Synchronisation des recettes de craft..."
                self._sync_recipes(api, dm, housing_item_ids)
                if self._stop_event.is_set(): return
            
            # 1d. Fetch ALL missing icons (housing items + pets) - pas de limite
            self.status_message = "Récupération des icônes manquantes..."
            self._fetch_icons(api, dm, limit=None)
            self._fetch_pet_icons(api, dm, limit=None)
            if self._stop_event.is_set(): return

            # === PHASE 2: PRICE SCAN ===
            
            # Construire la liste de tracking APRÈS le sync des recettes
            reagent_ids = dm.get_all_reagent_ids()
            target_item_ids = housing_item_ids | reagent_ids  # Union des deux sets
            print(f"Tracking {len(housing_item_ids)} housing items + {len(reagent_ids)} reagents = {len(target_item_ids)} total")
            
            self.status_message = "Récupération de la liste des serveurs..."
            self.progress = 0.1
            
            # 2. Charger les serveurs
            realms = api.get_all_realms_with_names()
            if self._stop_event.is_set(): return
            
            # Reordonner si priorité
            if priority_realm_id:
                realms.sort(key=lambda r: 0 if r["id"] == priority_realm_id else 1)
            
            total_realms = len(realms)
            self.total_steps = total_realms
            
            # 3. Scanner chaque serveur
            for i, realm in enumerate(realms):
                if self._stop_event.is_set(): break
                
                realm_name = realm["name"]
                realm_id = realm["id"]
                
                self.status_message = f"Scan: {realm_name}"
                # Progression de 10% à 100%
                self.progress = 0.1 + (0.9 * (i / total_realms))
                self.current_step = i + 1
                
                # Log progress to console for standalone scripts
                print(f"[{i+1}/{total_realms}] Scan: {realm_name}")
                
                try:
                    # Update realm info
                    dm.save_realm(
                        realm["id"], 
                        realm["name"], 
                        population=realm.get("population"),
                        region=realm.get("region")
                    )
                    
                    # Fetch auctions
                    all_auctions = api.get_auctions(realm_id)
                    
                    # Detect sales and cancels (Auction Diff)
                    item_sales, pet_sales, item_cancels, pet_cancels = self._detect_sales(realm_id, all_auctions)
                    if item_sales:
                        print(f"Detected sales for {len(item_sales)} items")
                    if item_cancels:
                        print(f"Detected cancels for {len(item_cancels)} items")
                    
                    # Process housing item auctions
                    self._process_auctions(realm_id, all_auctions, target_item_ids, dm, item_sales, item_cancels)
                    
                    # Process pet auctions
                    pet_ids = dm.get_pet_ids()
                    if pet_ids:
                        self._process_pet_auctions(realm_id, all_auctions, pet_ids, dm, pet_sales, pet_cancels)
                    
                except Exception as e:
                    print(f"Error scanning {realm_name}: {e}")
                    # On continue même si erreur sur un serveur
                    continue
            
            # 3.5. Fetch commodities (regional prices for materials)
            self.status_message = "Récupération des prix des matériaux..."
            try:
                commodities = api.get_commodities()
                print(f"Got {len(commodities)} commodities")
                self._process_auctions(0, commodities, reagent_ids, dm)  # realm_id=0 for regional
            except Exception as e:
                print(f"Error fetching commodities: {e}")

            # 4. Cleanup old data (keep only 7 days)
            self.status_message = "Nettoyage des anciennes données..."
            dm.cleanup_old_data(days=7)

            self.progress = 1.0
            self.status_message = "Mise à jour terminée avec succès !"
            self.last_update_time = datetime.now()
            
        except Exception as e:
            self.last_error = str(e)
            self.status_message = f"Erreur: {str(e)}"
            traceback.print_exc()
        finally:
            self._is_running = False

    def _fetch_icons(self, api, dm, limit=100):
        """Récupère les icônes manquantes. limit=None pour tout récupérer."""
        items_without_icons = dm.get_items_without_icons(limit=limit or 999999)
        
        if items_without_icons:
            print(f"Fetching icons for {len(items_without_icons)} items...")
        
        for item in items_without_icons:
            if self._stop_event.is_set(): return
            
            item_id = item["item_id"]
            try:
                media_data = api.get_item_media(item_id)
                assets = media_data.get("assets", [])
                icon_url = None
                
                for asset in assets:
                    if asset.get("key") == "icon":
                        icon_url = asset.get("value")
                        break
                
                if icon_url:
                    dm.update_icon_url(item_id, icon_url)
                else:
                    dm.update_icon_url(item_id, "NONE")
            except Exception:
                dm.update_icon_url(item_id, "NONE") # Eviter de boucler infini sur erreurs

    def _sync_housing_items(self, api, dm) -> List[Dict]:
        """Synchronise la liste des items de housing"""
        # Vérifier le cache existant
        existing_items = dm.get_housing_items()
        
        # Re-fetch si pas assez d'items ou si les items n'ont pas été rafraîchis récemment (30 jours)
        is_stale = False
        if existing_items:
            try:
                latest_update = max(
                    datetime.fromisoformat(str(i.get('updated_at', '')).replace('Z', '+00:00'))
                    for i in existing_items if i.get('updated_at')
                )
                if latest_update.tzinfo:
                    latest_update = latest_update.replace(tzinfo=None)
                is_stale = (datetime.now() - latest_update).days >= 30
            except (ValueError, TypeError):
                is_stale = True
        
        is_incomplete = len(existing_items) < 1000 or is_stale
        
        if not is_incomplete:
            return existing_items
            
        # Sinon on fetch
        try:
            housing_items = api.search_housing_items()
            for item in housing_items:
                data = item.get("data", {})
                item_id = data.get("id")
                
                name_data = data.get("name", {})
                if isinstance(name_data, dict):
                    name = name_data.get("fr_FR") or name_data.get("en_US") or f"Item {item_id}"
                else:
                    name = str(name_data)
                
                if item_id:
                    dm.save_housing_item(item_id, name, category="Housing")
                    
            return dm.get_housing_items()
        except Exception as e:
            if existing_items:
                return existing_items
            raise e

    def _process_auctions(self, realm_id: int, auctions: List[Dict], target_item_ids: set, dm, item_sales: Dict[int, int] = None, item_cancels: Dict[int, int] = None):
        """Traite les enchères pour un serveur"""
        item_stats = {}
        item_sales = item_sales or {}
        item_cancels = item_cancels or {}
        
        # 1. Process current auctions
        for auction in auctions:
            item_id = auction.get("item", {}).get("id")
            if item_id in target_item_ids:
                if item_id not in item_stats:
                    item_stats[item_id] = {"prices": [], "qty": 0}
                
                price = auction.get("buyout") or auction.get("unit_price", 0)
                qty = auction.get("quantity", 1)
                
                if price > 0:
                    item_stats[item_id]["prices"].append(price)
                    item_stats[item_id]["qty"] += qty

        # 2. Add sales data (even if no current auctions)
        for item_id, sales_count in item_sales.items():
            if item_id in target_item_ids:
                if item_id not in item_stats:
                    item_stats[item_id] = {"prices": [], "qty": 0} # No current prices
                
                # Store sales count in stats
                item_stats[item_id]["sales"] = sales_count
        
        # 2.5. Add cancels data
        for item_id, cancel_count in item_cancels.items():
            if item_id in target_item_ids:
                if item_id not in item_stats:
                    item_stats[item_id] = {"prices": [], "qty": 0}
                item_stats[item_id]["cancels"] = cancel_count
        
        # Batch insert logic could go here, but for now loop is fine with WAL
        # Prepare batch data
        batch_data = []
        for item_id, stats in item_stats.items():
            prices = stats["prices"]
            estimated_sales = stats.get("sales", 0)
            estimated_cancels = stats.get("cancels", 0)
            
            # We record if we have prices OR if we have sales OR cancels
            if prices or estimated_sales > 0 or estimated_cancels > 0:
                if prices:
                    min_price = min(prices)
                    avg_price = sum(prices) / len(prices)
                    total_qty = stats["qty"]
                    auction_count = len(prices)
                else:
                    # Case: Sales but no current listings
                    # We record 0 price/qty to indicate "Out of Stock" but "Sold"
                    # Or we should fallback to previous price? 
                    # For simplicity, 0 indicates no current market data.
                    min_price = 0
                    avg_price = 0
                    total_qty = 0
                    auction_count = 0
                
                batch_data.append((
                    item_id, realm_id, min_price, avg_price, 
                    total_qty, auction_count, estimated_sales, estimated_cancels
                ))
        
        # Batch insert
        if batch_data:
            dm.batch_record_price_data(batch_data)
    
    def _process_pet_auctions(self, realm_id: int, auctions: List[Dict], pet_ids: set, dm, pet_sales: Dict[int, int] = None, pet_cancels: Dict[int, int] = None):
        """Traite les enchères de pets pour un serveur"""
        pet_stats = {}
        pet_sales = pet_sales or {}
        pet_cancels = pet_cancels or {}
        
        for auction in auctions:
            # Les pets ont pet_species_id DANS l'objet item, pas à la racine
            item = auction.get("item", {})
            pet_species_id = item.get("pet_species_id")
            if pet_species_id and pet_species_id in pet_ids:
                if pet_species_id not in pet_stats:
                    pet_stats[pet_species_id] = {"prices": [], "qty": 0, "quality": None, "level": None}
                
                price = auction.get("buyout") or auction.get("unit_price", 0)
                quality = item.get("pet_quality_id")
                level = item.get("pet_level")
                
                if price > 0:
                    pet_stats[pet_species_id]["prices"].append(price)
                    pet_stats[pet_species_id]["qty"] += 1
                    # Garder la qualité/level du premier pet trouvé (on pourrait améliorer)
                    if pet_stats[pet_species_id]["quality"] is None:
                        pet_stats[pet_species_id]["quality"] = quality
                        pet_stats[pet_species_id]["level"] = level
        
        # Add sales for pets
        for pet_id, sales_count in pet_sales.items():
            if pet_id in pet_ids:
                if pet_id not in pet_stats:
                    pet_stats[pet_id] = {"prices": [], "qty": 0, "quality": None, "level": None}
                pet_stats[pet_id]["sales"] = sales_count
        
        # Add cancels for pets
        for pet_id, cancel_count in pet_cancels.items():
            if pet_id in pet_ids:
                if pet_id not in pet_stats:
                    pet_stats[pet_id] = {"prices": [], "qty": 0, "quality": None, "level": None}
                pet_stats[pet_id]["cancels"] = cancel_count
        
        # Enregistrer les prix des pets
        # Enregistrer les prix des pets en batch
        batch_data = []
        for pet_id, stats in pet_stats.items():
            prices = stats["prices"]
            estimated_sales = stats.get("sales", 0)
            estimated_cancels = stats.get("cancels", 0)
            
            if prices or estimated_sales > 0 or estimated_cancels > 0:
                if prices:
                    min_price = min(prices)
                    avg_price = sum(prices) / len(prices)
                    total_qty = stats["qty"]
                else:
                    min_price = 0
                    avg_price = 0
                    total_qty = 0
                
                # For pets without prices, we might lack quality/level if they are sales-only (no current listings)
                # We can leave them None or use reasonable defaults. DB allows NULL?
                # DataManager logic inserts them. Let's rely on DB schema.
                
                batch_data.append((
                    pet_id, realm_id, min_price, avg_price,
                    total_qty, stats["quality"], stats["level"], estimated_sales, estimated_cancels
                ))
        
        if batch_data:
            dm.batch_record_pet_prices(batch_data)

    def _sync_recipes(self, api, dm, housing_item_ids: set):
        """
        Synchronise les recettes de craft pour les items de housing.
        OPTIMISÉ: Ne scanne que les catégories "décoration" et matche par NOM.
        """
        # Professions de craft qui peuvent créer des items de housing
        CRAFTING_PROFESSION_IDS = [
            164,  # Blacksmithing
            165,  # Leatherworking
            171,  # Alchemy
            197,  # Tailoring
            202,  # Engineering
            333,  # Enchanting
            755,  # Jewelcrafting
            773,  # Inscription
        ]
        
        # Mots-clés pour identifier les catégories de décoration
        HOUSING_CATEGORY_KEYWORDS = ["décor", "decor", "housing", "maison", "ameublement", "furnish"]
        
        # Créer un dict nom -> item_id pour le matching
        housing_items = dm.get_housing_items()
        housing_name_to_id = {}
        for item in housing_items:
            name = item.get("name", "").lower().strip()
            if name:
                housing_name_to_id[name] = item["item_id"]
        
        print(f"Housing items loaded: {len(housing_name_to_id)} items")
        
        recipes_found = 0
        recipes_checked = 0
        
        for prof_idx, prof_id in enumerate(CRAFTING_PROFESSION_IDS):
            if self._stop_event.is_set():
                return
            
            try:
                profession = api.get_profession(prof_id)
                prof_name = profession.get("name", f"Profession {prof_id}")
                
                if isinstance(prof_name, dict):
                    prof_name = prof_name.get("fr_FR") or prof_name.get("en_US") or str(prof_id)
                
                self.status_message = f"Scan: {prof_name} ({prof_idx + 1}/{len(CRAFTING_PROFESSION_IDS)})"
                
                skill_tiers = profession.get("skill_tiers", [])
                
                for tier in skill_tiers:
                    if self._stop_event.is_set():
                        return
                    
                    tier_id = tier.get("id")
                    if not tier_id:
                        continue
                    
                    # Extraire le nom du tier (correspond à l'expansion)
                    tier_name = tier.get("name", "")
                    if isinstance(tier_name, dict):
                        tier_name = tier_name.get("fr_FR") or tier_name.get("en_US") or ""
                    
                    try:
                        tier_data = api.get_profession_skill_tier(prof_id, tier_id)
                        categories = tier_data.get("categories", [])
                        
                        for category in categories:
                            cat_name = category.get("name", "")
                            if isinstance(cat_name, dict):
                                cat_name = cat_name.get("fr_FR") or cat_name.get("en_US") or ""
                            
                            # Vérifier si c'est une catégorie de décoration
                            is_housing_category = any(
                                kw in cat_name.lower() 
                                for kw in HOUSING_CATEGORY_KEYWORDS
                            )
                            
                            if not is_housing_category:
                                continue
                            
                            # Scanner toutes les recettes de cette catégorie
                            recipes = category.get("recipes", [])
                            
                            for recipe_ref in recipes:
                                if self._stop_event.is_set():
                                    return
                                
                                recipe_id = recipe_ref.get("id")
                                if not recipe_id:
                                    continue
                                
                                recipes_checked += 1
                                
                                if recipes_checked % 10 == 0:
                                    self.status_message = f"{prof_name}: {recipes_checked} recettes déco ({recipes_found} matchées)"
                                
                                try:
                                    recipe = api.get_recipe(recipe_id)
                                    recipe_name = recipe.get("name", "")
                                    if isinstance(recipe_name, dict):
                                        recipe_name = recipe_name.get("fr_FR") or recipe_name.get("en_US") or ""
                                    
                                    # Essayer de trouver l'item correspondant par nom
                                    recipe_name_lower = recipe_name.lower().strip()
                                    crafted_item_id = housing_name_to_id.get(recipe_name_lower)
                                    
                                    if crafted_item_id:
                                        # Sauvegarder la recette
                                        dm.save_recipe(
                                            recipe_id=recipe_id,
                                            crafted_item_id=crafted_item_id,
                                            profession_id=prof_id,
                                            profession_name=prof_name,
                                            recipe_name=recipe_name,
                                            expansion=tier_name
                                        )
                                        
                                        # Sauvegarder les réactifs
                                        reagents_data = recipe.get("reagents", [])
                                        reagents = []
                                        for r in reagents_data:
                                            reagent_info = r.get("reagent", {})
                                            reagent_name = reagent_info.get("name", "")
                                            if isinstance(reagent_name, dict):
                                                reagent_name = reagent_name.get("fr_FR") or reagent_name.get("en_US") or ""
                                            
                                            reagents.append({
                                                "item_id": reagent_info.get("id"),
                                                "name": reagent_name,
                                                "quantity": r.get("quantity", 1)
                                            })
                                        
                                        # Sauvegarder les slots de craft modifié (catégories de composants)
                                        modified_slots = recipe.get("modified_crafting_slots", [])
                                        for slot in modified_slots:
                                            slot_type = slot.get("slot_type", {})
                                            slot_name = slot_type.get("name", "")
                                            if isinstance(slot_name, dict):
                                                slot_name = slot_name.get("fr_FR") or slot_name.get("en_US") or ""
                                            slot_id = slot_type.get("id")
                                            if slot_id and slot_name:
                                                # Essayer de résoudre le nom du slot en vrai item
                                                real_item_id = api.search_item_by_name(slot_name)
                                                if real_item_id:
                                                    reagents.append({
                                                        "item_id": real_item_id,
                                                        "name": slot_name,
                                                        "quantity": 1
                                                    })
                                                else:
                                                    # Fallback: ID négatif pour les slots non résolus
                                                    reagents.append({
                                                        "item_id": -slot_id,
                                                        "name": slot_name,
                                                        "quantity": 1
                                                    })
                                        
                                        if reagents:
                                            dm.save_recipe_reagents(recipe_id, reagents)
                                        
                                        recipes_found += 1
                                        print(f"[MATCHED] {recipe_name} -> Item {crafted_item_id}")
                                        
                                except Exception as e:
                                    continue
                                    
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"Error syncing profession {prof_id}: {e}")
                continue
        
        print(f"Recipe sync complete: {recipes_found} housing recipes matched ({recipes_checked} decoration recipes checked)")
    
    def _sync_pets(self, api, dm):
        """
        Synchronise la liste des pets depuis l'API Blizzard.
        Récupère tous les pets tradables avec leurs détails (source, type, icône).
        Optimisé via l'API Search pour récupérer les pets par lots de 100.
        """
        try:
            self.status_message = "Récupération de la liste des pets..."
            
            # search_pets retourne déjà les détails filtrés
            pets = api.search_pets()
            
            # Ne garder que les pets tradables
            tradable_pets = [p for p in pets if p.get("is_tradable")]
            total_tradable = len(tradable_pets)
            print(f"Found {total_tradable} tradable pets via Search API")
            
            synced_count = 0
            batch_pets = []
            BATCH_SIZE = 50
            
            for i, pet_data in enumerate(tradable_pets):
                if self._stop_event.is_set():
                    return
                
                if i % 100 == 0:
                    self.status_message = f"Synchronisation pets: {i}/{total_tradable}"
                
                batch_pets.append({
                    "pet_id": pet_data["id"],
                    "name": pet_data.get("name", ""),
                    "icon_url": pet_data.get("icon_url"),
                    "source": pet_data.get("source", ""),
                    "creature_type": pet_data.get("creature_type", ""),
                    "creature_id": pet_data.get("creature_id"),
                    "is_tradable": True
                })
                
                synced_count += 1
                
                # Sauvegarder par batch
                if len(batch_pets) >= BATCH_SIZE:
                    dm.save_pets_batch(batch_pets)
                    batch_pets = []
            
            # Sauvegarder le reste
            if batch_pets:
                dm.save_pets_batch(batch_pets)
            
            print(f"Pet sync complete: {synced_count} tradable pets synced")
            
        except Exception as e:
            print(f"Error syncing pets: {e}")
    
    def _fetch_pet_icons(self, api, dm, limit=100):
        """Récupère les icônes manquantes pour les pets. limit=None pour tout récupérer."""
        pets_without_icons = dm.get_pets_without_icons(limit=limit or 999999)
        
        if pets_without_icons:
            print(f"Fetching icons for {len(pets_without_icons)} pets...")
        
        for pet in pets_without_icons:
            if self._stop_event.is_set():
                return
            
            try:
                pet_id = pet["pet_id"]
                icon_data = api.get_pet_media(pet_id)
                
                if icon_data:
                    assets = icon_data.get("assets", [])
                    for asset in assets:
                        if asset.get("key") == "icon":
                            icon_url = asset.get("value")
                            dm.update_pet_icon(pet_id, icon_url)
                            break
            except Exception:
                continue

    def _get_snapshot_path(self, realm_id: int) -> str:
        """Retourne le chemin du fichier snapshot pour un serveur"""
        # On va chercher le dossier data via data_manager ou config si possible
        # Pour simplifier ici on utilise un dossier 'snapshots' dans le dossier courant backend/data
        # On peut inferer le path relative
        base_dir = os.path.dirname(__file__)
        data_dir = os.path.join(base_dir, "data", "snapshots")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, f"realm_{realm_id}.json")

    def _detect_sales(self, realm_id: int, current_auctions: List[Dict]) -> Tuple[Dict[int, int], Dict[int, int]]:
        """
        Compare les enchères actuelles avec le snapshot précédent pour détecter les ventes.
        Retourne (item_sales, pet_sales) où keys sont les IDs et values le nombre de ventes.
        """
        snapshot_path = self._get_snapshot_path(realm_id)
        
        # 1. Charger l'ancien snapshot
        old_auctions = {}
        if os.path.exists(snapshot_path):
            try:
                with open(snapshot_path, 'r') as f:
                    old_auctions = json.load(f)
            except Exception as e:
                print(f"Error loading snapshot for realm {realm_id}: {e}")
        
        # 2. Construire le nouveau snapshot
        # Format: auction_id -> {item_id, pet_species_id, time_left}
        new_snapshot = {}
        current_ids = set()
        
        for auc in current_auctions:
            auc_id = str(auc.get("id")) # JSON keys are strings
            item_id = auc.get("item", {}).get("id")
            pet_species_id = auc.get("item", {}).get("pet_species_id")
            time_left = auc.get("time_left")
            
            new_snapshot[auc_id] = {
                "i": item_id,
                "p": pet_species_id,
                "t": time_left
            }
            current_ids.add(auc_id)
            
        # 3. Sauvegarder le nouveau snapshot
        try:
            with open(snapshot_path, 'w') as f:
                json.dump(new_snapshot, f)
        except Exception as e:
            print(f"Error saving snapshot for realm {realm_id}: {e}")
            
        # 4. Détecter les disparitions (Old mais pas New)
        raw_item_sales = {}
        raw_pet_sales = {}
        
        # Détecter les apparitions (New mais pas Old)
        item_new_listings = {}
        pet_new_listings = {}
        
        # Helper pour compter les apparitions
        for auc_id in current_ids:
            if auc_id not in old_auctions:
                # C'est un nouvel item !
                data = new_snapshot[auc_id]
                item_id = data.get("i")
                if item_id:
                    item_new_listings[item_id] = item_new_listings.get(item_id, 0) + 1
                    
                pet_id = data.get("p")
                if pet_id:
                    pet_new_listings[pet_id] = pet_new_listings.get(pet_id, 0) + 1
        
        # Si pas d'ancien snapshot, on ne peut pas deviner les ventes
        if not old_auctions:
            return {}, {}
            
        for auc_id, data in old_auctions.items():
            if auc_id not in current_ids:
                # Disparu !
                time_left = data.get("t")
                
                # Si time_left n'était Pas SHORT (< 30min), on considère vendu (potentiellement)
                if time_left != "SHORT":
                    # Item Sale
                    item_id = data.get("i")
                    if item_id:
                        raw_item_sales[item_id] = raw_item_sales.get(item_id, 0) + 1
                        
                    # Pet Sale
                    pet_id = data.get("p")
                    if pet_id:
                        raw_pet_sales[pet_id] = raw_pet_sales.get(pet_id, 0) + 1
        
        # 5. Ajuster les ventes avec le "Churn" (Cancel/Relist)
        # Sales Réelles = Max(0, Disparus - Nouveaux)
        # Si 5 items disparaissent et 5 items apparaissent, on suppose 0 vente (juste du relisting)
        # NOUVEAU: Tracker les cancels = min(disparus, nouveaux) = paires cancel/relist
        
        final_item_sales = {}
        item_cancels = {}
        for item_id, count in raw_item_sales.items():
             new_count = item_new_listings.get(item_id, 0)
             adjusted_sales = max(0, count - new_count)
             cancel_count = min(count, new_count)  # Cancel/relist pairs
             if adjusted_sales > 0:
                 final_item_sales[item_id] = adjusted_sales
             if cancel_count > 0:
                 item_cancels[item_id] = cancel_count
                 
        final_pet_sales = {}
        pet_cancels = {}
        for pet_id, count in raw_pet_sales.items():
            new_count = pet_new_listings.get(pet_id, 0)
            adjusted_sales = max(0, count - new_count)
            cancel_count = min(count, new_count)  # Cancel/relist pairs
            if adjusted_sales > 0:
                final_pet_sales[pet_id] = adjusted_sales
            if cancel_count > 0:
                pet_cancels[pet_id] = cancel_count
                        
        return final_item_sales, final_pet_sales, item_cancels, pet_cancels
