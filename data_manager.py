"""
Gestionnaire de données pour le stockage et le calcul des métriques
Utilise SQLite pour stocker l'historique des prix et volumes
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from config import DATABASE_PATH, TREND_WEEKS


class DataManager:
    """
    Gestionnaire de données SQLite pour l'historique des prix et volumes
    """
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Crée une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialise les tables de la base de données"""
        conn = self._get_connection()
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
            # La colonne existe déjà, ignorer l'erreur
            pass
        
        conn.commit()
        conn.close()
    
    def save_realm(self, realm_id: int, name: str, population: str = None):
        """Sauvegarde ou met à jour un serveur"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO realms (realm_id, name, population, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (realm_id, name, population))
        
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
        
        cursor.execute("""
            INSERT OR REPLACE INTO housing_items (item_id, name, icon_url, category, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (item_id, name, icon_url, category))
        
        conn.commit()
        conn.close()
    
    def get_housing_items(self) -> List[Dict]:
        """Récupère tous les items de housing"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_id, name, icon_url, category 
            FROM housing_items 
            ORDER BY name
        """)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
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
        """Récupère les derniers prix d'un item sur tous les serveurs"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Sous-requête pour obtenir le dernier enregistrement par serveur
        cursor.execute("""
            SELECT 
                r.realm_id,
                r.name as realm_name,
                r.population,
                ph.min_price,
                ph.avg_price,
                ph.total_quantity,
                ph.auction_count,
                ph.recorded_at
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
            ORDER BY r.name
        """, (item_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_items_summary(self, realm_id: int) -> List[Dict]:
        """
        Récupère un résumé de tous les items de housing avec leurs métriques
        pour un serveur donné.
        Version optimisée : utilise une seule requête SQL au lieu de boucler.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Date il y a 7 et 21 jours pour les calculs
        # Note: SQLite 'now' est UTC.
        
        query = """
            WITH latest_prices AS (
                SELECT 
                    item_id, min_price, avg_price, total_quantity, auction_count, recorded_at,
                    ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY recorded_at DESC) as rn
                FROM price_history
                WHERE realm_id = ?
            ),
            historical_stats AS (
                SELECT 
                    item_id,
                    AVG(avg_price) as hist_avg_price
                FROM price_history
                WHERE realm_id = ? AND recorded_at >= datetime('now', '-21 days')
                GROUP BY item_id
            ),
            week_start_volume AS (
                SELECT 
                    item_id, total_quantity as start_quantity,
                    ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY recorded_at ASC) as rn
                FROM price_history
                WHERE realm_id = ? AND recorded_at >= datetime('now', '-7 days')
            )
            SELECT 
                hi.item_id,
                hi.name,
                hi.icon_url,
                hi.category,
                lp.min_price,
                lp.avg_price,
                lp.total_quantity,
                lp.auction_count,
                lp.recorded_at,
                hs.hist_avg_price,
                wsv.start_quantity
            FROM housing_items hi
            LEFT JOIN latest_prices lp ON hi.item_id = lp.item_id AND lp.rn = 1
            LEFT JOIN historical_stats hs ON hi.item_id = hs.item_id
            LEFT JOIN week_start_volume wsv ON hi.item_id = wsv.item_id AND wsv.rn = 1
            ORDER BY hi.name
        """
        
        cursor.execute(query, (realm_id, realm_id, realm_id))
        rows = cursor.fetchall()
        conn.close()
        
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
                "trend": None,
                "volume_change": None
            }
            
            # Calcul Trend (en Python car plus simple pour les arrondis/nulls)
            current_avg = row["avg_price"]
            hist_avg = row["hist_avg_price"]
            
            if current_avg and hist_avg and hist_avg > 0:
                item["trend"] = round(((current_avg - hist_avg) / hist_avg) * 100, 1)
            
            # Calcul Volume Change
            current_qty = row["total_quantity"]
            start_qty = row["start_quantity"]
            
            if current_qty is not None and start_qty is not None:
                item["volume_change"] = current_qty - start_qty
            
            items.append(item)
        
        return items
    
    def cleanup_old_data(self, days: int = 30):
        """Supprime les données de plus de X jours"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            DELETE FROM price_history WHERE recorded_at < ?
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


# Instance singleton
_data_manager: Optional[DataManager] = None


def get_data_manager() -> DataManager:
    """Retourne l'instance singleton du gestionnaire de données"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager
