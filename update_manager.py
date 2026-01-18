"""
Gestionnaire de mise à jour en arrière-plan
"""
import threading
import time
import queue
from datetime import datetime, timezone
from typing import Optional, List, Dict
import traceback

from blizzard_api import get_api, BlizzardAPIError
from data_manager import get_data_manager

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
            
            # 1. Charger/Mettre à jour les items de housing
            # Note: Cette logique est adaptée de app.py load_housing_items
            housing_items = self._sync_housing_items(api, dm)
            if self._stop_event.is_set(): return

            housing_item_ids = {item["item_id"] for item in housing_items}
            
            # Ajouter les IDs des réactifs pour tracker leurs prix
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
                    
                    # Process auctions
                    self._process_auctions(realm_id, all_auctions, target_item_ids, dm)
                    
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
            
            if self._stop_event.is_set(): return
            
            # 4. Sync recipes (only once, if not already done)
            if not dm.has_recipes_synced():
                self.status_message = "Synchronisation des recettes de craft..."
                self._sync_recipes(api, dm, housing_item_ids)
                if self._stop_event.is_set(): return
            
            # 5. Fetch missing icons
            self.status_message = "Récupération des icônes manquantes..."
            self._fetch_icons(api, dm)

            self.progress = 1.0
            self.status_message = "Mise à jour terminée avec succès !"
            self.last_update_time = datetime.now()
            
        except Exception as e:
            self.last_error = str(e)
            self.status_message = f"Erreur: {str(e)}"
            traceback.print_exc()
        finally:
            self._is_running = False

    def _fetch_icons(self, api, dm):
        """Récupère les icônes manquantes en arrière-plan"""
        items_without_icons = dm.get_items_without_icons(limit=100) # Par batch de 100 par scan
        
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
        
        # Logique simplifiée : si pas assez d'items ou force refresh demandé (logique implicite), on fetch
        # Ici on assume qu'on fetch si < 1000 items ou si on détecte qu'il manque des items récents
        has_new_items = any(i['item_id'] > 240000 for i in existing_items) if existing_items else False
        is_incomplete = len(existing_items) < 1000 or not has_new_items
        
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

    def _process_auctions(self, realm_id: int, auctions: List[Dict], target_item_ids: set, dm):
        """Traite les enchères pour un serveur"""
        item_stats = {}
        
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
        
        # Batch insert logic could go here, but for now loop is fine with WAL
        for item_id, stats in item_stats.items():
            prices = stats["prices"]
            if prices:
                min_price = min(prices)
                avg_price = sum(prices) / len(prices)
                total_qty = stats["qty"]
                auction_count = len(prices)
                
                dm.record_price_data(
                    item_id=item_id,
                    realm_id=realm_id,
                    min_price=min_price,
                    avg_price=avg_price,
                    total_quantity=total_qty,
                    auction_count=auction_count
                )

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
