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


def format_gold(copper_value: Optional[int]) -> str:
    """Formate une valeur en copper vers gold/silver/copper"""
    if copper_value is None:
        return "N/A"
    
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


def perform_global_scan():
    """Effectue un scan complet de tous les serveurs"""
    api = get_api()
    dm = get_data_manager()
    
    st_status = st.status("🔄 Mise à jour globale des données (cela peut prendre 1 à 2 minutes)...", expanded=True)
    
    try:
        # 1. Charger les items de housing pour avoir la liste
        st_status.write("📚 Chargement du catalogue d'items...")
        housing_items = load_housing_items()
        housing_item_ids = {item["item_id"] for item in housing_items}
        
        # 2. Charger la liste des serveurs (Optimisé)
        st_status.write("🌍 Récupération de la liste des serveurs...")
        realms = api.get_all_realms_with_names()
        
        # 3. Boucle sur les serveurs
        total_realms = len(realms)
        progress_bar = st_status.progress(0, text=f"Scan des serveurs (0/{total_realms})")
        
        scanned_count = 0
        
        for i, realm in enumerate(realms):
            realm_name = realm["name"]
            realm_id = realm["id"]
            realm_population = realm.get("population", "UNKNOWN")
            
            # Mise à jour progress bar
            progress_bar.progress((i + 1) / total_realms, text=f"Scan: {realm_name} ({i+1}/{total_realms})")
            
            try:
                # Sauvegarder le serveur si nouveau (avec population)
                dm.save_realm(realm_id, realm_name, realm_population)
                
                # Fetch auctions
                all_auctions = api.get_auctions(realm_id)
                
                # Filtrer en mémoire (rapide)
                # On prépare les données pour insertion batch si possible, 
                # ou on boucle avec record_price_data (SQLite est rapide en local)
                
                # Grouper par item_id
                item_stats = {}
                
                for auction in all_auctions:
                    item_id = auction.get("item", {}).get("id")
                    if item_id in housing_item_ids:
                        if item_id not in item_stats:
                            item_stats[item_id] = {"prices": [], "qty": 0}
                        
                        price = auction.get("buyout") or auction.get("unit_price", 0)
                        qty = auction.get("quantity", 1)
                        
                        if price > 0:
                            item_stats[item_id]["prices"].append(price)
                            item_stats[item_id]["qty"] += qty
                
                # Enregistrer stats
                for item_id, stats in item_stats.items():
                    prices = stats["prices"]
                    if prices:
                        min_price = min(prices)
                        avg_price = sum(prices) / len(prices)
                        total_qty = stats["qty"]
                        auction_count = len(prices) # Approx si stack > 1 mais ok
                        
                        dm.record_price_data(
                            item_id=item_id,
                            realm_id=realm_id,
                            min_price=min_price,
                            avg_price=avg_price,
                            total_quantity=total_qty,
                            auction_count=auction_count
                        )
                
                scanned_count += 1
                
            except Exception as e:
                # On continue même si un serveur plante
                print(f"Error scanning {realm_name}: {e}")
                continue
                
        st_status.update(label=f"✅ Mise à jour terminée! ({scanned_count} serveurs scannés)", state="complete", expanded=False)
        time.sleep(1) # Petit délai pour voir le succès
        
    except Exception as e:
        st_status.update(label=f"❌ Erreur durant la mise à jour: {str(e)}", state="error")


def check_startup_scan():
    """Vérifie si un scan au démarrage est nécessaire"""
    dm = get_data_manager()
    
    # Vérifier l'âge de la dernière donnée
    # On peut faire une requête rapide pour avoir le MAX(recorded_at) global
    # Mais data_manager n'a pas cette méthode publique. On va l'improviser ou l'ajouter.
    # Pour l'instant, on regarde item_summary du premier serveur chargé si dispo, sinon on force.
    pass # TODO: Implémenter logique précise avec DB


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
    """Affiche la sidebar avec la sélection du serveur"""
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
        if st.session_state.selected_realm_id:
            housing_items = load_housing_items()
            fetch_auction_data(st.session_state.selected_realm_id, housing_items)
            st.success("Données mises à jour!")
            st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Informations")
    st.sidebar.info(
        "Les prix sont affichés en or (g), argent (s) et cuivre (c).\n\n"
        "📈 = Prix en hausse (+5%)\n"
        "📉 = Prix en baisse (-5%)\n"
        "➡️ = Prix stable\n\n"
        "**Note :** 'N/A' signifie que l'item n'est pas en vente actuellement à l'Hôtel des Ventes de ce serveur."
    )
    
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
        perform_global_scan()



@st.cache_data(ttl=60)
def get_cached_items_summary(realm_id: int):
    """Wrapper avec cache pour récupérer le résumé des items"""
    dm = get_data_manager()
    return dm.get_items_summary(realm_id)


