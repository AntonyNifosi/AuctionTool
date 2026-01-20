# 🚀 Guide de Déploiement - WoW Housing Price Tracker

## Architecture
- **Backend**: FastAPI (Python) - Port 8000
- **Frontend**: React + Nginx - Port 8501
- **Base de données**: SQLite (Persistant via volume Docker)

## Prérequis
- Un VPS avec Docker et Docker Compose installés.
- Git installé sur le VPS.

## Installation Rapide

1. **Cloner le projet** (ou mettre à jour) :
   ```bash
   git clone <votre-repo>
   cd auction-tool-neo
   ```

2. **Configurer l'environnement** :
   Créez un fichier `.env` à la racine :
   ```env
   BLIZZARD_CLIENT_ID=votre_id
   BLIZZARD_CLIENT_SECRET=votre_secret
   API_REGION=eu
   DEFAULT_REALM=Hyjal
   ```

3. **Lancer le déploiement** :
   Utilisez le script fourni qui gère le pull, build et restart.
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

## Structure des Fichiers pour Déploiement

```
/root/wow-housing/
├── backend/            # Code API Python
├── frontend/           # Code Frontend React
├── docker-compose.yml  # Orchestration
├── deploy.sh           # Script de mise à jour
├── .env                # Secrets
└── housing_data.db     # Base de données (Persistée)
```

## Maintenance

- **Voir les logs Backend** : `docker compose logs -f backend`
- **Voir les logs Frontend** : `docker compose logs -f frontend`
- **Forcer un scan manuel** : L'API scanne automatiquement toutes les heures.
