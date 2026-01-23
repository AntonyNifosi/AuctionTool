import sqlite3
import os

# Try to find the DB
db_path = "housing_data.db"
if not os.path.exists(db_path):
    # Try backend folder
    db_path = os.path.join("backend", "housing_data.db")

print(f"Checking DB at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Search for the pet
    pet_name = "Flagellin du val d'Ammené"
    print(f"Searching for: {pet_name}")
    
    cursor.execute("SELECT * FROM pets WHERE name LIKE ?", (f"%{pet_name}%",))
    rows = cursor.fetchall()
    
    if not rows:
        print("Pet not found in DB.")
        # List a few pets to verify DB content
        cursor.execute("SELECT name FROM pets LIMIT 5")
        print("Sample pets in DB:", cursor.fetchall())
    else:
        # Get column names
        cols = [description[0] for description in cursor.description]
        for row in rows:
            print("\nFound Pet:")
            for col, val in zip(cols, row):
                print(f"{col}: {val}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
