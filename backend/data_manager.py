"""
Gestionnaire de données pour le stockage et le calcul des métriques
Utilise SQLite pour stocker l'historique des prix et volumes
"""
import sqlite3
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from .config import DATABASE_PATH, TREND_WEEKS


class DataManager:
    """
    Gestionnaire de données SQLite pour l'historique des prix et volumes
    """
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        # Database initialization is now explicit via initialize_database()
        # to avoid overhead on every request
    
    def initialize_database(self):
        """Public alias for _init_database for startup calls"""
        self._init_database()
        self._ensure_stats_exist()
        self._ensure_normalization()

    def _ensure_normalization(self):
        """Ensures name_normalized column exists and populates NULL values."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for table, id_col in [("housing_items", "item_id"), ("pets", "pet_id")]:
            # 1. Ensure Column Exists
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [info[1] for info in cursor.fetchall()]
            
            if "name_normalized" not in cols:
                print(f"[DataManager] Adding name_normalized to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN name_normalized TEXT")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_name_norm ON {table}(name_normalized)")
            
            # 2. Populate NULLs (smart catch-up)
            cursor.execute(f"SELECT {id_col}, name FROM {table} WHERE name_normalized IS NULL")
            rows = cursor.fetchall()
            
            if rows:
                print(f"[DataManager] Normalizing {len(rows)} new/missing items in {table}...")
                updates = [(self._normalize_text(r["name"]), r[id_col]) for r in rows]
                cursor.executemany(f"UPDATE {table} SET name_normalized = ? WHERE {id_col} = ?", updates)
                conn.commit()
                
        conn.close()

    def _normalize_text(self, text: str) -> str:
        """Removes accents, handles ligatures, and converts to lowercase."""
        import unicodedata
        if not text: return ""
        
        # Handle specific ligatures that NFD doesn't decompose or that we want expanded
        text = text.replace("Œ", "OE").replace("œ", "oe")
        text = text.replace("Æ", "AE").replace("æ", "ae")
        text = text.replace("’", "'") # Normalize curly quotes
        
        return ''.join(c for c in unicodedata.normalize('NFD', text)
                      if unicodedata.category(c) != 'Mn').lower()

    def _ensure_stats_exist(self):
        """Checks if optimizer statistics exist for large tables, runs ANALYZE if missing."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if sqlite_stat1 exists (it might not if ANALYZE never ran)
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='sqlite_stat1'")
        if cursor.fetchone()[0] == 0:
            print("[DataManager] Optimization statistics missing. Running ANALYZE (this may take a few seconds)...")
            cursor.execute("ANALYZE")
            print("[DataManager] Optimization complete.")
        else:
            # Check if price_history is analyzed
            cursor.execute("SELECT count(*) FROM sqlite_stat1 WHERE tbl='price_history'")
            if cursor.fetchone()[0] == 0:
                print("[DataManager] price_history statistics missing. Running ANALYZE...")
                cursor.execute("ANALYZE")
                print("[DataManager] Optimization complete.")
        
        conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Crée une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialise les tables de la base de données"""
        conn = self._get_connection()
        
        # Activer le mode WAL pour une meilleure performance et concurrence
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -100000;") # ~100MB cache
        conn.execute("PRAGMA temp_store = MEMORY;")
        
        cursor = conn.cursor()
        
        # Table pour stocker les informations des items de housing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS housing_items (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                icon_url TEXT,
                category TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table pour stocker les informations des serveurs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS realms (
                realm_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                population TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table pour stocker l'historique des prix
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                realm_id INTEGER NOT NULL,
                min_price INTEGER,
                avg_price REAL,
                total_quantity INTEGER,
                auction_count INTEGER,
                estimated_sales INTEGER DEFAULT 0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES housing_items(item_id),
                FOREIGN KEY (realm_id) REFERENCES realms(realm_id)
            )
        """)
        
        # Index pour accélérer les requêtes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_item_realm 
            ON price_history(item_id, realm_id, recorded_at)
        """)
        # Migration: ajouter colonne estimated_sales si elle n'existe pas
        try:
            cursor.execute("ALTER TABLE price_history ADD COLUMN estimated_sales INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        
        # Migration: ajouter colonne estimated_cancels pour tracker les annulations
        try:
            cursor.execute("ALTER TABLE price_history ADD COLUMN estimated_cancels INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # Table pour stocker les IDs des items de housing connus
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS known_housing_items (
                item_id INTEGER PRIMARY KEY,
                source TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migration: ajouter colonne population si elle n'existe pas (pour bases existantes)
        try:
            cursor.execute("ALTER TABLE realms ADD COLUMN population TEXT")
        except sqlite3.OperationalError:
            pass
            
        # Migration: ajouter colonne region si elle n'existe pas
        try:
            cursor.execute("ALTER TABLE realms ADD COLUMN region TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Table pour stocker les recettes (lien item crafté -> métier)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                recipe_id INTEGER PRIMARY KEY,
                crafted_item_id INTEGER NOT NULL,
                profession_id INTEGER,
                profession_name TEXT,
                recipe_name TEXT,
                expansion TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (crafted_item_id) REFERENCES housing_items(item_id)
            )
        """)
        
        # Table pour stocker les composants de recette
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_reagents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                reagent_item_id INTEGER NOT NULL,
                reagent_name TEXT,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id)
            )
        """)
        
        # Index pour accélérer les lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recipes_crafted_item 
            ON recipes(crafted_item_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reagents_recipe 
            ON recipe_reagents(recipe_id)
        """)
        
        # Migration: ajouter colonne expansion si elle n'existe pas
        try:
            cursor.execute("ALTER TABLE recipes ADD COLUMN expansion TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Table pour stocker les pets (battle pets)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                pet_id INTEGER PRIMARY KEY,
                name TEXT,
                icon_url TEXT,
                source TEXT,
                creature_type TEXT,
                creature_id INTEGER,
                is_tradable BOOLEAN,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migration: ajouter creature_id si la colonne n'existe pas
        try:
            cursor.execute("SELECT creature_id FROM pets LIMIT 1")
        except:
            cursor.execute("ALTER TABLE pets ADD COLUMN creature_id INTEGER")
        
        # Table pour l'historique des prix des pets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pet_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pet_id INTEGER NOT NULL,
                realm_id INTEGER NOT NULL,
                quality_id INTEGER,
                level INTEGER,
                min_price INTEGER,
                avg_price REAL,
                total_quantity INTEGER,
                estimated_sales INTEGER DEFAULT 0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pet_id) REFERENCES pets(pet_id)
            )
        """)
        
        # Index pour accélérer les lookups pets
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pet_price_realm_v2 
            ON pet_price_history(pet_id, realm_id, recorded_at)
        """)

        # Migration: ajouter colonne estimated_sales à pet_price_history
        try:
            cursor.execute("ALTER TABLE pet_price_history ADD COLUMN estimated_sales INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        
        # Migration: ajouter colonne estimated_cancels à pet_price_history
        try:
            cursor.execute("ALTER TABLE pet_price_history ADD COLUMN estimated_cancels INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
            
        # NOUVEAUX INDEXES POUR OPTIMISATION TRI ET FILTRE
        # Housing Items
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_housing_items_name ON housing_items(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_housing_items_category ON housing_items(category)")
        
        # Pets
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pets_name ON pets(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pets_creature_type ON pets(creature_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pets_source ON pets(source)")
        
        # Recipes (si on trie par nom de recette ou profession)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_profession ON recipes(profession_id)")
        
        conn.commit()
        conn.close()
    
    def save_realm(self, realm_id: int, name: str, population: str = None, region: str = None):
        """Sauvegarde ou met à jour un serveur"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO realms (realm_id, name, population, region, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (realm_id, name, population, region))
        
        conn.commit()
        conn.close()
    
    def get_realms(self) -> List[Dict]:
        """Récupère tous les serveurs"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT realm_id, name FROM realms ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        
        return [{"id": row["realm_id"], "name": row["name"]} for row in rows]
    
    def save_housing_item(self, item_id: int, name: str, icon_url: str = None, category: str = None):
        """Sauvegarde ou met à jour un item de housing"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        norm_name = self._normalize_text(name)
        
        cursor.execute("""
            INSERT INTO housing_items (item_id, name, icon_url, category, name_normalized, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(item_id) DO UPDATE SET
                name = excluded.name,
                icon_url = COALESCE(excluded.icon_url, housing_items.icon_url),
                category = excluded.category,
                name_normalized = excluded.name_normalized,
                updated_at = CURRENT_TIMESTAMP
        """, (item_id, name, icon_url, category, norm_name))
        
        conn.commit()
        conn.close()
    
    def get_housing_items(self) -> List[Dict]:
        """Récupère tous les items de housing"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_id, name, icon_url, category, updated_at 
            FROM housing_items 
            ORDER BY name
        """)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_items_without_icons(self, limit: int = 50) -> List[Dict]:
        """Récupère les items sans icône (pour fetch en background)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_id, name 
            FROM housing_items 
            WHERE icon_url IS NULL OR icon_url = ''
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    def update_icon_url(self, item_id: int, icon_url: str):
        """Met à jour l'URL de l'icône d'un item"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE housing_items 
            SET icon_url = ?, updated_at = CURRENT_TIMESTAMP
            WHERE item_id = ?
        """, (icon_url, item_id))
        
        conn.commit()
        conn.close()
    
    def clear_housing_items(self):
        """Vide la table des items de housing"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM housing_items")
        conn.commit()
        conn.close()
    
    def get_housing_item_ids(self) -> set:
        """Récupère les IDs de tous les items de housing connus"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT item_id FROM housing_items")
        rows = cursor.fetchall()
        conn.close()
        
        return {row["item_id"] for row in rows}
    
    def save_known_housing_item_id(self, item_id: int, source: str = "api"):
        """Sauvegarde un ID d'item de housing connu"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO known_housing_items (item_id, source)
            VALUES (?, ?)
        """, (item_id, source))
        
        conn.commit()
        conn.close()
    
    def get_known_housing_item_ids(self) -> set:
        """Récupère les IDs des items de housing connus"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT item_id FROM known_housing_items")
        rows = cursor.fetchall()
        conn.close()
        
        return {row["item_id"] for row in rows}
    
    def record_price_data(self, item_id: int, realm_id: int, min_price: int, 
                          avg_price: float, total_quantity: int, auction_count: int):
        """Enregistre les données de prix pour un item sur un serveur"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO price_history 
            (item_id, realm_id, min_price, avg_price, total_quantity, auction_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, realm_id, min_price, avg_price, total_quantity, auction_count))
        
        conn.commit()
        conn.close()

    def batch_record_price_data(self, price_data_list: List[Tuple]):
        """
        Enregistre un lot de données de prix
        Format: [(item_id, realm_id, min_price, avg_price, total_quantity, auction_count, estimated_sales, estimated_cancels), ...]
        """
        if not price_data_list:
            return
            
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.executemany("""
            INSERT INTO price_history 
            (item_id, realm_id, min_price, avg_price, total_quantity, auction_count, estimated_sales, estimated_cancels)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, price_data_list)
        
        conn.commit()
        conn.close()
    
    def get_current_price(self, item_id: int, realm_id: int) -> Optional[Dict]:
        """Récupère le dernier prix enregistré pour un item sur un serveur"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT min_price, avg_price, total_quantity, auction_count, recorded_at
            FROM price_history
            WHERE item_id = ? AND realm_id = ?
            ORDER BY recorded_at DESC
            LIMIT 1
        """, (item_id, realm_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_price_history(self, item_id: int, realm_id: int, days: int = 21) -> List[Dict]:
        """Récupère l'historique des prix sur une période donnée"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            SELECT min_price, avg_price, total_quantity, auction_count, recorded_at
            FROM price_history
            WHERE item_id = ? AND realm_id = ? AND recorded_at >= ?
            ORDER BY recorded_at ASC
        """, (item_id, realm_id, since))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def calculate_trend(self, item_id: int, realm_id: int) -> Optional[float]:
        """
        Calcule la tendance du prix sur les 3 dernières semaines
        Retourne le pourcentage de variation par rapport à la moyenne
        """
        history = self.get_price_history(item_id, realm_id, days=TREND_WEEKS * 7)
        
        if len(history) < 2:
            return None
        
        # Calculer le prix moyen sur la période
        avg_prices = [h["avg_price"] for h in history if h["avg_price"]]
        if not avg_prices:
            return None
        
        historical_avg = sum(avg_prices) / len(avg_prices)
        current_price = avg_prices[-1]
        
        if historical_avg == 0:
            return None
        
        trend = ((current_price - historical_avg) / historical_avg) * 100
        return round(trend, 2)
    
    def calculate_weekly_volume_change(self, item_id: int, realm_id: int) -> Optional[Dict]:
        """
        Calcule le changement de volume sur la dernière semaine
        Compare le nombre d'auctions au début et à la fin de la semaine
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        week_ago = datetime.now() - timedelta(days=7)
        
        # Données du début de la semaine
        cursor.execute("""
            SELECT total_quantity, auction_count, recorded_at
            FROM price_history
            WHERE item_id = ? AND realm_id = ? AND recorded_at >= ?
            ORDER BY recorded_at ASC
            LIMIT 1
        """, (item_id, realm_id, week_ago))
        
        start_row = cursor.fetchone()
        
        # Données les plus récentes
        cursor.execute("""
            SELECT total_quantity, auction_count, recorded_at
            FROM price_history
            WHERE item_id = ? AND realm_id = ?
            ORDER BY recorded_at DESC
            LIMIT 1
        """, (item_id, realm_id))
        
        end_row = cursor.fetchone()
        conn.close()
        
        if not start_row or not end_row:
            return None
        
        start_quantity = start_row["total_quantity"] or 0
        end_quantity = end_row["total_quantity"] or 0
        
        return {
            "start_quantity": start_quantity,
            "end_quantity": end_quantity,
            "change": end_quantity - start_quantity,
            "start_date": start_row["recorded_at"],
            "end_date": end_row["recorded_at"]
        }
    
    def get_all_realms_prices(self, item_id: int) -> List[Dict]:
        """Récupère les derniers prix d'un item sur tous les serveurs avec ventes 3j et cancels"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Date 3 jours en arrière pour le calcul des ventes
        date_3d = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            SELECT 
                r.realm_id,
                r.name as realm_name,
                r.population,
                r.region,
                ph.min_price,
                ph.avg_price,
                ph.total_quantity,
                ph.auction_count,
                ph.recorded_at,
                COALESCE(sales.sales_3d, 0) as sales_3d,
                COALESCE(mp3.min_price_3d, ph.min_price) as min_price_3d,
                COALESCE(cancels.cancels_3d, 0) as cancels_3d
            FROM realms r
            LEFT JOIN (
                SELECT 
                    realm_id,
                    min_price,
                    avg_price,
                    total_quantity,
                    auction_count,
                    recorded_at,
                    ROW_NUMBER() OVER (PARTITION BY realm_id ORDER BY recorded_at DESC) as rn
                FROM price_history
                WHERE item_id = ?
            ) ph ON r.realm_id = ph.realm_id AND ph.rn = 1
            LEFT JOIN (
                SELECT realm_id, SUM(estimated_sales) as sales_3d
                FROM price_history
                WHERE item_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            ) sales ON r.realm_id = sales.realm_id
            LEFT JOIN (
                SELECT realm_id, MIN(min_price) as min_price_3d
                FROM price_history
                WHERE item_id = ? AND recorded_at >= ? AND min_price > 0
                GROUP BY realm_id
            ) mp3 ON r.realm_id = mp3.realm_id
            LEFT JOIN (
                SELECT realm_id, SUM(COALESCE(estimated_cancels, 0)) as cancels_3d
                FROM price_history
                WHERE item_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            ) cancels ON r.realm_id = cancels.realm_id
            ORDER BY r.name
        """, (item_id, item_id, date_3d, item_id, date_3d, item_id, date_3d))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_items_summary(self, realm_id: int, search_query: str = None, category: str = None, 
                         sort_by: str = "name", sort_order: str = "asc", 
                         limit: int = 50, offset: int = 0) -> Tuple[List[Dict], int]:
        """
        Récupère un résumé des items de housing avec leurs métriques.
        OPTIMISÉ : Filtre, Tri et Pagination complets en SQL.
        JOIN correct pour éviter le full scan de price_history.
        Retourne (items, total_count).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Base Query Conditions
        where_conditions = ["1=1"]
        params = []
        
        if search_query:
            where_conditions.append("hi.name LIKE ?")
            params.append(f"%{search_query}%")
            
        if category and category != "Toutes":
            if category == "Autre":
                where_conditions.append("(hi.category IS NULL OR hi.category = 'Autre')")
            else:
                where_conditions.append("hi.category = ?")
                params.append(category)
        
        where_clause = " AND ".join(where_conditions)
            
        # 2. Get Total Count (with filters applied)
        count_query = f"SELECT COUNT(*) as total FROM housing_items hi WHERE {where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()["total"]
        
        if total_count == 0:
            conn.close()
            return [], 0
            
        # 3. Main Query with optimization
        
        sort_column = "name" # Scope is final_data, so no fi prefix
        direction = "ASC" if sort_order == "asc" else "DESC"
        
        if sort_by == "min_price":
            sort_column = "min_price"
        elif sort_by == "sales_3d":
            sort_column = "sales_3d"
        elif sort_by == "trend":
            sort_column = "trend"
            
        if sort_by == "name":
             # Use normalized column for sorting
             order_clause = f"ORDER BY name_normalized {direction}"
        else:
             order_clause = f"ORDER BY CASE WHEN {sort_column} IS NULL THEN 1 ELSE 0 END, {sort_column} {direction}, name_normalized ASC"
        
        # OPTIMIZATION STRATEGY:
        # If sorting by NAME (default), we can LIMIT inside filtered_items CTE.
        # This drastically reduces the number of items we need to fetch prices for (50 vs 2000).
        # If sorting by PRICE/TREND, we MUST fetch prices for all filtered items first, THEN sort/limit.
        # Note: Even for Price sort, joining filtered_items is critical to avoid Full Table Scan.
        
        # Re-structure params construction
        sql_filtered_items = f"""
            SELECT item_id, name, icon_url, category, name_normalized
            FROM housing_items hi
            WHERE {where_clause}
        """
        
        param_list = list(params) # Filter params
        
        if sort_by == "name":
            # Apply Limit/Offset EARLY
            sql_filtered_items += f" ORDER BY name_normalized {direction} LIMIT ? OFFSET ?"
            param_list.extend([limit, offset])
            
        # Common CTEs with JOINs
        # IMPORTANT: Join with filtered_items (fi) prevents Full Table Scan
        
        # Optimization: Use MAX(recorded_at) instead of Window Function ROW_NUMBER()
        # This allows SQLite to use the (item_id, realm_id, recorded_at) index for instant lookups
        # regardless of history size.
        
        query = f"""
        WITH filtered_items AS (
            {sql_filtered_items}
        ),
        latest_prices_lookup AS (
            SELECT fi.item_id, MAX(ph.recorded_at) as max_date
            FROM filtered_items fi
            JOIN price_history ph ON fi.item_id = ph.item_id
            WHERE ph.realm_id = ?
            GROUP BY fi.item_id
        ),
        latest_prices AS (
            SELECT 
                ph.item_id, ph.min_price, ph.avg_price, ph.total_quantity, ph.auction_count, ph.recorded_at
            FROM latest_prices_lookup lpl
            JOIN price_history ph 
                 ON lpl.item_id = ph.item_id 
                 AND lpl.max_date = ph.recorded_at
                 AND ph.realm_id = ?
        ),
        sales_3days AS (
            SELECT 
                fi.item_id,
                SUM(ph.estimated_sales) as sales_3d
            FROM filtered_items fi
            JOIN price_history ph ON fi.item_id = ph.item_id
            WHERE ph.realm_id = ? AND ph.recorded_at >= datetime('now', '-3 days')
            GROUP BY fi.item_id
        ),
        cancels_3days AS (
            SELECT 
                fi.item_id,
                SUM(COALESCE(ph.estimated_cancels, 0)) as cancels_3d
            FROM filtered_items fi
            JOIN price_history ph ON fi.item_id = ph.item_id
            WHERE ph.realm_id = ? AND ph.recorded_at >= datetime('now', '-3 days')
            GROUP BY fi.item_id
        ),
        min_price_3days AS (
            SELECT 
                fi.item_id,
                MIN(ph.min_price) as real_min_price
            FROM filtered_items fi
            JOIN price_history ph ON fi.item_id = ph.item_id
            WHERE ph.realm_id = ? AND ph.recorded_at >= datetime('now', '-3 days') AND ph.min_price > 0
            GROUP BY fi.item_id
        ),
        historical_stats AS (
            SELECT 
                fi.item_id,
                AVG(ph.avg_price) as hist_avg_price
            FROM filtered_items fi
            JOIN price_history ph ON fi.item_id = ph.item_id
            WHERE ph.realm_id = ? AND ph.recorded_at >= datetime('now', '-21 days')
            GROUP BY fi.item_id
        ),
        week_start_lookup AS (
             SELECT fi.item_id, MIN(ph.recorded_at) as min_date
             FROM filtered_items fi
             JOIN price_history ph ON fi.item_id = ph.item_id
             WHERE ph.realm_id = ? AND ph.recorded_at >= datetime('now', '-7 days')
             GROUP BY fi.item_id
        ),
        week_start_volume AS (
            SELECT 
                ph.item_id, ph.total_quantity as start_quantity
            FROM week_start_lookup wsl
            JOIN price_history ph 
                ON wsl.item_id = ph.item_id 
                AND wsl.min_date = ph.recorded_at
                AND ph.realm_id = ?
        ),
        final_data AS (
            SELECT 
                fi.item_id,
                fi.name,
                fi.name_normalized,
                fi.icon_url,
                fi.category,
                COALESCE(mp3.real_min_price, lp.min_price) as min_price,
                lp.avg_price,
                lp.total_quantity,
                lp.auction_count,
                lp.recorded_at,
                hs.hist_avg_price,
                wsv.start_quantity,
                COALESCE(s3.sales_3d, 0) as sales_3d,
                COALESCE(c3.cancels_3d, 0) as cancels_3d,
                r.recipe_id,
                r.profession_name,
                CASE 
                    WHEN lp.avg_price IS NOT NULL AND hs.hist_avg_price IS NOT NULL AND hs.hist_avg_price > 0 
                    THEN ROUND(((lp.avg_price - hs.hist_avg_price) / hs.hist_avg_price) * 100, 1)
                    ELSE NULL 
                END as trend
            FROM filtered_items fi
            LEFT JOIN latest_prices lp ON fi.item_id = lp.item_id
            LEFT JOIN sales_3days s3 ON fi.item_id = s3.item_id
            LEFT JOIN cancels_3days c3 ON fi.item_id = c3.item_id
            LEFT JOIN min_price_3days mp3 ON fi.item_id = mp3.item_id
            LEFT JOIN historical_stats hs ON fi.item_id = hs.item_id
            LEFT JOIN week_start_volume wsv ON fi.item_id = wsv.item_id
            LEFT JOIN recipes r ON fi.item_id = r.crafted_item_id
        )
        SELECT * FROM final_data
        {order_clause}
        """
        
        # Add Realm IDs to params
        # Add Realm IDs to params.
        # CTEs Order: latest_prices_lookup (1), latest_prices (1), sales_3days (1), cancels_3days (1), min_price_3days (1), historical_stats (1), week_start_lookup (1), week_start_volume (1)
        # Total 8 realm_id params needed
        param_list.extend([realm_id, realm_id, realm_id, realm_id, realm_id, realm_id, realm_id, realm_id])
        
        if sort_by == "name":
            # Already offsetted in CTE, just limit final result to be safe/consistent (offset 0)
            # We strictly don't need limit here if CTE limit is exact, but safety good.
             query += " LIMIT ?" 
             param_list.append(limit)
        else:
            # Need full limit offset
            query += " LIMIT ? OFFSET ?"
            param_list.extend([limit, offset])
        
        cursor.execute(query, param_list)
        rows = cursor.fetchall()
        conn.close()
        
        # Batch Calculate Craft Costs
        # Optimization: Only calculate for the item_ids we actually retrieved
        retrieved_ids = [row["item_id"] for row in rows]
        if retrieved_ids:
            craft_costs = self._batch_calculate_craft_costs(realm_id, retrieved_ids)
        else:
            craft_costs = {}
        
        items = []
        for row in rows:
            item = {
                "item_id": row["item_id"],
                "name": row["name"],
                "icon_url": row["icon_url"],
                "category": row["category"],
                "min_price": row["min_price"],
                "avg_price": row["avg_price"],
                "total_quantity": row["total_quantity"],
                "auction_count": row["auction_count"],
                "recorded_at": row["recorded_at"],
                "sales_3d": row["sales_3d"],
                "cancels_3d": row["cancels_3d"],
                "trend": row["trend"], 
                "volume_change": None,
                "profession_name": row["profession_name"],
                "craft_cost": craft_costs.get(row["item_id"]),
            }
            
            # Calcul Volume Change
            current_qty = row["total_quantity"]
            start_qty = row["start_quantity"]
            
            if current_qty is not None and start_qty is not None:
                item["volume_change"] = current_qty - start_qty
            
            items.append(item)
        
        return items, total_count
    
    def cleanup_old_data(self, days: int = 7):
        """Supprime les données de plus de X jours (défaut: 7 jours)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            DELETE FROM price_history WHERE recorded_at < ?
        """, (cutoff,))
        
        cursor.execute("""
            DELETE FROM pet_price_history WHERE recorded_at < ?
        """, (cutoff,))
        
        conn.commit()
        conn.close()

    def get_last_price_update(self) -> Optional[datetime]:
        """Retourne la date de la dernière mise à jour de prix enregistrée"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(recorded_at) as last_update FROM price_history")
        row = cursor.fetchone()
        conn.close()
        
        if row and row["last_update"]:
            try:
                return datetime.fromisoformat(str(row["last_update"]).replace("Z", "+00:00"))
            except ValueError:
                # Tenter un parsing plus permissif si needed ou assumer format standard
                return pd.to_datetime(row["last_update"]).to_pydatetime()
        return None

    def get_estimated_sales_3d(self, item_id: int, realm_id: int) -> int:
        """Calcule les ventes estimées sur les 3 derniers jours"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        date_3d = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            SELECT SUM(estimated_sales) as total_sales
            FROM price_history
            WHERE item_id = ? AND realm_id = ? AND recorded_at >= ?
        """, (item_id, realm_id, date_3d))
        
        row = cursor.fetchone()
        conn.close()
        
        return row["total_sales"] if row and row["total_sales"] is not None else 0

    def get_min_price_3d(self, item_id: int, realm_id: int) -> int:
        """Calcule le prix minimum sur les 3 derniers jours"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        date_3d = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            SELECT MIN(min_price) as min_price_3d
            FROM price_history
            WHERE item_id = ? AND realm_id = ? AND recorded_at >= ? AND min_price > 0
        """, (item_id, realm_id, date_3d))
        
        row = cursor.fetchone()
        conn.close()
        
        return row["min_price_3d"] if row and row["min_price_3d"] is not None else 0

    def get_best_servers_data(self, item_id: int, days: int = 7) -> List[Dict]:
        """
        Récupère les données pour le classement des meilleurs serveurs.
        Utilise les ventes estimées sur 3 jours et un score composite.
        Score = (Prix × 40%) + (Ventes × 40%) + (Population × 20%)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Date 3 jours en arrière pour le calcul des ventes
        date_3d = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        
        query = """
            WITH Latest AS (
                SELECT 
                    realm_id, min_price, total_quantity,
                    ROW_NUMBER() OVER (PARTITION BY realm_id ORDER BY recorded_at DESC) as rn
                FROM price_history 
                WHERE item_id = ?
            ),
            Sales3Days AS (
                SELECT realm_id, SUM(estimated_sales) as sales_3d
                FROM price_history
                WHERE item_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            ),
            Cancels3Days AS (
                SELECT realm_id, SUM(COALESCE(estimated_cancels, 0)) as cancels_3d
                FROM price_history
                WHERE item_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            ),
            MinPrice3Days AS (
                SELECT realm_id, MIN(min_price) as min_price_3d
                FROM price_history
                WHERE item_id = ? AND recorded_at >= ? AND min_price > 0
                GROUP BY realm_id
            )
            SELECT 
                r.name as realm_name,
                r.population,
                r.region,
                l.min_price,
                l.total_quantity as current_volume,
                COALESCE(s.sales_3d, 0) as sales_3d,
                COALESCE(c.cancels_3d, 0) as cancels_3d,
                COALESCE(mp.min_price_3d, l.min_price) as min_price_3d
            FROM realms r
            JOIN Latest l ON r.realm_id = l.realm_id AND l.rn = 1
            LEFT JOIN Sales3Days s ON r.realm_id = s.realm_id
            LEFT JOIN Cancels3Days c ON r.realm_id = c.realm_id
            LEFT JOIN MinPrice3Days mp ON r.realm_id = mp.realm_id
        """
        
        cursor.execute(query, (item_id, item_id, date_3d, item_id, date_3d, item_id, date_3d))
        rows = cursor.fetchall()
        conn.close()
        
        # Population scoring
        population_scores = {
            "FULL": 1.0,
            "HIGH": 0.8,
            "MEDIUM": 0.6,
            "LOW": 0.4,
            "NEW_PLAYERS": 0.3,
        }
        
        results = []
        for row in rows:
            results.append(dict(row))
        
        # Filtrer les serveurs russes et ceux sans prix (current ou historique)
        # On garde si on a un prix actuel OU un prix historique (pour les serveurs sold-out mais valides)
        results = [r for r in results if (r.get("min_price") or r.get("min_price_3d")) and r.get("region") != "ru_RU"]
        
        if not results:
            return []
        
        # Normalisation pour le score
        prices = [r["min_price_3d"] for r in results]
        sales = [r["sales_3d"] for r in results]
        
        max_price = max(prices) if prices else 1
        min_price = min(prices) if prices else 0
        max_sales = max(sales) if sales else 1
        min_sales = min(sales) if sales else 0
        
        # Calculer le score pour chaque serveur
        # Formule "Saturation du Volume" demandée par l'user :
        # Score = Prix * (1 - exp(-Ventes / K))
        # K = 7 => ~95% d'efficacité à 21 ventes. (User wants 20 sales ~ max utility)
        SATURATION_K = 7
        
        scores_raw = []
        for r in results:
            price = r["min_price_3d"]
            sale = r["sales_3d"]
            
            # Facteur de saturation (0 à 1)
            saturation = 1 - math.exp(-sale / SATURATION_K)
            
            raw_score = price * saturation
            r["raw_score"] = raw_score
            scores_raw.append(raw_score)
            
        # Normalisation 0-100 pour l'affichage
        max_score = max(scores_raw) if scores_raw else 1
        
        for r in results:
            # On normalise par rapport au meilleur score trouvé
            n_score = (r["raw_score"] / max_score) * 100 if max_score > 0 else 0
            r["score"] = round(n_score, 1)
        
        # Trier par score décroissant
        results.sort(key=lambda x: x["score"], reverse=True)
            
        return results

    # ========== RECIPE METHODS ==========
    
    def should_resync_recipes(self, max_age_days: int = 30) -> bool:
        """Vérifie si les recettes doivent être re-synchronisées (données absentes ou trop anciennes)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count, MAX(updated_at) as last_update FROM recipes WHERE expansion IS NOT NULL")
        row = cursor.fetchone()
        conn.close()
        
        if row["count"] == 0:
            return True  # Pas de recettes
        
        if row["last_update"]:
            try:
                last_update = datetime.fromisoformat(str(row["last_update"]).replace("Z", "+00:00"))
                if last_update.tzinfo:
                    last_update = last_update.replace(tzinfo=None)
                age = datetime.now() - last_update
                return age.days >= max_age_days
            except (ValueError, TypeError):
                return True
        
        return True
    
    def save_recipe(self, recipe_id: int, crafted_item_id: int, 
                    profession_id: int, profession_name: str, recipe_name: str,
                    expansion: str = None):
        """Sauvegarde ou met à jour une recette"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO recipes 
            (recipe_id, crafted_item_id, profession_id, profession_name, recipe_name, expansion, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (recipe_id, crafted_item_id, profession_id, profession_name, recipe_name, expansion))
        
        conn.commit()
        conn.close()
    
    def save_recipe_reagents(self, recipe_id: int, reagents: List[Dict]):
        """
        Sauvegarde les composants d'une recette.
        reagents: [{"item_id": 123, "name": "Material", "quantity": 5}, ...]
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Supprimer les anciens reagents pour cette recette (évite les doublons lors du re-sync)
        cursor.execute("DELETE FROM recipe_reagents WHERE recipe_id = ?", (recipe_id,))
        
        # Insérer les nouveaux
        for reagent in reagents:
            cursor.execute("""
                INSERT INTO recipe_reagents (recipe_id, reagent_item_id, reagent_name, quantity)
                VALUES (?, ?, ?, ?)
            """, (recipe_id, reagent["item_id"], reagent.get("name"), reagent["quantity"]))
            
            # [NEW] Register as item to fetch icon later
            cursor.execute("""
                INSERT OR IGNORE INTO housing_items (item_id, name, category, updated_at)
                VALUES (?, ?, 'Composant', CURRENT_TIMESTAMP)
            """, (reagent["item_id"], reagent.get("name")))
        
        conn.commit()
        conn.close()
    
    def get_recipe_for_item(self, item_id: int) -> Optional[Dict]:
        """Récupère la recette associée à un item crafté"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT recipe_id, crafted_item_id, profession_id, profession_name, recipe_name
            FROM recipes
            WHERE crafted_item_id = ?
        """, (item_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_recipe_reagents(self, recipe_id: int) -> List[Dict]:
        """Récupère les composants d'une recette"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT reagent_item_id, reagent_name, quantity
            FROM recipe_reagents
            WHERE recipe_id = ?
        """, (recipe_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_recipe_reagents_details(self, item_id: int, realm_id: int) -> List[Dict]:
        """
        Récupère les détails des composants pour un item (icône, quantité, prix).
        Join avec housing_items pour l'icône et price_history pour le prix actuel.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Trouver la recette
        recipe = self.get_recipe_for_item(item_id)
        if not recipe:
            conn.close()
            return []
            
        recipe_id = recipe["recipe_id"]
        
        # 2. Récupérer les réactifs avec leurs icônes (si dispo)
        cursor.execute("""
            SELECT rr.reagent_item_id, rr.reagent_name, rr.quantity, hi.icon_url
            FROM recipe_reagents rr
            LEFT JOIN housing_items hi ON rr.reagent_item_id = hi.item_id
            WHERE rr.recipe_id = ?
        """, (recipe_id,))
        
        reagents = []
        rows = cursor.fetchall()
        
        for row in rows:
            reagent_id = row["reagent_item_id"]
            name = row["reagent_name"]
            quantity = row["quantity"]
            icon_url = row["icon_url"]
            
            # 3. Récupérer le prix (local > régional > any)
            price_data = None
            if realm_id != 0:
                price_data = self.get_current_price(reagent_id, realm_id)
            
            if not price_data or not price_data.get("min_price"):
                price_data = self.get_current_price(reagent_id, 0)
                
            price = price_data.get("min_price") if price_data else None
            
            reagents.append({
                "item_id": reagent_id,
                "name": name,
                "quantity": quantity,
                "icon_url": icon_url,
                "unit_price": price
            })
            
        conn.close()
        return reagents
    
    def get_all_reagent_ids(self) -> set:
        """Récupère tous les IDs uniques de réactifs pour le tracking des prix"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT reagent_item_id FROM recipe_reagents")
        rows = cursor.fetchall()
        conn.close()
        
        return {row[0] for row in rows if row[0]}
    
    def _batch_calculate_craft_costs(self, realm_id: int, item_ids: List[int] = None) -> Dict[int, float]:
        """
        Calcule tous les craft costs en une seule passe pour la performance.
        Si item_ids est fourni, ne calcule que pour ces items.
        Retourne un dict {item_id: craft_cost}
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Récupérer toutes les recettes et leurs réactifs
        if item_ids:
            # SQLite safe way to do IN clause with variable number of params
            placeholders = ','.join(['?'] * len(item_ids))
            cursor.execute(f"""
                SELECT r.crafted_item_id, rr.reagent_item_id, rr.quantity
                FROM recipes r
                JOIN recipe_reagents rr ON r.recipe_id = rr.recipe_id
                WHERE r.crafted_item_id IN ({placeholders})
            """, item_ids)
        else:
            cursor.execute("""
                SELECT r.crafted_item_id, rr.reagent_item_id, rr.quantity
                FROM recipes r
                JOIN recipe_reagents rr ON r.recipe_id = rr.recipe_id
            """)
        recipe_reagents = cursor.fetchall()
        
        # Collecter les IDs de réactifs nécessaires
        reagent_ids = set()
        for _, r_id, _ in recipe_reagents:
            reagent_ids.add(r_id)
            
        if not reagent_ids:
            conn.close()
            return {}
            
        # 2. Récupérer les prix de ces réactifs (local + régional)
        # On ne récupère QUE les prix des réactifs nécessaires
        placeholders_reagents = ",".join("?" * len(reagent_ids))
        
        # Note: Pour une liste très longue de réactifs, IN (...) peut être lent ou limité
        # Mais c'est mieux que TOUT scanner si on a filtré les items.
        # Si item_ids est None (tout), on garde la logique optimisée globale sans filtre IN
        
        if item_ids and len(reagent_ids) < 1000: # Seuil arbitraire pour passer en filtre
             query = f"""
                WITH LatestPrices AS (
                    SELECT item_id, realm_id, min_price,
                           ROW_NUMBER() OVER (PARTITION BY item_id, realm_id ORDER BY recorded_at DESC) as rn
                    FROM price_history
                    WHERE realm_id IN (?, 0)
                    AND item_id IN ({placeholders_reagents})
                )
                SELECT item_id, realm_id, min_price
                FROM LatestPrices
                WHERE rn = 1
            """
             # Params: realm_id, *reagent_ids
             params = [realm_id] + list(reagent_ids)
             cursor.execute(query, params)
        else:
            # Fallback ou global scan
            cursor.execute("""
                WITH LatestPrices AS (
                    SELECT item_id, realm_id, min_price,
                           ROW_NUMBER() OVER (PARTITION BY item_id, realm_id ORDER BY recorded_at DESC) as rn
                    FROM price_history
                    WHERE realm_id IN (?, 0)
                )
                SELECT item_id, realm_id, min_price
                FROM LatestPrices
                WHERE rn = 1
            """, (realm_id,))
            
        price_rows = cursor.fetchall()
        conn.close()
        
        # 3. Construire un dict de prix: {item_id: min_price} (préfère local à régional)
        prices = {}
        for item_id, r_id, min_price in price_rows:
            if min_price:
                if r_id == realm_id:
                    prices[item_id] = min_price  # Prix local prioritaire
                elif item_id not in prices:
                    prices[item_id] = min_price  # Prix régional si pas de local
        
        # 4. Grouper les réactifs par crafted_item_id
        import collections
        item_reagents = collections.defaultdict(list)
        for crafted_id, reagent_id, qty in recipe_reagents:
            item_reagents[crafted_id].append((reagent_id, qty))
        
        # 5. Calculer les craft costs
        craft_costs = {}
        for item_id, reagents in item_reagents.items():
            total = 0
            for reagent_id, qty in reagents:
                if reagent_id in prices:
                    total += prices[reagent_id] * qty
            if total > 0:
                craft_costs[item_id] = total
        
        return craft_costs
    
    def get_all_expansions(self) -> List[str]:
        """Récupère toutes les expansions uniques pour les filtres"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT expansion FROM recipes WHERE expansion IS NOT NULL AND expansion != '' ORDER BY expansion")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_craftable_items_profit(self, realm_id: int, profession_ids: List[int] = None, expansions: List[str] = None) -> List[Dict]:
        """
        Récupère tous les items craftables avec calcul du profit.
        
        Args:
            realm_id: ID du serveur pour les prix de vente
            profession_ids: Liste optionnelle d'IDs de professions pour filtrer
            expansions: Liste optionnelle d'expansions pour filtrer (exact match ou substring match via LIKE si besoin, ici on fera simple)
            
        Returns:
            Liste de dicts avec item_id, name, profession_name, craft_cost, 
            sell_price, profit, profit_margin, volume, score
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Construction de la requête de base
        query = """
            SELECT r.crafted_item_id, hi.name, hi.icon_url, hi.category,
                   r.profession_id, r.profession_name, r.expansion
            FROM recipes r
            JOIN housing_items hi ON r.crafted_item_id = hi.item_id
            WHERE 1=1
        """
        params = []
        
        # Filtre Professions
        if profession_ids:
            placeholders = ",".join("?" * len(profession_ids))
            query += f" AND r.profession_id IN ({placeholders})"
            params.extend(profession_ids)
            
        # Filtre Expansions
        if expansions:
            # Cleaned expansion names from the frontend (e.g. "Ombreterre", "Kul Tiras / Zandalar")
            # need to match raw tier names in DB (e.g. "Forge d'Ombreterre", "Kul Tiras / Forge de Zandalar")
            # Simple LIKE %name% works for most cases.
            # For BfA "Kul Tiras / Zandalar", we split on "/" and require all parts to match.
            
            exp_conditions = []
            for exp in expansions:
                if " / " in exp:
                    # BfA format: each part must be present in the tier name
                    parts = [p.strip() for p in exp.split("/")]
                    sub_conditions = []
                    for part in parts:
                        sub_conditions.append("r.expansion LIKE ?")
                        params.append(f"%{part}%")
                    exp_conditions.append(f"({' AND '.join(sub_conditions)})")
                else:
                    exp_conditions.append("r.expansion LIKE ?")
                    params.append(f"%{exp}%")
            
            if exp_conditions:
                query += f" AND ({' OR '.join(exp_conditions)})"

        cursor.execute(query, params)
        
        recipe_items = cursor.fetchall()
        
        # Optimization: Si on a filtré les items (par profession ou expansion),
        # on peut restreindre les requêtes suivantes aux seuls item_ids trouvés.
        item_ids = [row["crafted_item_id"] for row in recipe_items]
        
        if not item_ids:
            conn.close()
            return []
            
        # Limite SQLite pour IN clause (variable, souvent 999 par défaut en Python/SQLite ancien, plus haut recent)
        # Si on a beaucoup d'items, on scanne tout (plus rapide que IN immense).
        # Si on a peu d'items (filtre actif), on utilise IN.
        use_item_filter = (len(item_ids) < 2000) and (profession_ids or expansions)
        
        item_filter_sql = ""
        item_filter_params = []
        
        if use_item_filter:
            placeholders = ",".join("?" * len(item_ids))
            item_filter_sql = f" AND item_id IN ({placeholders})"
            item_filter_params = list(item_ids)
            
        # Récupérer les prix de vente minimum sur les 3 derniers jours (plus représentatif)
        query_price = f"""
            SELECT item_id, MIN(min_price) as min_price
            FROM price_history
            WHERE realm_id = ? AND recorded_at >= datetime('now', '-3 days') AND min_price > 0
            {item_filter_sql}
            GROUP BY item_id
        """
        cursor.execute(query_price, [realm_id] + item_filter_params)
        
        sell_prices = {}
        for row in cursor.fetchall():
            sell_prices[row["item_id"]] = row["min_price"]
        
        # Calculer le volume de ventes estimé (sales_3d)
        query_sales = f"""
            SELECT item_id, SUM(estimated_sales) as sales_3d
            FROM price_history
            WHERE realm_id = ? AND recorded_at >= datetime('now', '-3 days')
            {item_filter_sql}
            GROUP BY item_id
        """
        cursor.execute(query_sales, [realm_id] + item_filter_params)
        
        sales_volume = {}
        for row in cursor.fetchall():
            sales_volume[row["item_id"]] = row["sales_3d"] or 0
        
        # Récupérer les cancels (cancels_3d)
        query_cancels = f"""
            SELECT item_id, SUM(COALESCE(estimated_cancels, 0)) as cancels_3d
            FROM price_history
            WHERE realm_id = ? AND recorded_at >= datetime('now', '-3 days')
            {item_filter_sql}
            GROUP BY item_id
        """
        cursor.execute(query_cancels, [realm_id] + item_filter_params)
        
        cancel_counts = {}
        for row in cursor.fetchall():
            cancel_counts[row["item_id"]] = row["cancels_3d"] or 0
        
        # Récupérer le stock actuel (dernière valeur)
        # Note: Pour le stock actuel, la sous-requête MAX(recorded_at) peut être optimisée aussi
        current_stock_query = f"""
            SELECT item_id, total_quantity
            FROM price_history
            WHERE realm_id = ?
            {item_filter_sql}
            AND (item_id, recorded_at) IN (
                SELECT item_id, MAX(recorded_at)
                FROM price_history
                WHERE realm_id = ?
                {item_filter_sql}
                GROUP BY item_id
            )
        """
        params_stock = [realm_id] + item_filter_params + [realm_id] + item_filter_params
        cursor.execute(current_stock_query, params_stock)
        
        current_stock = {}
        for row in cursor.fetchall():
            current_stock[row["item_id"]] = row["total_quantity"] or 0
        
        # Récupérer le stock au début de la semaine
        # On simplifie ou on garde, mais on peut aussi filtrer
        start_stock_query = f"""
            SELECT item_id, total_quantity
            FROM price_history
            WHERE realm_id = ?
            AND recorded_at >= datetime('now', '-7 days')
            {item_filter_sql}
            AND (item_id, recorded_at) IN (
                SELECT item_id, MIN(recorded_at)
                FROM price_history
                WHERE realm_id = ? AND recorded_at >= datetime('now', '-7 days')
                {item_filter_sql}
                GROUP BY item_id
            )
        """
        params_start_stock = [realm_id] + item_filter_params + [realm_id] + item_filter_params
        cursor.execute(start_stock_query, params_start_stock)
        
        start_stock = {}
        for row in cursor.fetchall():
            start_stock[row["item_id"]] = row["total_quantity"] or 0
        
        conn.close()
        
        # On utilise sales_volume (sales_3d) comme métrique principale de volume
        
        # Calculer les craft costs en batch (optimisé pour les items filtrés)
        # item_ids déjà calculé plus haut
        if use_item_filter:
            craft_costs = self._batch_calculate_craft_costs(realm_id, item_ids)
        else:
            craft_costs = self._batch_calculate_craft_costs(realm_id, None)
        
        # 4. Calculer Profits et Scores
        results = []
        
        # Constantes pour la normalisation du score (Score Absolu)
        # Ajusté suite au feedback user : 10k PO et 500 ventes/3j
        TARGET_MAX_PROFIT = 10000 * 10000 # 10k gold
        TARGET_MAX_VOLUME = 500 # 500 ventes sur 3 jours (~160/jour)
        
        results = []
        
        for row in recipe_items:
            item_id = row["crafted_item_id"]
            craft_cost = craft_costs.get(item_id, 0)
            sell_price = sell_prices.get(item_id, 0)
            volume = sales_volume.get(item_id, 0)
            cancels = cancel_counts.get(item_id, 0)
            
            # Calculs de base
            profit = (sell_price - craft_cost) if sell_price and craft_cost else None
            profit_margin = ((profit / craft_cost) * 100) if profit and craft_cost > 0 else None
            
            # Calcul du Score Absolu
            score = 0
            if profit and profit > 0:
                # Normalisation Profit (linéaire bornée)
                p_score = min(profit, TARGET_MAX_PROFIT) / TARGET_MAX_PROFIT
                
                # Normalisation Volume (linéaire bornée)
                v_score = min(volume, TARGET_MAX_VOLUME) / TARGET_MAX_VOLUME
                
                # Pondération : 70% Profit, 30% Volume
                score = (p_score * 70) + (v_score * 30)
                
                # Bonus margin (petit boost jusqu'à +10 si margin > 20%)
                if profit_margin and profit_margin > 20:
                     score += min((profit_margin - 20) / 2, 10)
                     
                score = min(score, 100) # Cape à 100
            else:
                score = 0 # No profit (was -1000)
            
            results.append({
                "item_id": item_id,
                "name": row["name"],
                "icon_url": row["icon_url"],
                "category": row["category"],
                "profession_id": row["profession_id"],
                "profession_name": row["profession_name"],
                "expansion": row["expansion"],
                "craft_cost": craft_cost if craft_cost > 0 else None,
                "sell_price": sell_price if sell_price else None,
                "profit": profit,
                "profit_margin": round(profit_margin, 1) if profit_margin else None,
                "volume": volume,
                "cancels_3d": cancels,
                "score": score
            })
            
        # Trier par score décroissant
        results.sort(key=lambda x: x["score"] or 0, reverse=True)
        
        return results
    
    def get_item_profit_by_realm(self, item_id: int) -> List[Dict]:
        """
        Récupère le profit potentiel d'un item sur tous les serveurs.
        
        Returns:
            Liste de dicts triés par score: realm_id, realm_name, sell_price, profit, volume (traded), score
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Récupérer les prix de vente actuels et le min price sur 3 jours
        cursor.execute("""
            WITH Latest AS (
                SELECT realm_id, total_quantity, min_price,
                       ROW_NUMBER() OVER (PARTITION BY realm_id ORDER BY recorded_at DESC) as rn
                FROM price_history
                WHERE item_id = ?
            ),
            MinPrice3Days AS (
                SELECT realm_id, MIN(min_price) as min_price_3d
                FROM price_history
                WHERE item_id = ? AND recorded_at >= datetime('now', '-3 days')
                GROUP BY realm_id
            )
            SELECT l.realm_id, r.name as realm_name, 
                   COALESCE(mp.min_price_3d, l.min_price) as min_price, 
                   l.total_quantity
            FROM Latest l
            JOIN realms r ON l.realm_id = r.realm_id
            LEFT JOIN MinPrice3Days mp ON l.realm_id = mp.realm_id
            WHERE l.rn = 1
        """, (item_id, item_id))
        
        realm_current = {}
        for row in cursor.fetchall():
            realm_current[row["realm_id"]] = {
                "realm_name": row["realm_name"],
                "min_price": row["min_price"],
                "current_stock": row["total_quantity"] or 0,
            }
        
        # Récupérer le stock au début de la semaine pour chaque serveur
        cursor.execute("""
            SELECT realm_id, total_quantity
            FROM price_history
            WHERE item_id = ?
            AND recorded_at >= datetime('now', '-7 days')
            AND (realm_id, recorded_at) IN (
                SELECT realm_id, MIN(recorded_at)
                FROM price_history
                WHERE item_id = ? AND recorded_at >= datetime('now', '-7 days')
                GROUP BY realm_id
            )
        """, (item_id, item_id))
        
        start_stock = {}
        for row in cursor.fetchall():
            start_stock[row["realm_id"]] = row["total_quantity"] or 0
        
        conn.close()
        
        # Calculer le craft cost (utilise realm_id=0 pour commodities régionales)
        craft_cost = self.calculate_craft_cost(item_id, 0)
        
        results = []
        for realm_id, data in realm_current.items():
            sell_price = data["min_price"]
            current = data["current_stock"]
            start = start_stock.get(realm_id, 0)
            # Volume vendu = réduction du stock (max 0)
            volume = max(0, start - current)
            
            profit = (sell_price - craft_cost) if sell_price and craft_cost else None
            
            # Penalize zero volume effectively
            if profit and profit > 0:
                if volume > 0:
                    score = profit * volume
                else:
                    score = -1.0 # Penalized for zero volume despite potential profit
            else:
                score = -1000.0 # No profit or invalid data
            
            results.append({
                "realm_id": realm_id,
                "realm_name": data["realm_name"],
                "sell_price": sell_price,
                "profit": profit,
                "volume": volume,
                "score": score,
            })
        
        # Trier par score décroissant (profit × volume)
        results.sort(key=lambda x: x["score"] or 0, reverse=True)
        
        return results
    
    def calculate_craft_cost(self, item_id: int, realm_id: int) -> Optional[int]:
        """
        Calcule le coût de craft d'un item basé sur les prix AH des composants.
        Utilise les prix régionaux (commodities, realm_id=0) si pas de prix local.
        
        Returns:
            Le coût total en copper, ou None si pas de recette
        """
        # 1. Récupérer la recette de l'item
        recipe = self.get_recipe_for_item(item_id)
        if not recipe:
            return None
        
        # 2. Récupérer les composants
        reagents = self.get_recipe_reagents(recipe["recipe_id"])
        if not reagents:
            return None
        
        # 3. Calculer le coût total (somme des composants disponibles)
        total_cost = 0
        
        for reagent in reagents:
            reagent_item_id = reagent["reagent_item_id"]
            quantity = reagent["quantity"]
            
            price_data = None
            
            # Essayer d'abord le prix local du serveur (si realm_id != 0)
            if realm_id != 0:
                price_data = self.get_current_price(reagent_item_id, realm_id)
            
            # Si pas de prix local, essayer le prix régional (commodities)
            if not price_data or not price_data.get("min_price"):
                price_data = self.get_current_price(reagent_item_id, 0)  # realm_id=0 = regional
            
            # Si toujours pas de prix, chercher n'importe quel prix disponible
            if not price_data or not price_data.get("min_price"):
                price_data = self._get_any_price(reagent_item_id)
            
            if price_data and price_data.get("min_price"):
                total_cost += price_data["min_price"] * quantity
            # Sinon on ignore ce composant (ex: bois qui n'est pas achetable)
        
        return total_cost if total_cost > 0 else None
    
    def _get_any_price(self, item_id: int) -> Optional[Dict]:
        """Récupère n'importe quel prix disponible pour un item (dernier prix enregistré)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT min_price, avg_price, realm_id
            FROM price_history
            WHERE item_id = ?
            ORDER BY recorded_at DESC
            LIMIT 1
        """, (item_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"min_price": row["min_price"], "avg_price": row["avg_price"]}
        return None
    
    # ========== PET METHODS ==========
    
    def save_pet(self, pet_id: int, name: str, icon_url: str = None, 
                 source: str = None, creature_type: str = None, creature_id: int = None, is_tradable: bool = True):
        """Sauvegarde ou met à jour un pet"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        norm_name = self._normalize_text(name)
        
        cursor.execute("""
            INSERT INTO pets 
            (pet_id, name, icon_url, source, creature_type, creature_id, is_tradable, name_normalized)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pet_id) DO UPDATE SET
                name = excluded.name,
                icon_url = COALESCE(excluded.icon_url, pets.icon_url),
                source = excluded.source,
                creature_type = excluded.creature_type,
                creature_id = excluded.creature_id,
                is_tradable = excluded.is_tradable,
                name_normalized = excluded.name_normalized
        """, (pet_id, name, icon_url, source, creature_type, creature_id, is_tradable, norm_name))
        
        conn.commit()
        conn.close()

    def save_pets_batch(self, pets_data: List[Dict]):
        """Sauvegarde une liste de pets en une seule transaction"""
        if not pets_data:
            return
            
        # Pre-normalize
        for p in pets_data:
            p["name_normalized"] = self._normalize_text(p.get("name", ""))
            
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Use INSERT ON CONFLICT to preserve existing icon_url if new value is NULL
            cursor.executemany("""
                INSERT INTO pets 
                (pet_id, name, icon_url, source, creature_type, creature_id, is_tradable, name_normalized)
                VALUES (:pet_id, :name, :icon_url, :source, :creature_type, :creature_id, :is_tradable, :name_normalized)
                ON CONFLICT(pet_id) DO UPDATE SET
                    name = excluded.name,
                    icon_url = COALESCE(excluded.icon_url, pets.icon_url),
                    source = excluded.source,
                    creature_type = excluded.creature_type,
                    creature_id = excluded.creature_id,
                    is_tradable = excluded.is_tradable,
                    name_normalized = excluded.name_normalized
            """, pets_data)
            conn.commit()
        except Exception as e:
            print(f"Error in batch save pets: {e}")
        finally:
            conn.close()

    def get_pets_summary(self, realm_id: int, search_query: str = None, 
                        source_filter: List[str] = None, creature_type: str = None, tradable_only: bool = False,
                        sort_by: str = "min_price", sort_order: str = "desc",
                        limit: int = 50, offset: int = 0) -> Tuple[List[Dict], int]:
        """
        Récupère un résumé des pets avec filtres, tri et pagination SQL.
        OPTIMISÉ : Join correct pour éviter le full scan.
        Retourne (items, total_count).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Base Query Conditions
        where_conditions = ["1=1"]
        params = []
        
        if search_query:
            where_conditions.append("p.name_normalized LIKE ?")
            params.append(f"%{self._normalize_text(search_query)}%")
            
        if creature_type:
            where_conditions.append("p.creature_type = ?")
            params.append(creature_type)
            
        if tradable_only:
            where_conditions.append("COALESCE(p.is_tradable, 1) = 1")

        if source_filter:
            source_conditions = []
            for s in source_filter:
                source_conditions.append("p.source LIKE ?")
                params.append(f"%{s}%")
            if source_conditions:
                where_conditions.append(f"({' OR '.join(source_conditions)})")
        
        where_clause = " AND ".join(where_conditions)
        
        # 2. Get Total Count
        count_query = f"SELECT COUNT(*) as total FROM pets p WHERE {where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()["total"]
        
        if total_count == 0:
            conn.close()
            return [], 0
            
        # 3. Main Query
        
        direction = "ASC" if sort_order == "asc" else "DESC"
        sort_column = "lp.min_price" # default
        
        if sort_by == "name":
            sort_column = "fp.name"
        elif sort_by == "level":
            sort_column = "lp.level"
        elif sort_by == "quality":
            sort_column = "lp.quality_id"
        else: # min_price
            sort_column = "lp.min_price"
            
        if sort_by == "name":
            sort_expression = f"fp.name_normalized {direction}"
        else:
            sort_expression = f"CASE WHEN {sort_column} IS NULL THEN 1 ELSE 0 END, {sort_column} {direction}, fp.name_normalized ASC"
        
        # Optimization Strategy similar to items:
        # If sort by Name, apply limit/offset in filtered_pets CTE.
        
        filtered_pets_sql = f"""
            SELECT pet_id, name, icon_url, source, creature_type, creature_id, is_tradable, name_normalized
            FROM pets p
            WHERE {where_clause}
        """
        
        query_params = list(params)
        
        if sort_by == "name":
            # Just use base filtered_pets_sql
            pass
            
        query = f"""
        WITH filtered_pets AS (
            {filtered_pets_sql}
        ),
        latest_prices_lookup AS (
             SELECT fp.pet_id, MAX(ph.recorded_at) as max_date
             FROM filtered_pets fp
             JOIN pet_price_history ph ON fp.pet_id = ph.pet_id
             WHERE ph.realm_id = ?
             GROUP BY fp.pet_id
        ),
        latest_prices AS (
            SELECT 
                ph.pet_id, ph.min_price, ph.total_quantity, ph.quality_id, ph.level, ph.recorded_at
            FROM latest_prices_lookup lpl
            JOIN pet_price_history ph 
                ON lpl.pet_id = ph.pet_id 
                AND lpl.max_date = ph.recorded_at
                AND ph.realm_id = ?
        ),
        sales_3d AS (
            SELECT 
                fp.pet_id,
                SUM(ph.estimated_sales) as sales_3d
            FROM filtered_pets fp
            JOIN pet_price_history ph ON fp.pet_id = ph.pet_id
            WHERE ph.realm_id = ? AND ph.recorded_at >= datetime('now', '-3 days')
            GROUP BY fp.pet_id
        ),
        min_price_3d AS (
             SELECT 
                fp.pet_id,
                MIN(ph.min_price) as min_price_3d
            FROM filtered_pets fp
            JOIN pet_price_history ph ON fp.pet_id = ph.pet_id
            WHERE ph.realm_id = ? AND ph.recorded_at >= datetime('now', '-3 days')
            GROUP BY fp.pet_id
        ),
        cancels_3d AS (
            SELECT 
                fp.pet_id,
                SUM(COALESCE(ph.estimated_cancels, 0)) as cancels_3d
            FROM filtered_pets fp
            JOIN pet_price_history ph ON fp.pet_id = ph.pet_id
            WHERE ph.realm_id = ? AND ph.recorded_at >= datetime('now', '-3 days')
            GROUP BY fp.pet_id
        )
        SELECT 
            fp.pet_id, fp.name, fp.icon_url, fp.source, fp.creature_type, fp.creature_id, 
            COALESCE(fp.is_tradable, 1) as is_tradable,
            lp.min_price, lp.total_quantity, lp.quality_id, lp.level,
            COALESCE(s3.sales_3d, 0) as sales_3d,
            COALESCE(mp3.min_price_3d, lp.min_price) as min_price_3d,
            COALESCE(c3.cancels_3d, 0) as cancels_3d,
            fp.name_normalized
        FROM filtered_pets fp
        LEFT JOIN latest_prices lp ON fp.pet_id = lp.pet_id
        LEFT JOIN sales_3d s3 ON fp.pet_id = s3.pet_id
        LEFT JOIN min_price_3d mp3 ON fp.pet_id = mp3.pet_id
        LEFT JOIN cancels_3d c3 ON fp.pet_id = c3.pet_id
        ORDER BY {sort_expression}
        """
        
        # Add realm params (5 times now)
        query_params.extend([realm_id, realm_id, realm_id, realm_id, realm_id])
        
        if sort_by == "name":
             query += " LIMIT ? OFFSET ?" 
             query_params.extend([limit, offset])
        else:
            query += " LIMIT ? OFFSET ?"
            query_params.extend([limit, offset])
        
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows], total_count


    def get_pet_all_realms_prices(self, pet_id: int) -> List[Dict]:
        """Récupère les derniers prix d'un pet sur tous les serveurs avec ventes 3j et cancels"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Date 3 jours en arrière pour le calcul des ventes
        date_3d = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            SELECT r.realm_id, r.name as realm_name, r.population, r.region,
                   ph.min_price, ph.total_quantity, ph.quality_id, ph.level, ph.recorded_at,
                   COALESCE(sales.sales_3d, 0) as sales_3d,
                   COALESCE(mp3.min_price_3d, ph.min_price) as min_price_3d,
                   COALESCE(cancels.cancels_3d, 0) as cancels_3d
            FROM realms r
            LEFT JOIN (
                SELECT realm_id, min_price, total_quantity, quality_id, level, recorded_at,
                       ROW_NUMBER() OVER (PARTITION BY realm_id ORDER BY recorded_at DESC) as rn
                FROM pet_price_history
                WHERE pet_id = ?
            ) ph ON r.realm_id = ph.realm_id AND ph.rn = 1
            LEFT JOIN (
                SELECT realm_id, SUM(estimated_sales) as sales_3d
                FROM pet_price_history
                WHERE pet_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            ) sales ON r.realm_id = sales.realm_id
            LEFT JOIN (
                SELECT realm_id, MIN(min_price) as min_price_3d
                FROM pet_price_history
                WHERE pet_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            ) mp3 ON r.realm_id = mp3.realm_id
            LEFT JOIN (
                SELECT realm_id, SUM(COALESCE(estimated_cancels, 0)) as cancels_3d
                FROM pet_price_history
                WHERE pet_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            ) cancels ON r.realm_id = cancels.realm_id
            ORDER BY CASE WHEN ph.min_price IS NULL THEN 1 ELSE 0 END, ph.min_price ASC
        """, (pet_id, pet_id, date_3d, pet_id, date_3d, pet_id, date_3d))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_pet_price_history(self, pet_id: int, realm_id: int, days: int = 21) -> List[Dict]:
        """Récupère l'historique des prix des pets sur une période donnée"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            SELECT min_price, avg_price, total_quantity, quality_id, level, recorded_at
            FROM pet_price_history
            WHERE pet_id = ? AND realm_id = ? AND recorded_at >= ?
            ORDER BY recorded_at ASC
        """, (pet_id, realm_id, since))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    def get_pet_best_sales_candidates(self, pet_id: int, days: int = 3) -> List[Dict]:
        """
        Récupère les données consolidées pour les meilleures ventes de pets (prix min sur X jours).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            WITH Latest AS (
                SELECT realm_id, total_quantity, min_price,
                       ROW_NUMBER() OVER (PARTITION BY realm_id ORDER BY recorded_at DESC) as rn
                FROM pet_price_history
                WHERE pet_id = ?
            ),
            Sales3D AS (
                SELECT 
                    realm_id,
                    SUM(estimated_sales) as sales_3d
                FROM pet_price_history
                WHERE pet_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            ),
            MinPriceWindow AS (
                SELECT realm_id, MIN(min_price) as min_price_window
                FROM pet_price_history
                WHERE pet_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            )
            SELECT 
                r.name as realm_name,
                r.population,
                r.region,
                l.realm_id,
                COALESCE(mp.min_price_window, l.min_price) as min_price,
                l.total_quantity,
                COALESCE(s.sales_3d, 0) as sales_3d
            FROM Latest l
            JOIN realms r ON l.realm_id = r.realm_id
            LEFT JOIN MinPriceWindow mp ON l.realm_id = mp.realm_id
            LEFT JOIN Sales3D s ON l.realm_id = s.realm_id
            WHERE l.rn = 1
        """, (pet_id, start_date, pet_id, start_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_pets(self) -> List[Dict]:
        """Récupère tous les pets"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pet_id, name, icon_url, source, creature_type, creature_id, is_tradable
            FROM pets
            ORDER BY name
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_pet_ids(self) -> set:
        """Récupère les IDs de tous les pets connus"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pet_id FROM pets")
        rows = cursor.fetchall()
        conn.close()
        return {row["pet_id"] for row in rows}
    
    def should_resync_pets(self, max_age_days: int = 30) -> bool:
        """Vérifie si les pets doivent être re-synchronisés (données absentes ou trop anciennes)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count, MAX(added_at) as last_sync FROM pets")
        row = cursor.fetchone()
        conn.close()
        
        if row["count"] == 0:
            return True  # Pas de pets
        
        if row["last_sync"]:
            try:
                last_sync = datetime.fromisoformat(str(row["last_sync"]).replace("Z", "+00:00"))
                if last_sync.tzinfo:
                    last_sync = last_sync.replace(tzinfo=None)
                age = datetime.now() - last_sync
                return age.days >= max_age_days
            except (ValueError, TypeError):
                return True
        
        return True
    
    def record_pet_price(self, pet_id: int, realm_id: int, min_price: int,
                         avg_price: float, total_quantity: int, 
                         quality_id: int = None, level: int = None):
        """Enregistre les données de prix pour un pet sur un serveur"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pet_price_history 
            (pet_id, realm_id, min_price, avg_price, total_quantity, quality_id, level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (pet_id, realm_id, min_price, avg_price, total_quantity, quality_id, level))
        
        conn.commit()
        conn.close()

        conn.commit()
        conn.close()

    def batch_record_pet_prices(self, pet_data_list: List[Tuple]):
        """
        Enregistre un lot de données de prix pour les pets.
        Format: [(pet_id, realm_id, min_price, avg_price, total_quantity, quality_id, level, estimated_sales, estimated_cancels), ...]
        """
        if not pet_data_list:
            return
            
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.executemany("""
            INSERT INTO pet_price_history 
            (pet_id, realm_id, min_price, avg_price, total_quantity, quality_id, level, estimated_sales, estimated_cancels)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, pet_data_list)
        
        conn.commit()
        conn.close()
    
    
    def get_pets_without_icons(self, limit: int = 50) -> List[Dict]:
        """Récupère les pets sans icône"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pet_id, name FROM pets 
            WHERE icon_url IS NULL OR icon_url = ''
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def update_pet_icon(self, pet_id: int, icon_url: str):
        """Met à jour l'icône d'un pet"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pets SET icon_url = ? WHERE pet_id = ?
        """, (icon_url, pet_id))
        conn.commit()
        conn.close()
    
    def cleanup_old_pet_data(self, days: int = 7):
        """Supprime les données de prix pets de plus de X jours"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            DELETE FROM pet_price_history WHERE recorded_at < ?
        """, (cutoff,))
        
        conn.commit()
        conn.close()


# Instance singleton
_data_manager: Optional[DataManager] = None


def get_data_manager() -> DataManager:
    """Retourne l'instance singleton du gestionnaire de données"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager
