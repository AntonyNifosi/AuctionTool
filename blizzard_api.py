"""
Module d'interaction avec l'API Blizzard Battle.net
Gère l'authentification OAuth2 et les appels aux endpoints WoW
"""
import requests
import time
from typing import Optional, Dict, List, Any
from config import (
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
                
                # Filtrer les noms vides
                realm_names = [n for n in realm_names if n]
                
                if realm_id and realm_names:
                    realms_list.append({
                        "id": realm_id,
                        "name": " / ".join(realm_names),
                        "population": population_type,
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
