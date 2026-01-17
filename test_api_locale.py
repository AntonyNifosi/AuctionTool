
import sys
import os
sys.path.append(os.getcwd())
from blizzard_api import BlizzardAPI, get_api

def test_realm_locale():
    print("Initializing API...")
    try:
        api = get_api()
    except Exception as e:
        print(f"Failed to init API: {e}")
        return

    print("Fetching realms...")
    try:
        # On appelle la méthode interne pour voir la structure brute d'un item
        # ou on appelle la méthode publique et on inspecte le résultat
        realms = api.get_all_realms_with_names()
        
        print(f"Found {len(realms)} connected realms.")
        
        if realms:
            first = realms[0]
            print(f"First realm: {first['name']}")
            print(f"Region/Locale: {first.get('region')}")
            print("Full data key 'realms' (first 1):")
            if 'realms' in first and first['realms']:
                print(first['realms'][0])
            else:
                print("No 'realms' key or empty")
                
            # Check specifically for locale in raw data if possible?
            # La méthode get_all_realms_with_names traite déjà la donnée.
            # Verifions si 'locale' apparaît dans le dump
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_realm_locale()
