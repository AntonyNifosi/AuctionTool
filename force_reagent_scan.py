"""
Force le tracking des prix des réactifs pour un seul serveur pour tester
"""
from blizzard_api import get_api
from data_manager import get_data_manager

api = get_api()
dm = get_data_manager()

# Get ALL IDs to track
housing_items = dm.get_housing_items()
housing_ids = {item['item_id'] for item in housing_items}
reagent_ids = dm.get_all_reagent_ids()
target_ids = housing_ids | reagent_ids

print(f"Tracking {len(housing_ids)} housing + {len(reagent_ids)} reagents = {len(target_ids)} total")

# Fetch auctions for Hyjal
realm_id = 1096
print(f"Fetching auctions for realm {realm_id}...")
auctions = api.get_auctions(realm_id)
print(f"Got {len(auctions)} auctions")

# Process like update_manager does
item_stats = {}
for auction in auctions:
    item_id = auction.get("item", {}).get("id")
    if item_id in target_ids:
        if item_id not in item_stats:
            item_stats[item_id] = {"prices": [], "qty": 0}
        
        price = auction.get("buyout") or auction.get("unit_price", 0)
        qty = auction.get("quantity", 1)
        
        if price > 0:
            item_stats[item_id]["prices"].append(price)
            item_stats[item_id]["qty"] += qty

print(f"Found {len(item_stats)} items to save")

# Count reagents
reagent_found = sum(1 for item_id in item_stats if item_id in reagent_ids)
print(f"Reagents found: {reagent_found}")

# Save prices
for item_id, stats in item_stats.items():
    prices = stats["prices"]
    if prices:
        min_price = min(prices)
        avg_price = sum(prices) / len(prices)
        total_qty = stats["qty"]
        auction_count = len(prices)
        
        dm.record_price_data(
            item_id=item_id,
            realm_id=realm_id,
            min_price=min_price,
            avg_price=avg_price,
            total_quantity=total_qty,
            auction_count=auction_count
        )

print("Done! Now checking reagent prices...")

# Verify
import sqlite3
conn = sqlite3.connect('housing_data.db')
c = conn.cursor()
c.execute('SELECT DISTINCT item_id FROM price_history WHERE item_id IN (SELECT reagent_item_id FROM recipe_reagents)')
reagent_prices = c.fetchall()
print(f'Reagents with prices now: {len(reagent_prices)}')

# Test craft cost
cost = dm.calculate_craft_cost(257037, realm_id)  # Holo-estrade
print(f"Craft cost for Holo-estrade: {cost}")
