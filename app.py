"""
WoW Housing Item Price Tracker
Application Streamlit pour suivre les prix des items de housing World of Warcraft
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
from typing import Dict, List, Optional

from blizzard_api import get_api, BlizzardAPIError
from data_manager import get_data_manager
from update_manager import UpdateManager

# Configuration de la page
st.set_page_config(
    page_title="WoW Housing Price Tracker",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FFD100;
        text-align: center;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    .item-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid #FFD100;
    }
    .price-up {
        color: #00ff00;
    }
    .price-down {
        color: #ff4444;
    }
    .price-stable {
        color: #888888;
    }
    .metric-card {
        background: rgba(255, 209, 0, 0.1);
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .stSelectbox > div > div {
        background-color: #1a1a2e;
    }
</style>
""", unsafe_allow_html=True)


def format_time_diff(dt_str) -> str:
    """Formate la différence de temps (ex: 'Il y a 5 min')"""
    if not dt_str:
        return "-"
    
    try:
        if isinstance(dt_str, str):
            # Tenter de parser ISO
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        else:
            dt = dt_str
            
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "< 1 min"
        elif seconds < 3600:
            return f"{int(seconds // 60)} min"
        elif seconds < 86400:
            return f"{int(seconds // 3600)} h"
        else:
            return f"{int(seconds // 86400)} j"
            
    except Exception:
        return ""


def format_gold(copper_value: Optional[int]) -> str:
    """Formate une valeur en copper vers gold/silver/copper"""
    if copper_value is None:
        return "N/A"
    
    # Gérer les valeurs NaN (float)
    try:
        import math
        if math.isnan(float(copper_value)):
            return "N/A"
    except (TypeError, ValueError):
        pass
    
    copper_value = int(copper_value)
    gold = copper_value // 10000
    silver = (copper_value % 10000) // 100
    copper = copper_value % 100
    
    parts = []
    if gold > 0:
        parts.append(f"{gold:,}g")
    if silver > 0:
        parts.append(f"{silver}s")
    if copper > 0 or not parts:
        parts.append(f"{copper}c")
    
    return " ".join(parts)


def format_trend(trend: Optional[float]) -> str:
    """Formate la tendance avec une couleur appropriée"""
    if trend is None:
        return "📊 N/A"
    
    # Gérer les valeurs NaN
    try:
        import math
        if math.isnan(float(trend)):
            return "📊 N/A"
    except (TypeError, ValueError):
        pass
    
    if trend > 5:
        return f"📈 +{trend:.1f}%"
    elif trend < -5:
        return f"📉 {trend:.1f}%"
    else:
        return f"➡️ {trend:.1f}%"


def get_trend_color(trend: Optional[float]) -> str:
    """Retourne la couleur basée sur la tendance"""
    if trend is None:
        return "gray"
    if trend > 5:
        return "green"
    elif trend < -5:
        return "red"
    return "orange"


def initialize_session_state():
    """Initialise les variables de session"""
    if "selected_realm_id" not in st.session_state:
        st.session_state.selected_realm_id = None
    if "selected_item_id" not in st.session_state:
        st.session_state.selected_item_id = None
    if "realms_loaded" not in st.session_state:
        st.session_state.realms_loaded = False
    if "items_loaded" not in st.session_state:
        st.session_state.items_loaded = False


def load_realms():
    """Charge la liste des serveurs depuis l'API"""
    try:
        api = get_api()
        dm = get_data_manager()
        
        # Essayer de charger depuis la base de données d'abord
        cached_realms = dm.get_realms()
        if cached_realms:
            return cached_realms
        
        # Sinon, charger depuis l'API
        with st.spinner("Chargement des serveurs depuis l'API Blizzard..."):
            realms = api.get_all_realms_with_names()
            
            # Sauvegarder dans la base de données
            for realm in realms:
                dm.save_realm(realm["id"], realm["name"])
            
            return realms
            
    except BlizzardAPIError as e:
        st.error(f"Erreur API: {str(e)}")
        return []


@st.cache_data(ttl=3600)  # Cache 1h pour éviter de taper la DB à chaque refresh
def get_housing_items_from_db():
    dm = get_data_manager()
    return dm.get_housing_items()


def fetch_missing_icons(batch_size: int = 30):
    """
    Récupère les icônes manquantes pour les items et les cache en DB.
    Appelé en arrière-plan à chaque chargement de page.
    """
    dm = get_data_manager()
    api = get_api()
    
    # Récupérer les items sans icône
    items_without_icons = dm.get_items_without_icons(limit=batch_size)
    
    if not items_without_icons:
        return 0  # Tous les items ont déjà une icône
    
    fetched_count = 0
    
    for item in items_without_icons:
        item_id = item["item_id"]
        try:
            # Appeler l'API Blizzard pour récupérer les médias
            media_data = api.get_item_media(item_id)
            
            # Extraire l'URL de l'icône
            assets = media_data.get("assets", [])
            icon_url = None
            
            for asset in assets:
                if asset.get("key") == "icon":
                    icon_url = asset.get("value")
                    break
            
            if icon_url:
                # Sauvegarder en base
                dm.update_icon_url(item_id, icon_url)
                fetched_count += 1
            else:
                # Marquer comme "pas d'icône" pour ne pas re-essayer
                dm.update_icon_url(item_id, "NONE")
                
        except Exception as e:
            # En cas d'erreur, on continue avec les autres items
            print(f"Error fetching icon for item {item_id}: {e}")
            continue
    
    # Vider le cache pour que les nouvelles icônes apparaissent
    if fetched_count > 0:
        get_housing_items_from_db.clear()
    
    return fetched_count


def load_housing_items():
    """
    Charge les items de housing depuis l'API Blizzard
    Inclut les decor items et les fixtures
    """
    dm = get_data_manager()
    
    # Vérifier si des items existent déjà en cache DB
    existing_items = get_housing_items_from_db()
    
    if existing_items:
        # Vérifier si on a des anciens IDs de decor (petits nombres ou hack 1000000+)
        has_bad_ids = any(i['item_id'] < 20000 or i['item_id'] > 900000 for i in existing_items)
        
        # Vérifier si on a des items de TWW (IDs > 240000)
        has_new_items = any(i['item_id'] > 240000 for i in existing_items)
        
        # On force le rechargement SEULEMENT si on a une liste manifestement incomplète
        # (moins de 1000 items OU absence d'items récents)
        is_incomplete = len(existing_items) < 1000 or not has_new_items
        
        if not has_bad_ids and not is_incomplete:
            return existing_items
        
        # Si on doit recharger, on vide le cache mémoire et la table
        get_housing_items_from_db.clear()
        if has_bad_ids or is_incomplete:
            dm.clear_housing_items()
    
    # Si on arrive ici, c'est qu'il faut charger depuis l'API
    try:
        api = get_api()
        
        with st.spinner("Chargement des items de housing depuis l'API Blizzard..."):
            # Rechercher tous les items de classe Housing (20)
            housing_items = api.search_housing_items()
            
            # Si on trouve des nouveaux items, on vide potentiellement la table pour éviter les doublons ID Decor vs Item ID
            # Cependant, truncate_items n'existe pas dans data_manager pour l'instant.
            # On va assumer que si le nombre d'items change drastiquement ou si les IDs changent, ça ira.
            # Mais attention: les IDs Decor étaient petits (ex: 530), les IDs Items sont grands (ex: 236678)
            
            items_loaded = 0
            
            for item in housing_items:
                # Structure attendue du search API: {'key': {'href': '...'}, 'data': {'name': {'en_US': '...'}, 'id': 123}}
                # Mais blizzard_api._make_request renvoie response.json(), et search_housing_items retourne data.get("results")
                # Les results du search sont sous forme: {"key": {"href": "..."}, "data": {"name": {"en_US": "Name"}, "id": 123}}
                
                # Attention: blizzard_api.py renvoie la liste 'results' brute.
                data = item.get("data", {})
                item_id = data.get("id")
                
                # Gestion du nom multivalue
                name_data = data.get("name", {})
                if isinstance(name_data, dict):
                    name = name_data.get("fr_FR") or name_data.get("en_US") or f"Item {item_id}"
                else:
                    name = str(name_data)
                
                if item_id:
                    dm.save_housing_item(item_id, name, category="Housing")
                    items_loaded += 1
            
            if items_loaded > 0:
                st.success(f"✅ {items_loaded} items de housing chargés!")
            
        return dm.get_housing_items()
        
    except BlizzardAPIError as e:
        st.warning(f"Impossible de charger les items depuis l'API: {str(e)}")
        # Fallback avec quelques items d'exemple
        sample_items = [
            {"item_id": 530, "name": "Stormwind Interior Doorway", "category": "Décoration"},
            {"item_id": 531, "name": "Gilded Mirror", "category": "Décoration"},
            {"item_id": 532, "name": "Ornate Bookshelf", "category": "Décoration"},
        ]
        for item in sample_items:
            dm.save_housing_item(item["item_id"], item["name"], category=item["category"])
        return dm.get_housing_items()








@st.cache_resource
def get_update_manager():
    """Retourne l'instance singleton du gestionnaire de mise à jour"""
    return UpdateManager()


@st.fragment(run_every=3)
def render_update_progress():
    """Affiche la progression de la mise à jour (rafraîchi toutes les 3s via fragment)"""
    mgr = get_update_manager()
    if mgr.is_running():
        st.warning(f"🔄 {mgr.status_message}")
        st.progress(mgr.progress)
    elif mgr.last_update_time:
         from datetime import datetime
         now = datetime.now()
         diff = now - mgr.last_update_time
         if diff.total_seconds() < 60:
             st.success("✅ Données à jour !")


def fetch_auction_data(realm_id: int, housing_items: List[Dict]):
    """Récupère et enregistre les données d'auction pour un serveur"""
    try:
        api = get_api()
        dm = get_data_manager()
        
        housing_item_ids = {item["item_id"] for item in housing_items}
        
        with st.spinner(f"Récupération des enchères..."):
            all_auctions = api.get_auctions(realm_id)
        
        # Filtrer les auctions de housing items
        item_auctions = {}
        for auction in all_auctions:
            item_id = auction.get("item", {}).get("id")
            if item_id in housing_item_ids:
                if item_id not in item_auctions:
                    item_auctions[item_id] = []
                item_auctions[item_id].append(auction)
        
        # Enregistrer les données
        for item_id, auctions in item_auctions.items():
            if auctions:
                prices = []
                total_quantity = 0
                
                for auction in auctions:
                    # Le prix peut être unitaire ou buyout
                    price = auction.get("buyout") or auction.get("unit_price", 0)
                    quantity = auction.get("quantity", 1)
                    
                    if price > 0:
                        prices.append(price)
                        total_quantity += quantity
                
                if prices:
                    min_price = min(prices)
                    avg_price = sum(prices) / len(prices)
                    
                    dm.record_price_data(
                        item_id=item_id,
                        realm_id=realm_id,
                        min_price=min_price,
                        avg_price=avg_price,
                        total_quantity=total_quantity,
                        auction_count=len(auctions)
                    )
        
        return True
        
    except BlizzardAPIError as e:
        st.error(f"Erreur lors de la récupération des enchères: {str(e)}")
        return False


def render_sidebar():
    """Affiche la sidebar avec la sélection du serveur et de la page"""
    
    # Sélecteur de page avec persistence via query params
    st.sidebar.markdown("## 📑 Navigation")
    
    # Grouper les pages par catégorie
    housing_pages = ["🏠 Items Housing", "💰 Profits Craft"]
    pets_pages = ["🐾 Pets", "👤 Ma Collection"]
    all_pages = housing_pages + pets_pages
    
    # Récupérer la page depuis les query params seulement si pas déjà en session
    if "current_page" not in st.session_state:
        query_page = st.query_params.get("page", None)
        if query_page:
            page_map = {"housing": "🏠 Items Housing", "craft": "💰 Profits Craft", "pets": "🐾 Pets", "collection": "👤 Ma Collection"}
            st.session_state.current_page = page_map.get(query_page, "🏠 Items Housing")
        else:
            st.session_state.current_page = "🏠 Items Housing"
    
    current_page = st.session_state.get("current_page", "🏠 Items Housing")
    
    # Section Housing
    st.sidebar.markdown("#### 🏡 Housing")
    housing_index = housing_pages.index(current_page) if current_page in housing_pages else None
    housing_page = st.sidebar.radio(
        "Housing",
        housing_pages,
        index=housing_index if housing_index is not None else 0,
        label_visibility="collapsed",
        key="housing_page_selector"
    )
    
    # Section Pets
    st.sidebar.markdown("#### 🐾 Pets")
    pets_index = pets_pages.index(current_page) if current_page in pets_pages else None
    pets_page = st.sidebar.radio(
        "Pets",
        pets_pages,
        index=pets_index if pets_index is not None else 0,
        label_visibility="collapsed",
        key="pets_page_selector"
    )
    
    # Déterminer quelle page est réellement sélectionnée
    if current_page in housing_pages:
        # L'utilisateur était sur Housing, vérifier s'il a cliqué sur Pets
        if pets_page != pets_pages[pets_index if pets_index is not None else 0] or (pets_index is None and current_page not in pets_pages):
            page = pets_page
        else:
            page = housing_page
    else:
        # L'utilisateur était sur Pets, vérifier s'il a cliqué sur Housing
        if housing_page != housing_pages[housing_index if housing_index is not None else 0] or (housing_index is None and current_page not in housing_pages):
            page = housing_page
        else:
            page = pets_page
    
    # Mettre à jour la session et les query params si changement
    if page != st.session_state.current_page:
        st.session_state.current_page = page
    
    # Sauvegarder dans query params pour persistence
    page_keys = {"🏠 Items Housing": "housing", "💰 Profits Craft": "craft", "🐾 Pets": "pets", "👤 Ma Collection": "collection"}
    st.query_params["page"] = page_keys.get(page, "housing")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("## ⚙️ Configuration")
    
    realms = load_realms()
    
    if not realms:
        st.sidebar.warning("Impossible de charger les serveurs")
        return None
    
    # Créer les options du dropdown
    realm_options = {realm["name"]: realm["id"] for realm in realms}
    realm_names = list(realm_options.keys())
    
    # Déterminer l'index par défaut
    from config import DEFAULT_REALM_NAME
    default_index = 0
    if DEFAULT_REALM_NAME and DEFAULT_REALM_NAME in realm_names:
        default_index = realm_names.index(DEFAULT_REALM_NAME)
    
    selected_realm_name = st.sidebar.selectbox(
        "🌍 Serveur de référence",
        options=realm_names,
        index=default_index,
        help="Sélectionnez le serveur à utiliser pour les données par défaut"
    )
    
    if selected_realm_name:
        st.session_state.selected_realm_id = realm_options[selected_realm_name]
    
    # Bouton pour définir comme défaut
    if st.sidebar.button("⭐ Définir comme défaut", use_container_width=True, help="Enregistre ce serveur comme défaut au prochain lancement"):
        save_default_realm(selected_realm_name)
        st.sidebar.success(f"'{selected_realm_name}' défini comme défaut!")
    
    st.sidebar.markdown("---")
    
    # Bouton pour rafraîchir les données
    if st.sidebar.button("🔄 Rafraîchir les données", use_container_width=True):
        mgr = get_update_manager()
        mgr.start_background_update(force=True)
        st.toast("Mise à jour lancée en arrière-plan !", icon="🚀")
    
    # Indicateur de mise à jour en cours (géré par fragment auto-rafraîchi)
    with st.sidebar:
        render_update_progress()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Informations")
    st.sidebar.info(
        "Les prix sont affichés en or (g), argent (s) et cuivre (c).\n\n"
        "📈 = Prix en hausse (+5%)\n"
        "📉 = Prix en baisse (-5%)\n"
        "➡️ = Prix stable\n\n"
        "**Note :** 'N/A' signifie que l'item n'est pas en vente actuellement à l'Hôtel des Ventes de ce serveur."
    )
    
    # Afficher la dernière mise à jour
    dm = get_data_manager()
    last_update = dm.get_last_price_update()
    if last_update:
        from datetime import timezone
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age = now - last_update
        minutes = int(age.total_seconds() // 60)
        if minutes < 60:
            st.sidebar.caption(f"🕒 Dernière mise à jour il y a {minutes} min")
        else:
            hours = minutes // 60
            st.sidebar.caption(f"🕒 Dernière mise à jour il y a {hours}h {minutes % 60}min")
    
    return st.session_state.selected_realm_id


def save_default_realm(realm_name: str):
    """Sauvegarde le serveur par défaut dans le fichier .env"""
    import os
    env_path = ".env"
    lines = []
    found = False
    
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # Chercher et remplacer DEFAULT_REALM
    new_lines = []
    for line in lines:
        if line.startswith("DEFAULT_REALM="):
            new_lines.append(f'DEFAULT_REALM="{realm_name}"\n')
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f'DEFAULT_REALM="{realm_name}"\n')
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


def check_startup_scan():
    """Vérifie si un scan au démarrage est nécessaire (données > 1h)"""
    dm = get_data_manager()
    
    last_update = dm.get_last_price_update()
    should_scan = False
    
    if last_update is None:
        should_scan = True
        st.info("👋 Bienvenue ! Premier démarrage détecté.")
    else:
        # Si last_update est naive, on le rend aware (timezone locale ou UTC selon DB)
        # SQLite stocke en UTC par défaut avec CURRENT_TIMESTAMP
        from datetime import timezone
        
        if last_update.tzinfo is None:
            # On assume UTC pour être safe avec la DB
            last_update = last_update.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        age = now - last_update
        
        if age.total_seconds() > 3600: # 1 heure
            should_scan = True
            st.info(f"🕒 Dernière mise à jour il y a {int(age.total_seconds()//60)} minutes.")

    if should_scan:
        mgr = get_update_manager()
        if not mgr.is_running():
            mgr.start_background_update()
            st.toast("🔄 Mise à jour des données lancée en arrière-plan...", icon="⏳")
    
    # Les icônes sont téléchargées en arrière-plan via Update Manager ou progressivement
    # check_and_download_all_icons() - Supprimé pour éviter blocage


def check_and_download_all_icons():
    """Télécharge toutes les icônes manquantes au démarrage"""
    dm = get_data_manager()
    
    # Vérifier combien d'icônes manquent
    items_without_icons = dm.get_items_without_icons(limit=9999)
    
    if not items_without_icons:
        return  # Toutes les icônes sont déjà en cache
    
    total = len(items_without_icons)
    
    # Afficher une barre de progression
    st_status = st.status(f"🖼️ Téléchargement des icônes ({total} manquantes)...", expanded=True)
    
    api = get_api()
    fetched = 0
    errors = 0
    
    progress_bar = st_status.progress(0, text=f"Icônes: 0/{total}")
    
    for i, item in enumerate(items_without_icons):
        item_id = item["item_id"]
        
        try:
            # Appeler l'API Blizzard pour récupérer les médias
            media_data = api.get_item_media(item_id)
            
            # Extraire l'URL de l'icône
            assets = media_data.get("assets", [])
            icon_url = None
            
            for asset in assets:
                if asset.get("key") == "icon":
                    icon_url = asset.get("value")
                    break
            
            if icon_url:
                dm.update_icon_url(item_id, icon_url)
                fetched += 1
            else:
                dm.update_icon_url(item_id, "NONE")
                
        except Exception:
            dm.update_icon_url(item_id, "NONE")
            errors += 1
        
        # Mise à jour progress bar tous les 10 items
        if (i + 1) % 10 == 0 or i == total - 1:
            progress_bar.progress((i + 1) / total, text=f"Icônes: {i+1}/{total}")
    
    # Vider le cache pour afficher les nouvelles icônes
    get_housing_items_from_db.clear()
    
    st_status.update(
        label=f"✅ {fetched} icônes téléchargées ({errors} erreurs)", 
        state="complete", 
        expanded=False
    )



@st.cache_data(ttl=60)
def get_cached_items_summary(realm_id: int):
    """Wrapper avec cache pour récupérer le résumé des items"""
    dm = get_data_manager()
    return dm.get_items_summary(realm_id)


@st.cache_data(ttl=60)
def get_cached_profit_data(realm_id: int, profession_ids: tuple = None):
    """Cache pour les données de profit"""
    dm = get_data_manager()
    return dm.get_craftable_items_profit(realm_id, list(profession_ids) if profession_ids else None)


def render_profit_page(realm_id: int):
    """Affiche la page d'analyse des profits de craft"""
    dm = get_data_manager()
    
    st.markdown("## 💰 Analyse des Profits de Craft")
    st.markdown("Identifiez les items les plus rentables à crafter sur votre serveur.")
    st.caption("💡 Le prix de vente affiché est le **prix minimum observé sur les 3 derniers jours**")
    
    # Liste des professions disponibles
    PROFESSIONS = {
        164: "Forge",
        165: "Travail du cuir",
        171: "Alchimie",
        197: "Couture",
        202: "Ingénierie",
        333: "Enchantement",
        755: "Joaillerie",
        773: "Calligraphie",
    }
    
    # Filtres
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        selected_professions = st.multiselect(
            "🔧 Filtrer par métier(s)",
            options=list(PROFESSIONS.keys()),
            format_func=lambda x: PROFESSIONS[x],
            default=None,
            placeholder="Tous les métiers"
        )
    
    with col2:
        min_profit_gold = st.number_input(
            "💰 Profit min (or)",
            min_value=0,
            value=0,
            step=100
        )
    
    with col3:
        min_volume = st.number_input(
            "📦 Ventes min",
            min_value=0,
            value=0,
            step=1
        )
    
    # Récupérer les données (avec cache)
    profession_ids = tuple(selected_professions) if selected_professions else None
    items = get_cached_profit_data(realm_id, profession_ids)
    
    # Extraire les noms d'extensions purs (sans le nom du métier)
    # Ex: "Joaillerie des Îles aux Dragons" -> "Îles aux Dragons"
    # Liste des extensions connues
    KNOWN_EXPANSIONS = [
        "Khaz Algar", "The War Within",
        "Îles aux Dragons", "Dragon Isles", "Îles aux dragons",
        "Shadowlands", "Terres obscures", "Ombreterre",
        "Kul Tiras", "Zandalar", "Battle for Azeroth",
        "Legion", "Légion",
        "Draenor", "Warlords of Draenor",
        "Pandarie", "Mists of Pandaria", "Pandaria",
        "Cataclysm", "Cataclysme",
        "Northrend", "Norfendre", "Wrath of the Lich King",
        "Outland", "Outreterre", "Burning Crusade",
        "Classic", "Classique", "Vanilla",
    ]
    
    def extract_expansion_name(tier_name: str) -> str:
        if not tier_name:
            return ""
        # Chercher une expansion connue dans le nom
        for exp in KNOWN_EXPANSIONS:
            if exp.lower() in tier_name.lower():
                return exp
        # Fallback: ne pas inclure si non reconnue
        return ""
    
    # Créer un mapping expansion_display -> liste de raw expansions
    expansion_to_raw = {}
    for item in items:
        raw_exp = item.get("expansion")
        if raw_exp:
            display_exp = extract_expansion_name(raw_exp)
            if display_exp:  # Ne pas inclure les expansions non reconnues
                if display_exp not in expansion_to_raw:
                    expansion_to_raw[display_exp] = set()
                expansion_to_raw[display_exp].add(raw_exp)
    
    available_expansions = sorted(expansion_to_raw.keys())
    
    # Filtre d'expansion (toujours affiché)
    selected_expansion_display = st.multiselect(
        "📅 Filtrer par extension",
        options=available_expansions if available_expansions else ["(Rescan nécessaire)"],
        default=None,
        placeholder="Toutes les extensions",
        disabled=not available_expansions
    )
    
    # Convertir les noms affichés en valeurs raw pour le filtrage
    selected_raw_expansions = set()
    for exp_display in selected_expansion_display:
        if exp_display in expansion_to_raw:
            selected_raw_expansions.update(expansion_to_raw[exp_display])
    
    if not available_expansions:
        st.caption("ℹ️ Rescanner les recettes pour activer ce filtre")
        selected_raw_expansions = set()
    
    # Filtrer par profit, volume et expansion
    min_profit_copper = min_profit_gold * 10000
    filtered_items = [
        item for item in items
        if (item.get("profit") or 0) >= min_profit_copper
        and (item.get("volume") or 0) >= min_volume
        and (not selected_raw_expansions or item.get("expansion") in selected_raw_expansions)
    ]
    
    # Stats summary
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    profitable_count = len([i for i in filtered_items if (i.get("profit") or 0) > 0])
    total_potential = sum(i.get("profit") or 0 for i in filtered_items if (i.get("profit") or 0) > 0)
    
    with col1:
        st.metric("📊 Items affichés", len(filtered_items))
    with col2:
        st.metric("✅ Items rentables", profitable_count)
    with col3:
        st.metric("💎 Profit potentiel total", format_gold(total_potential))
    with col4:
        avg_margin = sum(i.get("profit_margin") or 0 for i in filtered_items if i.get("profit_margin")) / max(profitable_count, 1)
        st.metric("📈 Marge moyenne", f"{avg_margin:.1f}%")
    
    st.markdown("---")
    
    if not filtered_items:
        st.info("Aucun item ne correspond aux critères. Essayez de réduire les filtres.")
        return
    
    # Préparer les données pour le tableau
    # Calculer le score max pour afficher en pourcentage
    max_score = max(item.get("score") or 0 for item in filtered_items) if filtered_items else 1
    if max_score == 0:
        max_score = 1
    
    df_data = []
    for item in filtered_items:
        profit = item.get("profit")
        indicator = ""
        if profit:
            if profit > 500000:  # > 50g
                indicator = "🟢"
            elif profit > 0:
                indicator = "🟡"
            else:
                indicator = "🔴"
        
        score_pct = int((item.get("score") or 0) / max_score * 100)
        
        df_data.append({
            "Item ID": item["item_id"],
            "Icon": item.get("icon_url") or "",
            "Nom": item["name"],
            "Métier": item["profession_name"],
            "Coût Craft": format_gold(item.get("craft_cost")),
            "Prix Vente": format_gold(item.get("sell_price")),
            "Profit": f"{indicator} {format_gold(profit)}" if profit else "-",
            "Marge %": f"{item.get('profit_margin'):.1f}%" if item.get("profit_margin") else "-",
            "Ventes 7j": item.get("volume") or 0,
            "Score": f"{score_pct}%",
        })
    
    df = pd.DataFrame(df_data)
    
    # Afficher le tableau
    event = st.dataframe(
        df,
        column_config={
            "Item ID": None,  # Caché
            "Icon": st.column_config.ImageColumn("", width="small"),
            "Nom": st.column_config.TextColumn("Item", width="medium"),
            "Métier": st.column_config.TextColumn("Métier", width="small"),
            "Coût Craft": st.column_config.TextColumn("Coût", width="small"),
            "Prix Vente": st.column_config.TextColumn("Prix Vente", width="small"),
            "Profit": st.column_config.TextColumn("Profit", width="small"),
            "Marge %": st.column_config.TextColumn("Marge", width="small"),
            "Ventes 7j": st.column_config.NumberColumn("Ventes 7j", width="small"),
            "Score": st.column_config.TextColumn("Score", width="small"),
        },
        hide_index=True,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        key="profit_table"
    )
    
    # Afficher les meilleurs serveurs si un item est sélectionné
    selected_rows = event.selection.rows if hasattr(event, 'selection') and hasattr(event.selection, 'rows') else []
    
    if selected_rows:
        selected_row_index = selected_rows[0]
        selected_item_id = int(df.iloc[selected_row_index]["Item ID"])  # Ensure int
        selected_item_name = df.iloc[selected_row_index]["Nom"]
        
        # Détails de l'item (mêmes sections que la page Housing)
        st.markdown("---")
        st.markdown(f"### 📊 Détails de l'item: **{selected_item_name}**")
        
        # Créer un dict item compatible avec les fonctions de détails
        selected_item_data = {
            "item_id": selected_item_id,
            "name": selected_item_name,
            "icon_url": df.iloc[selected_row_index].get("Icon") if "Icon" in df.columns else None,
        }
        
        # Récupérer des infos supplémentaires depuis la base
        item_info = dm.get_items_summary(realm_id)
        for item in item_info:
            if item["item_id"] == selected_item_id:
                selected_item_data.update(item)
                break
        
        # Onglets pour les différentes sections (même layout que page Housing)
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Prix par Serveur", 
            "📈 Historique Prix", 
            "📦 Volume",
            "🏆 Meilleurs Serveurs",
            "📉 Statistiques",
            "🔨 Craft"
        ])
        
        with tab1:
            render_prices_by_realm(selected_item_id)
        
        with tab2:
            render_price_history(selected_item_id, realm_id)
        
        with tab3:
            render_volume_history(selected_item_id, realm_id)
        
        with tab4:
            render_best_servers_to_sell(selected_item_id)
        
        with tab5:
            render_statistics(selected_item_id, realm_id)
        
        with tab6:
            render_craft_info(selected_item_id, realm_id)