def render_item_list(realm_id: int):
    """Affiche la liste des items de housing"""
    
    housing_items = load_housing_items()
    
    if not housing_items:
        st.warning("Aucun item de housing trouvé")
        return
    
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

        # Sélection des colonnes finales (Ajout Icone)
        final_cols = ["Item ID", "Icone", "Nom", "Catégorie", "Prix Min", "Prix Moyen", 
                      "Quantité", "Enchères", "Tendance", "Volume Δ"]
        
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
                "Quantité": st.column_config.TextColumn("Qté", width="small"),
                "Enchères": st.column_config.TextColumn("Ench.", width="small"),
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Prix par Serveur", 
        "📈 Historique Prix", 
        "📦 Volume",
        "🏆 Meilleurs Serveurs",
        "📉 Statistiques"
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
        
        pop_type = rp.get("population") or "UNKNOWN"
        pop_label = population_labels.get(pop_type, pop_type)
        
        df_data.append({
            "Serveur": rp["realm_name"],
            "Population": pop_label,
            "Prix Min (Gold)": min_price_gold,
            "Prix Min (formaté)": format_gold(rp.get("min_price")),
            "Prix Moyen": format_gold(int(rp["avg_price"]) if rp.get("avg_price") else None),
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
    
    df_display = df[["Serveur", "Population", "Prix Min (formaté)", "Prix Moyen", "Quantité", "Enchères"]].rename(
        columns={"Prix Min (formaté)": "Prix Min"}
    )
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Serveur": st.column_config.TextColumn("Serveur", width="medium"),
            "Population": st.column_config.TextColumn("Population", width="small"),
            "Prix Min": st.column_config.TextColumn("Prix Min", width="small"),
            "Prix Moyen": st.column_config.TextColumn("Prix Moyen", width="small"),
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
    
    realm_prices = dm.get_all_realms_prices(item_id)
    
    # Filtrer les serveurs avec des données
    realm_prices_with_data = [rp for rp in realm_prices if rp.get("min_price") and rp.get("total_quantity")]
    
    if not realm_prices_with_data or len(realm_prices_with_data) < 2:
        st.info("Pas assez de données pour calculer le classement.")
        st.caption("Le classement nécessite des données de prix et volume sur plusieurs serveurs.")
        return
    
    # Extraire les valeurs pour normalisation
    prices = [rp["avg_price"] or rp["min_price"] for rp in realm_prices_with_data]
    volumes = [rp["total_quantity"] for rp in realm_prices_with_data]
    
    max_price = max(prices) if prices else 1
    max_volume = max(volumes) if volumes else 1
    min_price = min(prices) if prices else 0
    min_volume = min(volumes) if volumes else 0
    
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
    
    # Calculer le score pour chaque serveur
    # Score = (Prix normalisé * 0.5) + (Volume normalisé * 0.4) + (Population * 0.1)
    # Prix: plus c'est cher, mieux c'est pour vendre
    # Volume: plus il y a de volume, plus ça s'échange
    results = []
    
    for rp in realm_prices_with_data:
        price = rp["avg_price"] or rp["min_price"]
        volume = rp["total_quantity"]
        pop_type = rp.get("population") or "UNKNOWN"
        
        # Normalisation 0-1
        price_norm = (price - min_price) / (max_price - min_price) if max_price != min_price else 0.5
        volume_norm = (volume - min_volume) / (max_volume - min_volume) if max_volume != min_volume else 0.5
        pop_score = population_scores.get(pop_type, 0.5)
        
        # Score pondéré
        score = (price_norm * 0.5) + (volume_norm * 0.4) + (pop_score * 0.1)
        
        results.append({
            "Serveur": rp["realm_name"],
            "Population": population_labels.get(pop_type, pop_type),
            "Prix Moyen": format_gold(int(price)),
            "Volume": volume,
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
    st.caption("Score basé sur: Prix moyen (50%) + Volume échangé (40%) + Population (10%)")
    
    # Top 3 en métriques
    if len(results) >= 3:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🥇 1er", results[0]["Serveur"], results[0]["Score %"])
        with col2:
            st.metric("🥈 2ème", results[1]["Serveur"], results[1]["Score %"])
        with col3:
            st.metric("🥉 3ème", results[2]["Serveur"], results[2]["Score %"])
        
        st.markdown("---")
    
    # Tableau complet
    st.dataframe(
        df[["Rang", "Serveur", "Population", "Prix Moyen", "Volume", "Score %"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rang": st.column_config.TextColumn("Rang", width="small"),
            "Serveur": st.column_config.TextColumn("Serveur", width="medium"),
            "Population": st.column_config.TextColumn("Pop.", width="small"),
            "Volume": st.column_config.NumberColumn("Volume", width="small"),
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
    
    # Contenu principal
    render_item_list(selected_realm_id)


if __name__ == "__main__":
    main()
