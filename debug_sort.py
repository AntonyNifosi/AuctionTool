"""
Script de test du tri Search API
"""
import requests
from config import BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET, AUTH_URL

def get_token():
    response = requests.post(
        AUTH_URL,
        data={"grant_type": "client_credentials"},
        auth=(BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET),
        timeout=10
    )
    return response.json().get("access_token")

def test_sort():
    token = get_token()
    base_url = "https://eu.api.blizzard.com"
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=== Test Tri ID Desc ===")
    url = f"{base_url}/data/wow/search/item"
    params = {
        "namespace": "static-eu",
        "locale": "en_US",
        "item_class.id": 20,
        "_pageSize": 100,
        "_page": 1,
        "orderby": "id:desc"  # Tentative de tri descendant
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        print(f"Status: {resp.status_code}")
        
        results = data.get("results", [])
        if results:
            first_id = results[0]['data']['id']
            last_id = results[-1]['data']['id']
            print(f"Premier ID (Desc): {first_id}")
            print(f"Dernier ID (Desc): {last_id}")
            
            # Comparer avec Asc
            params["orderby"] = "id:asc"
            resp_asc = requests.get(url, headers=headers, params=params, timeout=10)
            data_asc = resp_asc.json()
            results_asc = data_asc.get("results", [])
            print(f"Premier ID (Asc): {results_asc[0]['data']['id']}")
            
            if first_id > results_asc[-1]['data']['id']:
                print(">>> Le tri descendant fonctionne et révèle des IDs plus récents !")
            else:
                print(">>> Le tri descendant ne semble pas donner de résultats différents ou plus récents.")
        
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    test_sort()