def render_item_list(realm_id: int):
    """Affiche la liste des items de housing"""
    
    housing_items = load_housing_items()
    
    if not housing_items:
        st.warning("Aucun item de housing trouvé")
        return
    
    st.caption("💡 Le prix affiché est le **prix minimum observé sur les 3 derniers jours**")
    
    # Récupérer le résumé avec les métriques (avec cache)
    items_summary = get_cached_items_summary(realm_id)
    
    # Si pas de données de prix, créer un résumé basique
    if not items_summary:
        items_summary = [
            {
                "item_id": item["item_id"],
                "name": item["name"],
                "icon_url": item.get("icon_url"),
                "category": item.get("category"),
                "min_price": None,
                "avg_price": None,
                "total_quantity": None,
                "auction_count": None,
                "trend": None,
                "volume_change": None
            }
            for item in housing_items
        ]
    
    # Filtres
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_query = st.text_input("🔍 Rechercher un item", placeholder="Nom de l'item...")
    
    with col2:
        categories = list(set(item.get("category") or "Autre" for item in items_summary))
        selected_category = st.selectbox("📁 Catégorie", ["Toutes"] + sorted(categories))
    
    with col3:
        sort_options = {
            "Nom": "name",
            "Prix (croissant)": "min_price_asc",
            "Prix (décroissant)": "min_price_desc",
            "Tendance": "trend"
        }
        sort_by = st.selectbox("📊 Trier par", list(sort_options.keys()))
    
    # Filtrer les items
    filtered_items = items_summary
    
    # --- OPTIMISATION : Conversion Vectorisée ---
    # Convertir directement la liste de dicts en DataFrame Pandas
    if not items_summary:
        st.info("Aucune donnée disponible pour ce serveur.")
        return

    # Utiliser un cache de session pour le DataFrame brut pour éviter de le recréer à chaque frappe
    cache_key = f"raw_df_{realm_id}_{len(items_summary)}"
    
    if cache_key not in st.session_state:
        df_raw = pd.DataFrame(items_summary)
        # S'assurer que les colonnes numériques sont bien typées
        numeric_cols = ["min_price", "avg_price", "total_quantity", "auction_count", "trend", "volume_change"]
        for col in numeric_cols:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
        st.session_state[cache_key] = df_raw
    
    df_raw = st.session_state[cache_key]
    
    # --- FILTRAGE VECTORISÉ (Rapide) ---
    mask = pd.Series(True, index=df_raw.index)
    
    # Filtre Recherche (Case insensitive)
    if search_query:
        mask &= df_raw["name"].str.contains(search_query, case=False, na=False)
    
    # Filtre Catégorie
    if selected_category != "Toutes":
        mask &= (df_raw["category"].fillna("Autre") == selected_category)
    
    # Appliquer le masque
    df_filtered = df_raw[mask].copy()
    
    # --- TRI VECTORISÉ ---
    if sort_by == "Prix (croissant)":
        df_filtered = df_filtered.sort_values("min_price", ascending=True, na_position='last')
    elif sort_by == "Prix (décroissant)":
        df_filtered = df_filtered.sort_values("min_price", ascending=False, na_position='last')
    elif sort_by == "Tendance":
        df_filtered = df_filtered.sort_values("trend", ascending=False, na_position='last')
    elif sort_by == "Nom":
        df_filtered = df_filtered.sort_values("name", ascending=True)

    st.markdown(f"### 📦 Items de Housing ({len(df_filtered)} résultats)")
    
    if not df_filtered.empty:
        # --- FORMATAGE VECTORISÉ POUR AFFICHAGE ---
        df_display = df_filtered.copy()
        
        # Renommage colonne ID pour la clé interne
        df_display["Item ID"] = df_display["item_id"]
        
        # Icône (Future proofing, même si vide pour l'instant)
        df_display["Icone"] = df_display.get("icon_url", "")
        
        df_display["Nom"] = df_display["name"]
        df_display["Catégorie"] = df_display["category"].fillna("N/A")
        
        df_display["Prix Min"] = df_display["min_price"].apply(format_gold)
        df_display["Prix Moyen"] = df_display["avg_price"].apply(lambda x: format_gold(int(x)) if pd.notnull(x) else None)
        df_display["Quantité"] = df_display["total_quantity"].fillna("N/A")
        df_display["Enchères"] = df_display["auction_count"].fillna("N/A")
        df_display["Tendance"] = df_display["trend"].apply(format_trend)
        
        def fmt_vol(val):
            if pd.isna(val) or val == 0: return "N/A"
            return f"+{int(val)}" if val > 0 else str(int(val))
            
        df_display["Volume Δ"] = df_display["volume_change"].apply(fmt_vol)
        
        # Formatage Date de MAJ
        df_display["Maj"] = df_display["recorded_at"].apply(format_time_diff)
        
        # Métier (profession)
        df_display["Métier"] = df_display["profession_name"].fillna("-")
        
        # Coût Craft avec indicateur de profit
        def format_craft_cost(row):
            craft_cost = row.get("craft_cost")
            min_price = row.get("min_price")
            
            if pd.isna(craft_cost) or craft_cost is None:
                return "-"
            
            cost_str = format_gold(int(craft_cost))
            
            # Indicateur de profit si on a les deux prix
            if min_price and craft_cost:
                if min_price > craft_cost * 1.1:  # 10%+ profit
                    return f"🟢 {cost_str}"
                elif min_price < craft_cost * 0.9:  # On perd 10%+
                    return f"🔴 {cost_str}"
                else:
                    return f"⚪ {cost_str}"
            return cost_str
        
        df_display["Coût Craft"] = df_display.apply(format_craft_cost, axis=1)

        # Sélection des colonnes finales (Ajout Métier et Coût Craft)
        final_cols = ["Icone", "Item ID", "Nom", "Catégorie", "Métier", "Prix Min", "Coût Craft",
                      "Quantité", "Enchères", "Tendance", "Volume Δ", "Maj"]
        
        df_final = df_display[final_cols]
        
        event = st.dataframe(
            df_final,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"housing_table_{realm_id}",
            column_config={
                "Item ID": st.column_config.NumberColumn("ID", width="small"),
                "Icone": st.column_config.ImageColumn("Icon", width="small"),
                "Nom": st.column_config.TextColumn("Nom", width="medium"),
                "Catégorie": st.column_config.TextColumn("Catégorie", width="small"),
                "Métier": st.column_config.TextColumn("Métier", width="small", help="Profession requise pour crafter cet item"),
                "Coût Craft": st.column_config.TextColumn("Coût Craft", width="small", help="🟢 = Profit, 🔴 = Perte, ⚪ = Neutre"),
                "Quantité": st.column_config.TextColumn("Qté", width="small"),
                "Enchères": st.column_config.TextColumn("Ench.", width="small"),
                "Maj": st.column_config.TextColumn("Maj", width="small", help="Temps écoulé depuis la dernière mise à jour"),
            }
        )
        
        if len(event.selection.rows) > 0:
            selected_row_index = event.selection.rows[0]
            selected_item_id = df_final.iloc[selected_row_index]["Item ID"]
            st.session_state.selected_item_id = int(selected_item_id)
        
        # Affichage des détails si un item est sélectionné
        if st.session_state.selected_item_id:
            # Trouver l'item sélectionné dans la liste complète des items FILTRÉS ou NON ? 
            # Il vaut mieux chercher dans filtered_items car l'index correspond à ce tableau
            # Mais comme on a l'ID, on peut chercher dans la liste complète si besoin.
            # L'index de event.selection.rows correspond à df, qui est construit sur filtered_items.
            
            selected_item = next(
                (item for item in filtered_items if item["item_id"] == st.session_state.selected_item_id),
                None
            )
            
            # Si non trouvé dans filtered_items (ex: changement de filtre), chercher dans items_summary global
            if not selected_item:
                 selected_item = next(
                    (item for item in items_summary if item["item_id"] == st.session_state.selected_item_id),
                    None
                )
            
            if selected_item:
                st.markdown("---")
                render_item_details(selected_item, realm_id)
            else:
                # Si l'item n'existe plus (ex: données rechargées), reset la sélection
                st.session_state.selected_item_id = None


