"""
Script pour découvrir les items de housing depuis l'API Blizzard
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

def test_housing_endpoints():
    token = get_token()
    base_url = "https://eu.api.blizzard.com"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Liste des endpoints housing potentiels
    endpoints = [
        "/data/wow/decor/index",
        "/data/wow/fixture/index",
        "/data/wow/room/index",
        "/data/wow/neighborhood-map/index",
        "/data/wow/item-class/index",  # Pour voir les classes d'items
    ]
    
    for endpoint in endpoints:
        print(f"\n=== Testing {endpoint} ===")
        for ns in ["static-eu", "dynamic-eu"]:
            url = f"{base_url}{endpoint}"
            params = {"namespace": ns, "locale": "en_US"}
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                print(f"  {ns}: Status {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    # Afficher un aperçu des données
                    keys = list(data.keys())
                    print(f"    Keys: {keys}")
                    for key in keys:
                        if isinstance(data[key], list) and len(data[key]) > 0:
                            print(f"    {key}: {len(data[key])} items")
                            print(f"    Premier item: {data[key][0]}")
                    break
            except Exception as e:
                print(f"  {ns}: Erreur - {e}")
    
    # Tester l'item class 20 (Trade Goods) ou autre classe qui pourrait contenir housing
    print("\n=== Testing Item Classes ===")
    url = f"{base_url}/data/wow/item-class/index"
    params = {"namespace": "static-eu", "locale": "en_US"}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    if resp.status_code == 200:
        classes = resp.json().get("item_classes", [])
        print(f"Total classes: {len(classes)}")
        for item_class in classes:
            print(f"  - {item_class}")


if __name__ == "__main__":
    test_housing_endpoints()
