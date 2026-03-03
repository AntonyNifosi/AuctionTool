"""
Module d'interaction avec l'API Blizzard Battle.net
Gère l'authentification OAuth2 et les appels aux endpoints WoW
"""
import requests
import time
from typing import Optional, Dict, List, Any
from .config import (
    BLIZZARD_CLIENT_ID,
    BLIZZARD_CLIENT_SECRET,
    API_BASE_URL,
    AUTH_URL,
    DYNAMIC_NAMESPACE,
    STATIC_NAMESPACE,
    DEFAULT_LOCALE
)


class BlizzardAPIError(Exception):
    """Exception personnalisée pour les erreurs de l'API Blizzard"""
    pass


class BlizzardAPI:
    """
    Client pour l'API Blizzard Battle.net
    Gère l'authentification et les appels aux endpoints WoW
    """
    
    def __init__(self):
        self.client_id = BLIZZARD_CLIENT_ID
        self.client_secret = BLIZZARD_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0
        
        if not self.client_id or not self.client_secret:
            raise BlizzardAPIError(
                "Credentials Blizzard manquants. "
                "Veuillez renseigner BLIZZARD_CLIENT_ID et BLIZZARD_CLIENT_SECRET dans le fichier .env"
            )
    
    def _get_access_token(self) -> str:
        """
        Obtient un access token via OAuth2 Client Credentials Grant
        """
        # Vérifier si le token actuel est encore valide
        if self.access_token and time.time() < self.token_expires_at - 60:
            return self.access_token
        
        try:
            response = requests.post(
                AUTH_URL,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data["access_token"]
            self.token_expires_at = time.time() + data.get("expires_in", 3600)
            
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            raise BlizzardAPIError(f"Erreur d'authentification: {str(e)}")
    
    def _make_request(self, endpoint: str, namespace: str, params: Optional[Dict] = None) -> Dict:
        """
        Effectue une requête authentifiée à l'API Blizzard
        """
        token = self._get_access_token()
        
        url = f"{API_BASE_URL}{endpoint}"
        
        # Utiliser le header Authorization au lieu du paramètre URL
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        request_params = {
            "namespace": namespace,
            "locale": DEFAULT_LOCALE
        }
        
        if params:
            request_params.update(params)
        
        try:
            response = requests.get(url, headers=headers, params=request_params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                return {}
            raise BlizzardAPIError(f"Erreur API ({response.status_code}): {str(e)}")
        except requests.exceptions.RequestException as e:
            raise BlizzardAPIError(f"Erreur de connexion: {str(e)}")
    
    def get_connected_realms_index(self) -> List[Dict]:
        """
        Récupère la liste des connected realms (serveurs)
        """
        data = self._make_request("/data/wow/connected-realm/index", DYNAMIC_NAMESPACE)
        realms = data.get("connected_realms", [])
        return realms
    
    def get_connected_realm_details(self, realm_id: int) -> Dict:
        """
        Récupère les détails d'un connected realm
        """
        return self._make_request(f"/data/wow/connected-realm/{realm_id}", DYNAMIC_NAMESPACE)
    
    def get_all_realms_with_names(self) -> List[Dict[str, Any]]:
        """
        Récupère tous les serveurs avec leurs noms en une seule requête via Search API
        """
        try:
            # Utiliser l'API Search pour récupérer tous les connected realms d'un coup
            # On demande l'ID et les real,s
            params = {
                "namespace": DYNAMIC_NAMESPACE,
                "_pageSize": 1000,  # Suffisant pour tous les serveurs EU/US
                "_page": 1,
                "status.type": "UP" # Optionnel: filtrer ceux qui sont up
            }
            
            # Note: l'endpoint de search pour connected-realm
            data = self._make_request("/data/wow/search/connected-realm", DYNAMIC_NAMESPACE, params)
            results = data.get("results", [])
            
            realms_list = []
            
            for item in results:
                data = item.get("data", {})
                realm_id = data.get("id")
                
                # Extraire la population (FULL, HIGH, MEDIUM, LOW, etc.)
                population_data = data.get("population", {})
                population_type = population_data.get("type", "UNKNOWN") if population_data else "UNKNOWN"
                
                realms_data = data.get("realms", [])
                realm_names = [r.get("name", {}).get(DEFAULT_LOCALE, "") for r in realms_data]
                
                # Extraire la locale (ex: "fr_FR", "en_GB", "ru_RU", etc.)
                # On prend la locale du premier realm du groupe
                region_locale = "en_GB" # Valeur par défaut
                if realms_data:
                    first_realm = realms_data[0]
                    region_locale = first_realm.get("locale", "en_GB")

                # Filtrer les noms vides
                realm_names = [n for n in realm_names if n]
                
                if realm_id and realm_names:
                    realms_list.append({
                        "id": realm_id,
                        "name": " / ".join(realm_names),
                        "population": population_type,
                        "region": region_locale,
                        "realms": realms_data
                    })
            
            return sorted(realms_list, key=lambda x: x["name"])
            
        except Exception as e:
            # Fallback en cas d'erreur sur le search (ex: endpoint indisponible)
            print(f"Search API error: {e}, falling back to index")
            return self._get_all_realms_slow_fallback()

    def _get_all_realms_slow_fallback(self) -> List[Dict[str, Any]]:
        """Fallback: méthode lente originale"""
        realms_index = self.get_connected_realms_index()
        realms = []
        
        for realm_ref in realms_index:
            href = realm_ref.get("href", "")
            try:
                realm_id = int(href.split("/connected-realm/")[1].split("?")[0])
                realm_details = self.get_connected_realm_details(realm_id)
                
                if realm_details:
                    realm_names = [r.get("name", "") for r in realm_details.get("realms", [])]
                    realms.append({
                        "id": realm_id,
                        "name": " / ".join(realm_names) if realm_names else f"Realm {realm_id}",
                        "realms": realm_details.get("realms", [])
                    })
            except (IndexError, ValueError):
                continue
        
        return sorted(realms, key=lambda x: x["name"])
    
    def get_auctions(self, connected_realm_id: int) -> List[Dict]:
        """
        Récupère toutes les auctions d'un connected realm
        """
        data = self._make_request(
            f"/data/wow/connected-realm/{connected_realm_id}/auctions",
            DYNAMIC_NAMESPACE
        )
        return data.get("auctions", [])
    
    def get_commodities(self) -> List[Dict]:
        """
        Récupère les prix des commodities (matériaux stackables) 
        au niveau régional (pas par serveur).
        Les commodities incluent: herbes, minerais, tissus, matériaux d'enchantement, etc.
        """
        data = self._make_request(
            "/data/wow/auctions/commodities",
            DYNAMIC_NAMESPACE
        )
        return data.get("auctions", [])
    
    def search_housing_items(self) -> List[Dict]:
        """
        Recherche tous les items de la classe Housing (ID 20) via l'API Search.
        Effectue deux passes (ordre croissant et décroissant) pour contourner la limite de 1000 items
        et récupérer à la fois les anciens et les nouveaux items.
        """
        all_items_dict = {}  # Utiliser un dict par ID pour dédupliquer
        page_size = 100
        
        # Liste des ordres de tri à tester
        sort_orders = ["id:asc", "id:desc"]
        
        for sort_order in sort_orders:
            page = 1
            while True:
                params = {
                    "item_class.id": 20,
                    "_pageSize": page_size,
                    "_page": page,
                    "orderby": sort_order
                }
                
                try:
                    data = self._make_request("/data/wow/search/item", STATIC_NAMESPACE, params)
                    results = data.get("results", [])
                    
                    if not results:
                        break
                        
                    for item in results:
                        item_id = item["data"]["id"]
                        if item_id not in all_items_dict:
                            all_items_dict[item_id] = item
                    
                    # Vérifier si on a atteint la dernière page
                    page_count = data.get("pageCount", 0)
                    if page >= page_count:
                        break
                        
                    page += 1
                    
                except BlizzardAPIError:
                    break
        
        return list(all_items_dict.values())
    
    def search_item_by_modified_crafting_category(self, slot_type_id: int, slot_name: str) -> Optional[int]:
        """
        Résout un slot de craft modifié vers un vrai item_id.
        
        Approche : 
        1. Appelle /data/wow/modified-crafting/reagent-slot-type/{slot_type_id}
           pour obtenir les compatible_categories
        2. Utilise le premier category.id pour chercher les items via
           /data/wow/search/item?modified_crafting.category.id=<cat_id>
        3. Retourne le rang 1 (plus petit ID d'item) de ce groupe
        4. Fallback : recherche textuelle par nom si l'approche structurée échoue
        """
        try:
            # Étape 1 : récupérer les catégories compatibles du slot type
            slot_data = self._make_request(
                f"/data/wow/modified-crafting/reagent-slot-type/{slot_type_id}",
                STATIC_NAMESPACE
            )
            categories = slot_data.get("compatible_categories", [])
            if not categories:
                raise BlizzardAPIError("No compatible_categories found")
            
            # Prendre la première catégorie
            category_id = categories[0].get("id")
            if not category_id:
                raise BlizzardAPIError("No category id found")
            
            # Étape 2 : chercher les items qui appartiennent à cette catégorie
            params = {
                "modified_crafting.category.id": category_id,
                "_pageSize": 10,
                "_page": 1,
            }
            data = self._make_request("/data/wow/search/item", STATIC_NAMESPACE, params)
            results = data.get("results", [])
            
            if not results:
                raise BlizzardAPIError(f"No items found for category {category_id}")
            
            # Étape 3 : prendre le rang 1 (item_id le plus petit = rang de base)
            item_ids = sorted([r["data"]["id"] for r in results])
            return item_ids[0]
            
        except BlizzardAPIError:
            # Fallback : recherche textuelle si l'approche structurée échoue
            return self.search_item_by_name(slot_name)
    
    def search_item_by_name(self, item_name: str) -> Optional[int]:
        """
        Recherche un item par nom exact via l'API Search.
        Retourne l'item_id du premier résultat correspondant, ou None.
        Utilisé en fallback de search_item_by_modified_crafting_category.
        """
        try:
            params = {
                "name.fr_FR": item_name,
                "_pageSize": 10,
                "_page": 1
            }
            data = self._make_request("/data/wow/search/item", STATIC_NAMESPACE, params)
            results = data.get("results", [])
            
            if not results:
                return None
            
            exact_matches = []
            for item in results:
                item_data = item.get("data", {})
                name = item_data.get("name", {})
                if isinstance(name, dict):
                    name = name.get("fr_FR", "")
                if name == item_name:
                    exact_matches.append(item_data)
            
            if not exact_matches:
                return None
            
            exact_matches.sort(key=lambda x: x.get("id", 0))
            return exact_matches[0]["id"]
            
        except BlizzardAPIError:
            return None
    
    def get_item_classes(self) -> List[Dict]:
        """
        Récupère les classes d'items (pour filtrer les items de housing)
        """
        data = self._make_request("/data/wow/item-class/index", STATIC_NAMESPACE)
        return data.get("item_classes", [])
    
    def get_item_details(self, item_id: int) -> Dict:
        """
        Récupère les détails d'un item spécifique
        """
        return self._make_request(f"/data/wow/item/{item_id}", STATIC_NAMESPACE)
    
    def get_item_media(self, item_id: int) -> Dict:
        """
        Récupère les médias (icône) d'un item
        """
        try:
            return self._make_request(f"/data/wow/media/item/{item_id}", STATIC_NAMESPACE)
        except BlizzardAPIError:
            return {}
    
    def get_housing_auctions(self, connected_realm_id: int, housing_item_ids: set) -> List[Dict]:
        """
        Récupère uniquement les auctions d'items de housing
        
        Args:
            connected_realm_id: ID du serveur
            housing_item_ids: Set des IDs d'items de housing
        
        Returns:
            Liste des auctions filtrées pour les items de housing
        """
        all_auctions = self.get_auctions(connected_realm_id)
        
        housing_auctions = []
        for auction in all_auctions:
            item_id = auction.get("item", {}).get("id")
            if item_id and item_id in housing_item_ids:
                housing_auctions.append(auction)
        
        return housing_auctions


    def get_profession_index(self) -> List[Dict]:
        """
        Récupère la liste de tous les métiers (professions)
        """
        data = self._make_request("/data/wow/profession/index", STATIC_NAMESPACE)
        return data.get("professions", [])
    
    def get_profession(self, profession_id: int) -> Dict:
        """
        Récupère les détails d'un métier, incluant les skill tiers
        """
        return self._make_request(f"/data/wow/profession/{profession_id}", STATIC_NAMESPACE)
    
    def get_profession_skill_tier(self, profession_id: int, skill_tier_id: int) -> Dict:
        """
        Récupère les catégories et recettes d'un skill tier
        """
        return self._make_request(
            f"/data/wow/profession/{profession_id}/skill-tier/{skill_tier_id}", 
            STATIC_NAMESPACE
        )
    
    def get_recipe(self, recipe_id: int) -> Dict:
        """
        Récupère les détails d'une recette (item crafté + composants)
        """
        return self._make_request(f"/data/wow/recipe/{recipe_id}", STATIC_NAMESPACE)
    
    def get_recipe_media(self, recipe_id: int) -> Dict:
        """
        Récupère les médias (icône) d'une recette
        """
        try:
            return self._make_request(f"/data/wow/media/recipe/{recipe_id}", STATIC_NAMESPACE)
        except BlizzardAPIError:
            return {}
    
    # ========== PET METHODS ==========
    
    def search_pets(self) -> List[Dict]:
        """
        Recherche tous les pets du jeu via l'API Search (100 par page).
        Extrêmement plus rapide que de fetch les détails individuellement.
        """
        all_pets = []
        page_size = 100
        page = 1
        
        while True:
            params = {
                "_pageSize": page_size,
                "_page": page,
                "orderby": "id:asc"
            }
            
            try:
                data = self._make_request("/data/wow/search/pet", STATIC_NAMESPACE, params)
                results = data.get("results", [])
                
                if not results:
                    break
                    
                for item in results:
                    pet_data = item.get("data", {})
                    # Extraire nom
                    name = pet_data.get("name", "")
                    if isinstance(name, dict):
                        name = name.get("fr_FR") or name.get("en_US") or ""
                        
                    # Extraire type de battle pet
                    battle_pet_type = pet_data.get("battle_pet_type", {})
                    type_name = battle_pet_type.get("name", "") if battle_pet_type else ""
                    if isinstance(type_name, dict):
                        type_name = type_name.get("fr_FR") or type_name.get("en_US") or ""
                        
                    # Extraire source
                    source = pet_data.get("source", {})
                    source_name = source.get("name", "") if source else ""
                    if isinstance(source_name, dict):
                        source_name = source_name.get("fr_FR") or source_name.get("en_US") or ""
                        
                    # Creature ID
                    creature = pet_data.get("creature", {})
                    creature_id = creature.get("id") if creature else None
                    
                    # is_tradable and id
                    is_tradable = pet_data.get("is_tradable", False)
                    pet_id = pet_data.get("id")
                    
                    if pet_id:
                        all_pets.append({
                            "id": pet_id,
                            "name": name,
                            "source": source_name,
                            "creature_type": type_name,
                            "is_tradable": is_tradable,
                            "creature_id": creature_id,
                            # Icon will be handled by fetch_icons background job as needed
                            "icon_url": None 
                        })
                
                # Vérifier si on a atteint la dernière page
                page_count = data.get("pageCount", 0)
                if page >= page_count:
                    break
                    
                page += 1
                
            except BlizzardAPIError:
                break
                
        return all_pets
    
    def get_pet_details(self, pet_id: int) -> Dict:
        """
        Récupère les détails d'un pet (nom, source, type créature, etc.)
        """
        try:
            data = self._make_request(f"/data/wow/pet/{pet_id}", STATIC_NAMESPACE)
            
            # Extraire les infos utiles
            name = data.get("name", "")
            if isinstance(name, dict):
                name = name.get("fr_FR") or name.get("en_US") or ""
            
            # Source: comment obtenir le pet
            source = data.get("source", {})
            source_name = source.get("name", "") if source else ""
            if isinstance(source_name, dict):
                source_name = source_name.get("fr_FR") or source_name.get("en_US") or ""
            
            # Type de créature
            creature_type = data.get("battle_pet_type", {})
            type_name = creature_type.get("name", "") if creature_type else ""
            if isinstance(type_name, dict):
                type_name = type_name.get("fr_FR") or type_name.get("en_US") or ""
            
            # Est-ce tradable?
            is_tradable = data.get("is_tradable", False)
            
            # Creature ID (pour le lien wowhead npc)
            creature = data.get("creature", {})
            creature_id = creature.get("id") if creature else None
            
            # Icône
            icon_url = None
            media = data.get("media", {})
            if media and "key" in media:
                # Récupérer l'icône
                icon_data = self.get_pet_media(pet_id)
                if icon_data:
                    assets = icon_data.get("assets", [])
                    for asset in assets:
                        if asset.get("key") == "icon":
                            icon_url = asset.get("value")
                            break
            
            return {
                "id": pet_id,
                "name": name,
                "source": source_name,
                "creature_type": type_name,
                "is_tradable": is_tradable,
                "creature_id": creature_id,
                "icon_url": icon_url
            }
        except BlizzardAPIError:
            return {}
    
    def get_pet_media(self, pet_id: int) -> Dict:
        """Récupère les médias (icône) d'un pet"""
        try:
            return self._make_request(f"/data/wow/media/pet/{pet_id}", STATIC_NAMESPACE)
        except BlizzardAPIError:
            return {}
    
    def get_character_pets(self, realm_slug: str, character_name: str) -> Dict:
        """
        Récupère la collection de pets d'un personnage.
        
        Args:
            realm_slug: Nom du serveur en slug (ex: "argent-dawn", "uldaman")
            character_name: Nom du personnage en minuscules
        
        Returns:
            Dict avec 'pets' (liste des pets) et 'unlocked_battle_pet_slots'
        """
        try:
            # Le namespace profile est différent
            profile_namespace = "profile-eu"
            
            # Le nom du personnage doit être en minuscules
            char_name_lower = character_name.lower()
            realm_slug_lower = realm_slug.lower().replace(" ", "-").replace("'", "")
            
            endpoint = f"/profile/wow/character/{realm_slug_lower}/{char_name_lower}/collections/pets"
            data = self._make_request(endpoint, profile_namespace)
            
            return data
        except BlizzardAPIError as e:
            print(f"Error fetching character pets: {e}")
            return {}


# Instance singleton pour faciliter l'utilisation
_api_instance: Optional[BlizzardAPI] = None


def get_api() -> BlizzardAPI:
    """
    Retourne l'instance singleton de l'API Blizzard
    """
    global _api_instance
    if _api_instance is None:
        _api_instance = BlizzardAPI()
    return _api_instance
