"""
Configuration de l'application WoW Housing Price Tracker
"""
import os
from dotenv import load_dotenv

# Charger les variables d'environnement du fichier .env
load_dotenv()

# Credentials Blizzard API
BLIZZARD_CLIENT_ID = os.getenv("BLIZZARD_CLIENT_ID", "")
BLIZZARD_CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET", "")

# Configuration API Blizzard - Région EU
API_REGION = "eu"
API_BASE_URL = f"https://{API_REGION}.api.blizzard.com"
AUTH_URL = "https://oauth.battle.net/token"

# Namespace pour les données dynamiques (auction house)
DYNAMIC_NAMESPACE = f"dynamic-{API_REGION}"
# Namespace pour les données statiques (items, decor)
STATIC_NAMESPACE = f"static-{API_REGION}"

# Locale par défaut
DEFAULT_LOCALE = "fr_FR"

# Configuration de la base de données
# Utilise le dossier data/ pour Docker, sinon le répertoire courant
# Utilise le dossier data/ pour Docker, sinon le répertoire courant (parent de backend)
import os as _os
# Check for Docker volume mount at /app/data or local backend/data
_data_dir = _os.path.join(_os.path.dirname(__file__), "data")
# Check for parent dir (project root)
_root_dir = _os.path.dirname(_os.path.dirname(__file__))

if _os.path.isdir(_data_dir):
    DATABASE_PATH = _os.getenv("DATABASE_PATH", _os.path.join(_data_dir, "housing_data.db"))
else:
    # Fallback to root directory for local dev
    DATABASE_PATH = _os.getenv("DATABASE_PATH", _os.path.join(_root_dir, "housing_data.db"))

# Configuration du cache
CACHE_DURATION_HOURS = 1  # Durée de validité du cache des auctions
ITEMS_CACHE_DURATION_HOURS = 24  # Durée de validité du cache des items

# Configuration des tendances
TREND_WEEKS = 3  # Nombre de semaines pour calculer la tendance

# Serveur par défaut (None = premier de la liste, ou spécifier le nom exact)
# Exemples: "Hyjal", "Archimonde", "Ysondre"
DEFAULT_REALM_NAME = os.getenv("DEFAULT_REALM", None)