def render_item_details(item: Dict, current_realm_id: int):
    """Affiche les détails d'un item"""
    dm = get_data_manager()
    
    st.markdown(f"## 📋 Détails: {item['name']}")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Prix Minimum",
            format_gold(item.get("min_price")),
            help="Prix le plus bas actuellement sur le serveur sélectionné"
        )
    
    with col2:
        st.metric(
            "📊 Prix Moyen",
            format_gold(int(item["avg_price"]) if item.get("avg_price") else None),
            help="Prix moyen des enchères actuelles"
        )
    
    with col3:
        trend = item.get("trend")
        st.metric(
            "📈 Tendance",
            f"{trend:+.1f}%" if trend is not None else "N/A",
            delta=f"{trend:+.1f}%" if trend is not None else None,
            delta_color="normal" if trend and trend > 0 else "inverse" if trend else "off",
            help="Variation par rapport au prix moyen sur 3 semaines"
        )
    
    with col4:
        volume = item.get("volume_change")
        st.metric(
            "📦 Volume Δ Semaine",
            f"{volume:+d}" if volume is not None else "N/A",
            help="Changement du nombre d'items en vente sur la semaine"
        )
    
    st.markdown("---")
    
    # Onglets pour les différentes vues
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Prix par Serveur", 
        "📈 Historique Prix", 
        "📦 Volume",
        "🏆 Meilleurs Serveurs",
        "📉 Statistiques",
        "🔨 Craft"
    ])
    
    with tab1:
        render_prices_by_realm(item["item_id"])
    
    with tab2:
        render_price_history(item["item_id"], current_realm_id)
    
    with tab3:
        render_volume_history(item["item_id"], current_realm_id)
    
    with tab4:
        render_best_servers_to_sell(item["item_id"])
    
    with tab5:
        render_statistics(item["item_id"], current_realm_id)
    
    with tab6:
        render_craft_info(item["item_id"], current_realm_id)


def render_craft_info(item_id: int, realm_id: int):
    """Affiche les informations de craft d'un item"""
    dm = get_data_manager()
    
    # Récupérer la recette de l'item
    recipe = dm.get_recipe_for_item(item_id)
    
    if not recipe:
        st.info("🔨 Cet item n'est pas craftable ou la recette n'a pas encore été synchronisée.")
        st.caption("Les recettes sont synchronisées automatiquement lors du premier scan.")
        return
    
    # Afficher les infos de la recette
    st.markdown(f"### 🔨 {recipe['recipe_name']}")
    st.markdown(f"**Métier :** {recipe['profession_name']}")
    
    st.markdown("---")
    
    # Récupérer les composants
    reagents = dm.get_recipe_reagents(recipe["recipe_id"])
    
    if not reagents:
        st.warning("Aucun composant trouvé pour cette recette.")
        return
    
    st.markdown("#### 📦 Composants nécessaires")
    
    # Préparer les données pour l'affichage
    components_data = []
    total_cost = 0
    all_prices_available = True
    
    for reagent in reagents:
        reagent_id = reagent["reagent_item_id"]
        reagent_name = reagent["reagent_name"] or f"Item {reagent_id}"
        quantity = reagent["quantity"]
        
        # Essayer d'abord le prix local du serveur
        price_data = dm.get_current_price(reagent_id, realm_id)
        
        # Si pas de prix local, essayer le prix régional (commodities)
        if not price_data or not price_data.get("min_price"):
            price_data = dm.get_current_price(reagent_id, 0)  # realm_id=0 = regional
        
        if price_data and price_data.get("min_price"):
            unit_price = price_data["min_price"]
            line_total = unit_price * quantity
            total_cost += line_total
            
            components_data.append({
                "Composant": reagent_name,
                "Quantité": quantity,
                "Prix Unitaire": format_gold(unit_price),
                "Sous-total": format_gold(line_total)
            })
        else:
            all_prices_available = False
            components_data.append({
                "Composant": reagent_name,
                "Quantité": quantity,
                "Prix Unitaire": "❓ Non dispo",
                "Sous-total": "-"
            })
    
    # Afficher le tableau des composants
    if components_data:
        df_components = pd.DataFrame(components_data)
        st.dataframe(
            df_components,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Composant": st.column_config.TextColumn("Composant", width="medium"),
                "Quantité": st.column_config.NumberColumn("Qté", width="small"),
                "Prix Unitaire": st.column_config.TextColumn("Prix Unit.", width="small"),
                "Sous-total": st.column_config.TextColumn("Sous-total", width="small")
            }
        )
    
    st.markdown("---")
    
    # Afficher le coût total et la comparaison
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if total_cost > 0:
            st.metric("💰 Coût de Craft", format_gold(total_cost))
        else:
            st.metric("💰 Coût de Craft", "N/A")
    
    with col2:
        # Récupérer le prix de vente actuel
        current_price_data = dm.get_current_price(item_id, realm_id)
        if current_price_data and current_price_data.get("min_price"):
            ah_price = current_price_data["min_price"]
            st.metric("🏪 Prix AH Actuel", format_gold(ah_price))
        else:
            ah_price = None
            st.metric("🏪 Prix AH Actuel", "N/A")
    
    with col3:
        if all_prices_available and ah_price and total_cost > 0:
            profit = ah_price - total_cost
            profit_percent = ((ah_price / total_cost) - 1) * 100
            
            if profit > 0:
                st.metric(
                    "📈 Profit Potentiel",
                    format_gold(profit),
                    delta=f"+{profit_percent:.1f}%",
                    delta_color="normal"
                )
            else:
                st.metric(
                    "📉 Perte Potentielle",
                    format_gold(abs(profit)),
                    delta=f"{profit_percent:.1f}%",
                    delta_color="inverse"
                )
        else:
            st.metric("📊 Profit", "N/A", help="Calcul impossible - données manquantes")


# --- Utils ---
def get_flag_emoji(region_locale: str) -> str:
    """Retourne un emoji drapeau selon le locale"""
    if not region_locale:
        return "🏳️"
    
    # Mapping locale -> drapeau (supporte avec et sans underscore)
    flags = {
        "fr_FR": "🇫🇷", "frFR": "🇫🇷",
        "en_GB": "🇬🇧", "enGB": "🇬🇧",
        "de_DE": "🇩🇪", "deDE": "🇩🇪",
        "es_ES": "🇪🇸", "esES": "🇪🇸",
        "it_IT": "🇮🇹", "itIT": "🇮🇹",
        "ru_RU": "🇷🇺", "ruRU": "🇷🇺",
        "pt_PT": "🇵🇹", "ptPT": "🇵🇹",
        "ko_KR": "🇰🇷", "koKR": "🇰🇷",
        "zh_TW": "🇹🇼", "zhTW": "🇹🇼",
        "zh_CN": "🇨🇳", "zhCN": "🇨🇳",
        "en_US": "🇺🇸", "enUS": "🇺🇸",
    }
    # Par défaut on affiche "??" si inconnu
    return flags.get(region_locale, "🏳️")


def get_flag_url(region_locale: str) -> str:
    """Retourne l'URL de l'image du drapeau (flagcdn) selon le locale"""
    if not region_locale:
        return "https://flagcdn.com/48x36/un.png" # ONU comme fallback
    
    # Nettoyage (fr_FR -> frfr, frFR -> frfr)
    clean_locale = region_locale.replace("_", "").lower()
    
    # Extraction du code pays (généralement les 2 derniers caractères)
    # ex: frfr -> fr, engb -> gb, enus -> us
    if len(clean_locale) >= 4:
        country_code = clean_locale[-2:]
    else:
        # Fallback si le format est étrange, on essaie les 2 premiers
        country_code = clean_locale[:2]
        
    return f"https://flagcdn.com/48x36/{country_code}.png"


