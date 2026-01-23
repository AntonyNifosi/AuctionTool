import sqlite3
import os

db_path = "housing_data.db"
if not os.path.exists(db_path):
    db_path = os.path.join("backend", "housing_data.db")

print(f"Checking DB at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check ID 212
    print(f"Checking Pet ID 212...")
    cursor.execute("SELECT * FROM pets WHERE pet_id = 212")
    row = cursor.fetchone()
    
    if row:
        print(f"Found Pet 212:")
        print(f"Name: {row['name']}")
        print(f"Source: {row['source']}")
        print(f"ID: {row['pet_id']}")
    else:
        print("Pet 212 NOT FOUND in DB.")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
