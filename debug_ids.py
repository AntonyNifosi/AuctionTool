"""
Script d'analyse des Items via Search API et Item Class
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

def analyze_items():
    token = get_token()
    base_url = "https://eu.api.blizzard.com"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Tester Search API pour Item Class 20
    print("=== Analyse Search API (Item Class 20) ===")
    url = f"{base_url}/data/wow/search/item"
    params = {
        "namespace": "static-eu",
        "locale": "en_US",
        "item_class.id": 20,
        "_pageSize": 100,
        "_page": 1,
        "orderby": "id"
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            print(f"Total results: {data.get('pageCount')} pages, {data.get('pageSize')} per page")
            print(f"Items trouvés dans page 1: {len(results)}")
            if results:
                print(f"Premier item: {results[0]}")
                # Vérifier si on a un lien vers le decor ID (peu probable mais sait-on jamais)
    except Exception as e:
        print(f"Erreur Search: {e}")

    # 2. Tester Search API pour Decor (si possible)
    # On sait que Decor id 530 est lié à Item id 236678.
    # On peut chercher Item 236678 voir à quoi il ressemble
    print("\n=== Analyse Item Specifique 236678 ===")
    url = f"{base_url}/data/wow/item/236678"
    params = {"namespace": "static-eu", "locale": "en_US"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Nom: {data.get('name')}")
            print(f"Class ID: {data.get('item_class', {}).get('id')}")
            print(f"Subclass ID: {data.get('item_subclass', {}).get('id')}")
    except Exception as e:
        print(f"Erreur Item: {e}")

if __name__ == "__main__":
    analyze_items()