def render_prices_by_realm(item_id: int):
    """Affiche les prix d'un item sur tous les serveurs"""
    dm = get_data_manager()
    
    realm_prices = dm.get_all_realms_prices(item_id)
    
    if not realm_prices:
        st.info("Aucune donnée de prix disponible pour cet item sur les différents serveurs.")
        st.caption("Cliquez sur 'Rafraîchir les données' dans la sidebar pour récupérer les données actuelles.")
        return
    
    # Filtrer les serveurs avec des prix
    realm_prices_with_data = [rp for rp in realm_prices if rp.get("min_price")]
    
    if not realm_prices_with_data:
        st.info("Aucune enchère active trouvée pour cet item.")
        return
    
    # Créer un DataFrame
    df_data = []
    
    # Traduction des types de population
    population_labels = {
        "FULL": "🔴 Complet",
        "HIGH": "🟠 Élevée", 
        "MEDIUM": "🟡 Moyenne",
        "LOW": "🟢 Faible",
        "NEW_PLAYERS": "🆕 Nouveaux",
        "UNKNOWN": "❓ Inconnu"
    }
    
    for rp in realm_prices_with_data:
        # Conversion Copper -> Gold pour le graphique
        min_price_gold = rp.get("min_price", 0) / 10000.0
        avg_price_gold = int(rp["avg_price"]) / 10000.0 if rp.get("avg_price") else None
        
        pop_type = rp.get("population") or "UNKNOWN"
        pop_label = population_labels.get(pop_type, pop_type)
        
        # Drapeau
        # Drapeau
        region = rp.get("region")
        flag_url = get_flag_url(region)
        
        df_data.append({
            "Region": flag_url,
            "Serveur": rp["realm_name"],
            "Population": pop_label,
            "Prix Min (Gold)": min_price_gold,
            "Prix Min": min_price_gold,  # Raw numeric for sorting
            "Prix Moyen": avg_price_gold, # Raw numeric for sorting
            "Quantité": rp.get("total_quantity") or 0,
            "Enchères": rp.get("auction_count") or 0,
        })
    
    df = pd.DataFrame(df_data)
    
    # Tronquer les noms de serveurs trop longs pour l'affichage
    df["Serveur_Court"] = df["Serveur"].apply(lambda x: x[:12] + "..." if len(x) > 15 else x)
    
    # Tri par défaut par prix croissant
    df = df.sort_values("Prix Min (Gold)")
    
    # Note pour l'utilisateur si seul un serveur est affiché
    if len(df) <= 1:
        st.caption("ℹ️ Astuce : Pour comparer avec d'autres serveurs, sélectionnez-les dans la barre latérale et cliquez sur 'Rafraîchir les données'. L'historique sera conservé.")

    # Graphique des prix par serveur
    fig = px.bar(
        df,
        x="Serveur_Court",
        y="Prix Min (Gold)",
        title="Prix Minimum par Serveur",
        labels={"Prix Min (Gold)": "Prix (Gold)", "Serveur_Court": ""},
        color="Prix Min (Gold)",
        color_continuous_scale="RdYlGn_r",
        custom_data=["Serveur"]  # Garder le nom complet pour le tooltip
    )
    
    # Amélioration du tooltip avec nom complet
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Prix: %{y:,.2f}g<extra></extra>"
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        height=400,
        showlegend=False,
        yaxis_title="Prix (Gold)",
        margin=dict(r=120),  # Marge droite plus large pour la légende
        coloraxis_colorbar=dict(
            title="Prix",
            thicknessmode="pixels",
            thickness=15,
            lenmode="fraction",
            len=0.7,
            yanchor="middle",
            y=0.5,
            tickformat=",.0f"
        )
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau des prix (triable via clic sur les colonnes)
    st.markdown("#### 📊 Comparaison détaillée (cliquez sur une colonne pour trier)")
    
    df_display = df[["Region", "Serveur", "Population", "Prix Min", "Prix Moyen", "Quantité", "Enchères"]]
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Region": st.column_config.ImageColumn("Pays", width="small"),
            "Serveur": st.column_config.TextColumn("Serveur", width="medium"),
            "Population": st.column_config.TextColumn("Population", width="small"),
            "Prix Min": st.column_config.NumberColumn("Prix Min", width="small", format="%.0f g"),
            "Prix Moyen": st.column_config.NumberColumn("Prix Moyen", width="small", format="%.0f g"),
            "Quantité": st.column_config.NumberColumn("Quantité", width="small"),
            "Enchères": st.column_config.NumberColumn("Enchères", width="small"),
        }
    )


