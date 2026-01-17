import sqlite3
from datetime import datetime

conn = sqlite3.connect('housing_data.db')
c = conn.cursor()

# Latest records
c.execute('SELECT MAX(recorded_at) FROM price_history')
latest = c.fetchone()[0]
print(f'Latest price record: {latest}')
print(f'Current time: {datetime.now()}')

# Count records from today
c.execute("SELECT COUNT(*) FROM price_history WHERE recorded_at > datetime('now', '-1 hour')")
recent = c.fetchone()[0]
print(f'Records from last hour: {recent}')

# Check reagent prices specifically
c.execute('SELECT DISTINCT item_id FROM price_history WHERE item_id IN (SELECT reagent_item_id FROM recipe_reagents)')
reagent_prices = c.fetchall()
print(f'Reagents with ANY prices: {len(reagent_prices)}')
