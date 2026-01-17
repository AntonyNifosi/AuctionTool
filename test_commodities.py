from blizzard_api import get_api
from data_manager import get_data_manager

api = get_api()
dm = get_data_manager()

# Test commodities
print('Fetching commodities...')
commodities = api.get_commodities()
print(f'Got {len(commodities)} commodities')

# Check for our reagents
reagent_ids = [22449, 22446, 22445]  # BC enchanting mats
found = [c for c in commodities if c.get('item', {}).get('id') in reagent_ids]
print(f'Found {len(found)} of our reagents in commodities')
for f in found[:5]:
    item_id = f['item']['id']
    price = f.get('unit_price')
    print(f"  Item {item_id}: {price} copper")

# Save commodity prices for our reagents
all_reagent_ids = dm.get_all_reagent_ids()
print(f"\nProcessing {len(all_reagent_ids)} reagent IDs...")

item_stats = {}
for c in commodities:
    item_id = c.get('item', {}).get('id')
    if item_id in all_reagent_ids:
        if item_id not in item_stats:
            item_stats[item_id] = {'prices': [], 'qty': 0}
        
        price = c.get('unit_price', 0)
        qty = c.get('quantity', 1)
        
        if price > 0:
            item_stats[item_id]['prices'].append(price)
            item_stats[item_id]['qty'] += qty

print(f"Found {len(item_stats)} reagents in commodities")

# Save to DB with realm_id=0 (regional)
for item_id, stats in item_stats.items():
    prices = stats['prices']
    if prices:
        min_price = min(prices)
        avg_price = sum(prices) / len(prices)
        dm.record_price_data(
            item_id=item_id,
            realm_id=0,  # Regional
            min_price=min_price,
            avg_price=avg_price,
            total_quantity=stats['qty'],
            auction_count=len(prices)
        )

print("Done! Testing craft cost...")

# Test craft cost
cost = dm.calculate_craft_cost(257037, 1096)  # Holo-estrade on Hyjal
print(f"Craft cost for Holo-estrade: {cost}")
if cost:
    gold = cost // 10000
    silver = (cost % 10000) // 100
    copper = cost % 100
    print(f"  = {gold}g {silver}s {copper}c")
