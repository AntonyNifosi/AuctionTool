import sqlite3
conn = sqlite3.connect('housing_data.db')
c = conn.cursor()

# Find the recipe for Holo-estrade draeneï
c.execute("SELECT recipe_id, crafted_item_id, profession_name, recipe_name FROM recipes WHERE recipe_name LIKE '%Holo%' OR recipe_name LIKE '%estrade%'")
recipes = c.fetchall()
print('Found recipes:', len(recipes))
for r in recipes:
    print(f'  {r}')

if recipes:
    recipe_id = recipes[0][0]
    c.execute('SELECT reagent_item_id, reagent_name, quantity FROM recipe_reagents WHERE recipe_id = ?', (recipe_id,))
    reagents = c.fetchall()
    print('\nReagents:')
    for rg in reagents:
        # Check if this reagent has price data
        c.execute('SELECT COUNT(*) FROM price_history WHERE item_id = ?', (rg[0],))
        has_price = c.fetchone()[0] > 0
        print(f'  {rg[0]}: {rg[1]} x{rg[2]} - Has price data: {has_price}')
