# 🏠 WoW Housing Price Tracker (Neo)

Application moderne pour suivre les prix des items de housing World of Warcraft via l'API Blizzard.
Refonte complète en **React + FastAPI**.

## 🚀 Stack Technique

- **Backend**: FastAPI, Python 3.11, SQLite
- **Frontend**: React 18, Vite, Recharts
- **Déploiement**: Docker Compose, Nginx

## 📋 Fonctionnalités

### 🔍 Recherche et Suivi
- **Items Housing** : Prix, tendances, et volumes d'échange.
- **Pets** : Suivi des mascottes et de leur valeur.
- **Crafts** : Calcul de rentabilité pour les métiers.

### 📊 Analyses
- **Meilleurs Serveurs** : Algorithme de scoring (40% Prix, 40% Volume, 20% Population).
- **Collection** : Import de collection Battle.net et valorisation.

## 🛠️ Installation Locale

### Backend
```bash
cd backend
# Idéalement dans un venv
pip install -r ../requirements.txt
python -m uvicorn backend.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Accès : `http://localhost:5173` (Dev)

## 🐳 Déploiement

Voir [DEPLOY.md](DEPLOY.md) pour les instructions détaillées.
Le projet utilise `docker-compose` pour orchestrer le backend et le frontend.

```bash
./deploy.sh
```
