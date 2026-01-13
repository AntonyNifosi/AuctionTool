"""
Script de diagnostic avancé des prix
"""
import requests
import json
from config import BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET, AUTH_URL

def get_token():
    response = requests.post(
        AUTH_URL,
        data={"grant_type": "client_credentials"},
        auth=(BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET),
        timeout=10
    )
    return response.json().get("access_token")

def debug_pricing():
    token = get_token()
    base_url = "https://eu.api.blizzard.com"
    headers = {"Authorization": f"Bearer {token}"}
    
    print("1. Recherche des items Housing (Page 1)")
    search_url = f"{base_url}/data/wow/search/item"
    params = {
        "namespace": "static-eu",
        "locale": "en_US",
        "item_class.id": 20,
        "_pageSize": 100,
        "_page": 1,
        "orderby": "id"
    }
    
    housing_ids = set()
    try:
        resp = requests.get(search_url, headers=headers, params=params, timeout=10)
        data = resp.json()
        print(f"   Status: {resp.status_code}")
        print(f"   Total items trouvés (API): {data.get('pageCount', 0) * 100} approx")
        
        for item in data.get("results", []):
            housing_ids.add(item['data']['id'])
            
        print(f"   IDs chargés (page 1): {len(housing_ids)}")
        sample_id = list(housing_ids)[0]
        print(f"   Exemple ID: {sample_id}")
        
    except Exception as e:
        print(f"   Erreur Search: {e}")
        return

    print("\n2. Récupération des enchères pour un gros serveur (Hyjal - ID 1390)")
    # Hyjal EU est souvent ID 1390, vérifions si on peut le trouver ou utilisons un ID connu
    # Aegwynn est 57, Archimonde 1615
    realm_id = 1615 # Archimonde
    
    auctions_url = f"{base_url}/data/wow/connected-realm/{realm_id}/auctions"
    params = {
        "namespace": "dynamic-eu",
        "locale": "en_US"
    }
    
    try:
        print("   Téléchargement des enchères (peut être long)...")
        resp = requests.get(auctions_url, headers=headers, params=params, timeout=30)
        print(f"   Status: {resp.status_code}")
        
        if resp.status_code == 200:
            auction_data = resp.json()
            auctions = auction_data.get("auctions", [])
            print(f"   Nombre total d'enchères: {len(auctions)}")
            
            # Analyse des correspondances
            matched_count = 0
            housing_matches = []
            
            for auc in auctions:
                item_id = auc.get("item", {}).get("id")
                if item_id in housing_ids:
                    matched_count += 1
                    if len(housing_matches) < 5:
                        housing_matches.append((item_id, auc.get("buyout") or auc.get("unit_price")))
            
            print(f"   Enchères correspondant aux items Housing (Page 1 seulement): {matched_count}")
            if housing_matches:
                print(f"   Exemples de prix trouvés: {housing_matches}")
            else:
                print("   AUCUNE CORRESPONDANCE TROUVÉE !")
                
                # Cherchons si l'exemple ID est dans les auctions
                print(f"   Recherche spécifique de l'ID {sample_id} dans les enchères...")
                found = False
                for auc in auctions:
                    if auc.get("item", {}).get("id") == sample_id:
                        print(f"   TROUVÉ ! {auc}")
                        found = True
                        break
                if not found:
                    print(f"   ID {sample_id} non trouvé dans les enchères.")

    except Exception as e:
        print(f"   Erreur Auctions: {e}")

if __name__ == "__main__":
    debug_pricing()
