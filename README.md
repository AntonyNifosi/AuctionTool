# 🏠 WoW Housing Price Tracker

Application Streamlit pour suivre les prix des items de housing World of Warcraft via l'API Blizzard.

## 🚀 Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Configurer les credentials Blizzard

1. Créez un compte développeur sur [Battle.net Developer Portal](https://develop.battle.net/access/clients)
2. Créez une nouvelle application pour obtenir votre `CLIENT_ID` et `CLIENT_SECRET`
3. Éditez le fichier `.env` et ajoutez vos credentials :

```env
BLIZZARD_CLIENT_ID=votre_client_id_ici
BLIZZARD_CLIENT_SECRET=votre_client_secret_ici
```

### 3. Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvrira dans votre navigateur à l'adresse `http://localhost:8501`

## 📋 Fonctionnalités

### Liste des Items de Housing
- Affichage de tous les items de housing avec leurs métriques
- Recherche par nom
- Filtrage par catégorie
- Tri par nom, prix ou tendance

### Pour chaque item :
- **Prix minimum** : Le prix le plus bas actuellement en vente
- **Prix moyen** : Moyenne des prix des enchères actives
- **Quantité** : Nombre total d'items en vente
- **Tendance** : Variation du prix par rapport à la moyenne sur 3 semaines (%)
- **Volume Δ** : Changement du nombre d'items en vente sur la dernière semaine

### Vue Détail d'un Item
- **Prix par Serveur** : Comparaison des prix sur tous les serveurs EU
- **Historique des Prix** : Graphique d'évolution sur les 3 dernières semaines
- **Statistiques** : Min, Max, Moyenne, Médiane, Écart-type

### Sélection du Serveur de Référence
- Dropdown dans la sidebar pour choisir le serveur principal
- Tous les prix de la liste utilisent ce serveur comme référence

## 🔄 Mise à jour des données

Cliquez sur le bouton **"🔄 Rafraîchir les données"** dans la sidebar pour récupérer les dernières enchères depuis l'API Blizzard.

> **Note** : Les données historiques s'accumulent au fil du temps. Plus vous rafraîchissez régulièrement, plus les tendances et volumes seront précis.

## 📁 Structure du projet

```
AuctionTool/
├── app.py              # Application Streamlit principale
├── blizzard_api.py     # Module d'interaction avec l'API Blizzard
├── data_manager.py     # Gestionnaire de données SQLite
├── config.py           # Configuration de l'application
├── requirements.txt    # Dépendances Python
├── .env                # Credentials (à configurer)
├── .env.example        # Template de credentials
├── .gitignore          # Fichiers ignorés par git
└── housing_data.db     # Base de données SQLite (créée automatiquement)
```

## ⚠️ Limitations

- **Pas d'historique API** : L'API Blizzard ne fournit pas d'historique des prix. Les tendances sont calculées à partir des données stockées localement.
- **Items de Housing** : L'API housing est récente (11.2.7). Si les endpoints ne sont pas disponibles, des items d'exemple sont utilisés.
- **Région EU uniquement** : L'application est configurée pour la région EU.

## 🔧 Configuration avancée

Modifiez `config.py` pour personnaliser :
- `TREND_WEEKS` : Nombre de semaines pour le calcul des tendances (défaut: 3)
- `CACHE_DURATION_HOURS` : Durée du cache des auctions (défaut: 1h)
- `DEFAULT_LOCALE` : Locale pour les noms d'items (défaut: fr_FR)
