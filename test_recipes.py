from blizzard_api import get_api
import sqlite3

api = get_api()
conn = sqlite3.connect('housing_data.db')
c = conn.cursor()
c.execute('SELECT item_id FROM housing_items')
housing_ids = set(row[0] for row in c.fetchall())
print(f'Housing items in DB: {len(housing_ids)}')

# Get Tailoring TWW tier - decorations category
tier = api.get_profession_skill_tier(197, 2533)  # TWW tier
cats = tier.get('categories', [])

for cat in cats:
    name = cat.get('name', '')
    if 'd' in name.lower() and 'cor' in name.lower():  # decor
        recipes = cat.get('recipes', [])
        print(f'Found {len(recipes)} decoration recipes in category: {name}')
        # Check first 5 recipes
        for r in recipes[:5]:
            recipe = api.get_recipe(r['id'])
            crafted = recipe.get('crafted_item', {})
            crafted_id = crafted.get('id')
            in_db = crafted_id in housing_ids
            crafted_name = crafted.get('name', 'Unknown')
            print(f'  Recipe {r["id"]}: crafts item {crafted_id} ({crafted_name}), in housing_items={in_db}')
