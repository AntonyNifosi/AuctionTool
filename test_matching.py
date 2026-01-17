import sqlite3
from blizzard_api import get_api

api = get_api()
conn = sqlite3.connect('housing_data.db')
c = conn.cursor()

# Get housing items and create name lookup dict
c.execute('SELECT item_id, name FROM housing_items')
housing_items = c.fetchall()
housing_name_to_id = {name.lower().strip(): item_id for item_id, name in housing_items}

print(f"Housing items loaded: {len(housing_name_to_id)}")

# Get a decoration recipe
recipe = api.get_recipe(55996)  # Tapis de Dazar'alor rouge
recipe_name = recipe.get("name", "")
print(f"Recipe name: '{recipe_name}'")
print(f"Recipe name lower: '{recipe_name.lower().strip()}'")

# Check if it exists in housing items
matched_id = housing_name_to_id.get(recipe_name.lower().strip())
print(f"Matched item ID: {matched_id}")

# Search partial
if not matched_id:
    print("\nSearching partial matches...")
    for name, item_id in housing_name_to_id.items():
        if "dazar" in name and "rouge" in name:
            print(f"  Found: '{name}' -> {item_id}")
