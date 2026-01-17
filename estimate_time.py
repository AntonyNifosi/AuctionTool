from blizzard_api import get_api
import time

api = get_api()
PROFS = [164, 165, 171, 197, 202, 333, 755, 773]
HOUSING_KEYWORDS = ['décor', 'decor', 'housing', 'maison', 'ameublement', 'furnish']

total_deco_recipes = 0
start = time.time()

for pid in PROFS:
    prof = api.get_profession(pid)
    name = prof.get('name', {})
    if isinstance(name, dict):
        name = name.get('fr_FR', str(pid))
    
    tiers = prof.get('skill_tiers', [])
    for tier in tiers:
        tier_data = api.get_profession_skill_tier(pid, tier['id'])
        for cat in tier_data.get('categories', []):
            cat_name = cat.get('name', '')
            if isinstance(cat_name, dict):
                cat_name = cat_name.get('fr_FR', '')
            if any(kw in cat_name.lower() for kw in HOUSING_KEYWORDS):
                count = len(cat.get('recipes', []))
                total_deco_recipes += count
                print(f"{name} - {cat_name}: {count} recipes")

elapsed = time.time() - start
print("---")
print(f"Total decoration recipes: {total_deco_recipes}")
print(f"Time to scan categories: {elapsed:.1f}s")
print(f"Estimated total time: {total_deco_recipes * 0.5:.0f}s (~{total_deco_recipes * 0.5 / 60:.1f} min)")