def render_price_history(item_id: int, realm_id: int):
    """Affiche l'historique des prix d'un item"""
    dm = get_data_manager()
    
    history = dm.get_price_history(item_id, realm_id, days=21)
    
    if not history:
        st.info("Pas assez de données historiques. Les données s'accumuleront au fil du temps.")
        st.caption("Rafraîchissez régulièrement les données pour construire l'historique.")
        return
    
    # Créer un DataFrame
    df = pd.DataFrame(history)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    df["min_price_gold"] = df["min_price"] / 10000  # Convertir en gold
    df["avg_price_gold"] = df["avg_price"] / 10000
    
    # Graphique d'évolution des prix
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["recorded_at"],
        y=df["min_price_gold"],
        name="Prix Min",
        line=dict(color="#00ff00", width=2),
        mode="lines+markers"
    ))
    
    fig.add_trace(go.Scatter(
        x=df["recorded_at"],
        y=df["avg_price_gold"],
        name="Prix Moyen",
        line=dict(color="#FFD100", width=2),
        mode="lines+markers"
    ))
    
    fig.update_layout(
        title="Évolution des Prix (en or)",
        xaxis_title="Date",
        yaxis_title="Prix (gold)",
        height=400,
        hovermode="x unified",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor="#FFD100",
            borderwidth=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_volume_history(item_id: int, realm_id: int):
    """Affiche l'historique du volume d'un item"""
    dm = get_data_manager()
    
    history = dm.get_price_history(item_id, realm_id, days=21)
    
    if not history:
        st.info("Pas assez de données historiques pour le volume.")
        st.caption("Rafraîchissez régulièrement les données pour construire l'historique.")
        return
    
    # Créer un DataFrame
    df = pd.DataFrame(history)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    
    # Graphique de l'évolution du volume
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["recorded_at"],
        y=df["total_quantity"],
        name="Quantité totale",
        fill="tozeroy",
        line=dict(color="#4CAF50", width=2),
        mode="lines+markers"
    ))
    
    fig.add_trace(go.Scatter(
        x=df["recorded_at"],
        y=df["auction_count"],
        name="Nombre d'enchères",
        line=dict(color="#FF9800", width=2, dash="dash"),
        mode="lines+markers"
    ))
    
    fig.update_layout(
        title="📦 Évolution du Volume sur 3 semaines",
        xaxis_title="Date",
        yaxis_title="Quantité",
        height=400,
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistiques de volume
    if len(df) >= 2:
        vol_start = df.iloc[0]["total_quantity"] if df.iloc[0]["total_quantity"] else 0
        vol_end = df.iloc[-1]["total_quantity"] if df.iloc[-1]["total_quantity"] else 0
        
        # Si le volume a diminué (moins d'items en vente), c'est qu'ils se sont vendus = positif
        # Si le volume a augmenté (plus d'items en vente), c'est plus de concurrence = négatif
        items_exchanged = vol_start - vol_end  # Inversé: diminution = ventes = positif
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Volume actuel", f"{vol_end:,}")
        with col2:
            # Affichage: + = items vendus, - = plus de concurrence
            st.metric("Items échangés", f"{items_exchanged:+,}", 
                     delta=f"{items_exchanged:+,}" if items_exchanged != 0 else None,
                     delta_color="normal" if items_exchanged > 0 else "inverse")
        with col3:
            avg_vol = df["total_quantity"].mean()
            st.metric("Volume moyen", f"{int(avg_vol):,}" if pd.notna(avg_vol) else "N/A")


def render_best_servers_to_sell(item_id: int):
    """Affiche le classement des meilleurs serveurs pour vendre cet item"""
    dm = get_data_manager()
    
    # Utiliser la nouvelle méthode qui calcule le volume échangé
    best_servers_data = dm.get_best_servers_data(item_id, days=7)
    
    # Filtrer les serveurs avec des données
    # On veut des serveurs où il y a un prix minimum défini
    servers_with_data = [d for d in best_servers_data if d.get("min_price")]
    
    # FILTRE ANTI-RUSSE (demandé par utilisateur)
    # On exclut les serveurs dont le region is 'ru_RU'
    servers_with_data = [d for d in servers_with_data if d.get("region") != "ru_RU"]
    
    if not servers_with_data or len(servers_with_data) < 2:
        st.info("Pas assez de données pour calculer le classement.")
        st.caption("Le classement nécessite des données sur plusieurs serveurs.")
        return
    
    # Extraire les valeurs pour normalisation
    prices = [d["min_price"] for d in servers_with_data]
    # On ne garde que les volumes échangés positifs (ventes) pour le max, sinon 1
    # On permet les volumes négatifs dans la liste pour les pénaliser
    volumes = [d["volume_exchanged"] for d in servers_with_data]
    max_volume = max(volumes) if volumes and max(volumes) > 0 else 1
    min_volume = min(volumes) if volumes else 0
    
    max_price = max(prices) if prices else 1
    min_price_val = min(prices) if prices else 0
    
    # Traduction population
    population_scores = {
        "FULL": 1.0,
        "HIGH": 0.8,
        "MEDIUM": 0.6,
        "LOW": 0.4,
        "NEW_PLAYERS": 0.3,
        "UNKNOWN": 0.5
    }
    
    population_labels = {
        "FULL": "🔴 Complet",
        "HIGH": "🟠 Élevée", 
        "MEDIUM": "🟡 Moyenne",
        "LOW": "🟢 Faible",
        "NEW_PLAYERS": "🆕 Nouveaux",
        "UNKNOWN": "❓ Inconnu"
    }
    
    results = []
    
    for d in servers_with_data:
        price = d["min_price"]
        vol_exchanged = d["volume_exchanged"]
        pop_type = d.get("population") or "UNKNOWN"
        region = d.get("region")
        
        # Normalisation 0-1
        price_norm = (price - min_price_val) / (max_price - min_price_val) if max_price != min_price_val else 0.5
        
        # Normalisation volume: on favorise les ventes positives
        # Si vol_exchanged est négatif (stock augmente), le score sera bas
        volume_norm = (vol_exchanged - min_volume) / (max_volume - min_volume) if max_volume != min_volume else 0.5
        
        pop_score = population_scores.get(pop_type, 0.5)
        
        # Score pondéré initial
        score = (price_norm * 0.5) + (volume_norm * 0.4) + (pop_score * 0.1)
        
        # Pénalité MAJEURE si aucune vente (volume négatif ou nul)
        # L'utilisateur considère que même si le prix est haut, si ça ne vend pas, c'est un mauvais choix.
        if vol_exchanged <= 0:
            score = score * 0.1
        
        # Formatage du volume pour l'affichage
        vol_display = f"{vol_exchanged:+}" if vol_exchanged != 0 else "0"
        
        flag = get_flag_emoji(region)
        flag_url = get_flag_url(region)
        # server_name_display = f"{flag} {d['realm_name']}" # Séparé pour le tri
        
        results.append({
            "RegionEmoji": flag,
            "Region": flag_url,
            "Serveur": d["realm_name"],
            "Population": population_labels.get(pop_type, pop_type),
            "Prix Min": format_gold(int(price)),
            "Var. Stock 7j": vol_display,  # Renommé pour précision
            "Score": score,
            "Score %": f"{score*100:.0f}%"
        })
    
    # Trier par score décroissant
    results.sort(key=lambda x: x["Score"], reverse=True)
    
    # Ajouter le rang
    for i, r in enumerate(results):
        r["Rang"] = f"#{i+1}"
    
    df = pd.DataFrame(results)
    
    st.markdown("### 🏆 Classement des Meilleurs Serveurs pour Vendre")
    st.caption("Score basé sur : Prix min (50%) + **Variation du stock sur 7 jours** (40%) + Population (10%)")
    st.caption("*Note : Une variation négative (ex: -5) signifie que le stock a baissé, ce qui est bon pour la vente.*")
    
    # Top 3 en métriques
    if len(results) >= 3:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🥇 1er", f"{results[0]['RegionEmoji']} {results[0]['Serveur']}", results[0]["Score %"])
        with col2:
            st.metric("🥈 2ème", f"{results[1]['RegionEmoji']} {results[1]['Serveur']}", results[1]["Score %"])
        with col3:
            st.metric("🥉 3ème", f"{results[2]['RegionEmoji']} {results[2]['Serveur']}", results[2]["Score %"])
        
        st.markdown("---")
    
    # Tableau complet
    st.dataframe(
        df[["Rang", "Region", "Serveur", "Population", "Prix Min", "Var. Stock 7j", "Score %"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rang": st.column_config.TextColumn("Rang", width="small"),
            "Region": st.column_config.ImageColumn("Pays", width="small"),
            "Serveur": st.column_config.TextColumn("Serveur", width="medium"),
            "Population": st.column_config.TextColumn("Pop.", width="small"),
            "Prix Min": st.column_config.NumberColumn("Prix Min", width="small", format="%.0f g"),
            "Var. Stock 7j": st.column_config.TextColumn("Var. Stock 7j", width="small"),
            "Score %": st.column_config.TextColumn("Score", width="small"),
        }
    )


def render_statistics(item_id: int, realm_id: int):
    """Affiche les statistiques d'un item"""
    dm = get_data_manager()
    
    history = dm.get_price_history(item_id, realm_id, days=21)
    
    if not history:
        st.info("Pas assez de données pour calculer les statistiques.")
        return
    
    prices = [h["min_price"] for h in history if h.get("min_price")]
    
    if not prices:
        st.info("Aucune donnée de prix disponible.")
        return
    
    import statistics
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Statistiques de Prix (3 semaines)")
        
        stats_data = {
            "Métrique": ["Minimum", "Maximum", "Moyenne", "Médiane", "Écart-type"],
            "Valeur": [
                format_gold(min(prices)),
                format_gold(max(prices)),
                format_gold(int(statistics.mean(prices))),
                format_gold(int(statistics.median(prices))),
                format_gold(int(statistics.stdev(prices))) if len(prices) > 1 else "N/A"
            ]
        }
        
        st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("### 📦 Statistiques de Volume")
        
        volumes = [h["total_quantity"] for h in history if h.get("total_quantity")]
        auctions = [h["auction_count"] for h in history if h.get("auction_count")]
        
        if volumes:
            vol_stats = {
                "Métrique": ["Volume Min", "Volume Max", "Volume Moyen"],
                "Valeur": [
                    min(volumes),
                    max(volumes),
                    int(statistics.mean(volumes))
                ]
            }
            st.dataframe(pd.DataFrame(vol_stats), use_container_width=True, hide_index=True)
        else:
            st.info("Pas de données de volume disponibles.")


def render_pets_page(realm_id: int):
    """Affiche la page des pets avec prix et meilleurs serveurs"""
    
    st.markdown("## 🐾 Battle Pets")
    st.markdown("Prix des familiers par serveur")
    
    dm = get_data_manager()
    
    # Récupérer les pets avec leurs prix
    pets = dm.get_pets_summary(realm_id)
    
    if not pets:
        st.warning("Aucun pet trouvé. Lancez un scan pour synchroniser les pets.")
        return
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Filtre par type de créature
        creature_types = sorted(set(
            p.get("creature_type") for p in pets if p.get("creature_type")
        ))
        selected_types = st.multiselect(
            "🐉 Type de créature",
            options=creature_types if creature_types else ["Tous"],
            default=None,
            placeholder="Tous les types",
            disabled=not creature_types
        )
    
    with col2:
        # Filtre par source (comment l'obtenir)
        sources = sorted(set(
            p.get("source") for p in pets if p.get("source")
        ))
        selected_sources = st.multiselect(
            "📦 Comment l'obtenir",
            options=sources if sources else ["Tous"],
            default=None,
            placeholder="Toutes les sources",
            disabled=not sources
        )
    
    with col3:
        # Recherche par nom
        search_query = st.text_input("🔍 Rechercher", placeholder="Nom du pet...")
    
    # Filtrer les pets
    filtered_pets = pets
    if selected_types:
        filtered_pets = [p for p in filtered_pets if p.get("creature_type") in selected_types]
    if selected_sources:
        filtered_pets = [p for p in filtered_pets if p.get("source") in selected_sources]
    if search_query:
        search_lower = search_query.lower()
        filtered_pets = [p for p in filtered_pets if search_lower in (p.get("name") or "").lower()]
    
    # Stats
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Pets affichés", len(filtered_pets))
    with col2:
        pets_with_price = len([p for p in filtered_pets if p.get("min_price")])
        st.metric("💰 Avec prix", pets_with_price)
    with col3:
        st.metric("📦 Total pets", len(pets))
    
    st.markdown("---")
    
    # Préparer les données pour le tableau
    df_data = []
    for pet in filtered_pets:
        price = pet.get("min_price") or 0  # 0 pour N/A (tri en bas)
        pet_id = pet["pet_id"]
        pet_name = pet.get("name") or "Inconnu"
        creature_id = pet.get("creature_id")
        # URL wowhead: npc si creature_id disponible, sinon battle-pet
        if creature_id:
            wowhead_url = f"https://www.wowhead.com/fr/npc={creature_id}"
        else:
            wowhead_url = f"https://www.wowhead.com/fr/battle-pet/{pet_id}"
        df_data.append({
            "Pet ID": pet_id,
            "Icon": pet.get("icon_url") or "",
            "Nom": pet_name,
            "Type": pet.get("creature_type") or "-",
            "Source": pet.get("source") or "-",
            "Prix_num": price,  # Colonne numérique pour le tri
            "Prix": format_gold(price) if price > 0 else "N/A",
            "Qté": pet.get("total_quantity") or 0,
            "Wowhead": wowhead_url,
        })
    
    df = pd.DataFrame(df_data)
    
    # Trier par prix décroissant (N/A = 0 en bas) - seulement si le df n'est pas vide
    if not df.empty:
        df = df.sort_values("Prix_num", ascending=False).reset_index(drop=True)
    
    # Afficher le tableau
    event = st.dataframe(
        df,
        column_config={
            "Pet ID": None,  # Caché
            "Prix_num": None,  # Caché (utilisé pour le tri)
            "Icon": st.column_config.ImageColumn("", width="small"),
            "Nom": st.column_config.TextColumn("Nom", width="medium"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Source": st.column_config.TextColumn("Comment l'obtenir", width="large"),
            "Prix": st.column_config.TextColumn("Prix", width="small"),
            "Qté": st.column_config.NumberColumn("Qté", width="small"),
            "Wowhead": st.column_config.LinkColumn("🔗", width="small", display_text="Wowhead"),
        },
        hide_index=True,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        key="pets_table"
    )
    
    # Afficher les meilleurs serveurs si un pet est sélectionné
    if event and event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        if selected_idx < len(df):
            # Convert numpy.int64 to Python int for SQLite compatibility
            selected_pet_id = int(df.iloc[selected_idx]["Pet ID"])
            selected_pet_name = df.iloc[selected_idx]["Nom"]
            
            st.markdown("---")
            st.markdown(f"### 🏆 Meilleurs serveurs pour **{selected_pet_name}**")
            
            # Sélecteur mode Achat/Vente
            col1, col2 = st.columns([1, 3])
            with col1:
                mode = st.radio(
                    "Mode",
                    ["🛒 Achat", "💰 Vente"],
                    index=1,  # Vente par défaut
                    horizontal=True,
                    label_visibility="collapsed"
                )
            with col2:
                if mode == "🛒 Achat":
                    st.caption("🛒 **Achat** : Serveurs où le pet est le moins cher (pour acheter)")
                else:
                    st.caption("💰 **Vente** : Serveurs où le pet est le plus cher (pour vendre)")
            
            # Récupérer les prix sur tous les serveurs
            all_realm_prices = dm.get_pet_all_realms_prices(selected_pet_id)
            
            # Filtrer les serveurs qui ont des prix
            realms_with_prices = [r for r in all_realm_prices if r.get("min_price")]
            
            if realms_with_prices:
                # Trier par prix selon le mode
                if mode == "🛒 Achat":
                    # Moins cher en premier pour l'achat
                    top_realms = sorted(realms_with_prices, key=lambda x: x["min_price"])[:10]
                else:
                    # Plus cher en premier pour la vente
                    top_realms = sorted(realms_with_prices, key=lambda x: x["min_price"], reverse=True)[:10]
                
                realm_df = pd.DataFrame([
                    {
                        "Rang": "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else f"{i+1}")),
                        "Serveur": r["realm_name"],
                        "Prix": format_gold(r.get("min_price")),
                        "Qté": r.get("total_quantity") or 0,
                    }
                    for i, r in enumerate(top_realms)
                ])
                
                st.dataframe(
                    realm_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Rang": st.column_config.TextColumn("", width="small"),
                        "Serveur": st.column_config.TextColumn("Serveur", width="medium"),
                        "Prix": st.column_config.TextColumn("Prix", width="small"),
                        "Qté": st.column_config.NumberColumn("Qté", width="small"),
                    }
                )
            else:
                st.info("Pas de données de prix disponibles pour ce pet.")


def render_collection_page(realm_id: int):
    """Affiche la collection de pets d'un joueur avec les prix de vente"""
    
    st.markdown("## 👤 Ma Collection de Pets")
    st.markdown("Entrez le nom de votre personnage pour voir la valeur de votre collection")
    
    dm = get_data_manager()
    
    # Formulaire pour permettre Entrée = Rechercher
    with st.form("collection_search_form"):
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            # Liste des serveurs pour le dropdown
            realms = load_realms()
            realm_names = sorted([r["name"] for r in realms]) if realms else []
            selected_realm_name = st.selectbox(
                "🌍 Serveur",
                options=realm_names,
                placeholder="Choisir un serveur"
            )
        
        with col2:
            character_name = st.text_input(
                "👤 Nom du personnage",
                placeholder="Ex: Jaina"
            )
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacer
            search_button = st.form_submit_button("🔍 Rechercher", use_container_width=True)
    
    # Rechercher la collection
    if search_button and character_name and selected_realm_name:
        with st.spinner(f"Chargement de la collection de {character_name}..."):
            from blizzard_api import get_api
            api = get_api()
            
            # Convertir le nom du serveur en slug
            realm_slug = selected_realm_name.lower().replace(" ", "-").replace("'", "")
            
            # Récupérer les pets du personnage
            collection_data = api.get_character_pets(realm_slug, character_name)
            
            if not collection_data or "pets" not in collection_data:
                st.error(f"❌ Personnage '{character_name}' non trouvé sur {selected_realm_name} ou profil privé.")
                st.info("💡 Assurez-vous que le nom est correct et que le profil n'est pas privé dans les options Battle.net")
                return
            
            player_pets = collection_data.get("pets", [])
            st.success(f"✅ {len(player_pets)} pets trouvés dans la collection !")
            
            # Récupérer les infos de pets depuis notre BDD
            db_pets = {p["pet_id"]: p for p in dm.get_pets()}
            
            # Construire le tableau avec les prix
            df_data = []
            total_value = 0
            tradable_count = 0
            
            for player_pet in player_pets:
                species = player_pet.get("species", {})
                species_id = species.get("id")
                pet_name = species.get("name", "Inconnu")
                quality = player_pet.get("quality", {}).get("name", "-")
                level = player_pet.get("level", 1)
                
                # Chercher le pet dans notre BDD
                db_pet = db_pets.get(species_id, {})
                
                # Récupérer le prix moyen sur tous les serveurs
                price = None
                if species_id:
                    prices = dm.get_pet_all_realms_prices(species_id)
                    if prices:
                        valid_prices = [p["min_price"] for p in prices if p.get("min_price")]
                        if valid_prices:
                            price = min(valid_prices)  # Prix le plus bas
                
                is_tradable = db_pet.get("is_tradable", False) if db_pet else False
                
                if price and is_tradable:
                    total_value += price
                    tradable_count += 1
                
                df_data.append({
                    "Icon": db_pet.get("icon_url") or "",
                    "Nom": pet_name,
                    "Niveau": level,
                    "Qualité": quality,
                    "Type": db_pet.get("creature_type", "-"),
                    "Prix": format_gold(price) if price else "N/A",
                    "Prix_num": price or 0,
                    "Échangeable": "✅" if is_tradable else "❌",
                })
            
            # Créer le DataFrame
            df = pd.DataFrame(df_data)
            
            # Trier par prix décroissant
            if not df.empty:
                df = df.sort_values("Prix_num", ascending=False).reset_index(drop=True)
            
            # Afficher les stats
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Total pets", len(player_pets))
            with col2:
                st.metric("💰 Échangeables", tradable_count)
            with col3:
                st.metric("🏆 Valeur totale", format_gold(total_value))
            with col4:
                # Valeur en or (gold)
                gold_value = total_value // 10000
                st.metric("🪙 En or", f"{gold_value:,}g".replace(",", " "))
            
            st.markdown("---")
            
            # Afficher le tableau
            st.dataframe(
                df,
                column_config={
                    "Prix_num": None,  # Caché
                    "Icon": st.column_config.ImageColumn("", width="small"),
                    "Nom": st.column_config.TextColumn("Nom", width="medium"),
                    "Niveau": st.column_config.NumberColumn("Niv.", width="small"),
                    "Qualité": st.column_config.TextColumn("Qualité", width="small"),
                    "Type": st.column_config.TextColumn("Type", width="small"),
                    "Prix": st.column_config.TextColumn("Prix (min)", width="small"),
                    "Échangeable": st.column_config.TextColumn("💱", width="small"),
                },
                hide_index=True,
                use_container_width=True,
                height=600
            )


def main():
    """Fonction principale de l'application"""
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">🏠 WoW Housing Price Tracker</h1>', unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; color: #888;'>Suivez les prix des items de housing World of Warcraft</p>",
        unsafe_allow_html=True
    )
    
    # Vérification et Scan au démarrage
    check_startup_scan()
    
    # Vérifier les credentials
    try:
        from config import BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET
        
        if not BLIZZARD_CLIENT_ID or not BLIZZARD_CLIENT_SECRET:
            st.error(
                "⚠️ **Credentials Blizzard manquants!**\n\n"
                "Veuillez configurer vos credentials dans le fichier `.env`:\n"
                "```\n"
                "BLIZZARD_CLIENT_ID=votre_client_id\n"
                "BLIZZARD_CLIENT_SECRET=votre_client_secret\n"
                "```\n\n"
                "Obtenez vos credentials sur [Battle.net Developer Portal](https://develop.battle.net/access/clients)"
            )
            return
            
    except Exception as e:
        st.error(f"Erreur de configuration: {str(e)}")
        return
    
    # Sidebar avec sélection du serveur
    selected_realm_id = render_sidebar()
    
    if not selected_realm_id:
        st.warning("Veuillez sélectionner un serveur de référence dans la sidebar.")
        return
    
    # Routing des pages
    current_page = st.session_state.get("current_page", "🏠 Items Housing")
    
    if current_page == "💰 Profits Craft":
        render_profit_page(selected_realm_id)
    elif current_page == "🐾 Pets":
        render_pets_page(selected_realm_id)
    elif current_page == "👤 Ma Collection":
        render_collection_page(selected_realm_id)
    else:
        # Page par défaut: Items Housing
        render_item_list(selected_realm_id)
    
    # Fetch des icônes en arrière-plan (30 par chargement de page)
    # Cela permet de progressivement remplir le cache sans bloquer l'UI
    try:
        fetched = fetch_missing_icons(batch_size=30)
        if fetched > 0:
            st.toast(f"🖼️ {fetched} icônes récupérées en arrière-plan", icon="✅")
    except Exception:
        pass  # Silencieux en cas d'erreur


if __name__ == "__main__":
    main()
