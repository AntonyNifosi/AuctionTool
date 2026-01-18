# 🚀 Guide de Déploiement - WoW Housing Price Tracker

## Prérequis

- Un VPS (serveur Linux) avec Docker installé
  - Recommandé: Hetzner Cloud (~5€/mois), DigitalOcean, OVH
- Docker et Docker Compose installés sur le serveur

## Fichiers nécessaires

```
AuctionTool/
├── app.py
├── blizzard_api.py
├── config.py
├── data_manager.py
├── update_manager.py
├── scheduler.py          ← Nouveau
├── Dockerfile            ← Nouveau
├── docker-compose.yml    ← Nouveau
├── requirements.txt      ← Nouveau
├── .env                  ← Tes credentials
└── data/
    └── housing_data.db   ← Base de données
```

## Étapes de déploiement

### 1. Préparer le serveur

```bash
# Installer Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Installer Docker Compose
sudo apt install docker-compose-plugin
```

### 2. Copier les fichiers sur le serveur

```bash
# Depuis ton PC Windows (PowerShell)
scp -r C:\Users\Antony\Documents\Workspace\AuctionTool user@ton-serveur:/home/user/

# OU avec rsync (plus rapide pour les mises à jour)
rsync -avz --exclude 'data/' --exclude '.git/' ./AuctionTool/ user@ton-serveur:/home/user/AuctionTool/
```

### 3. Configurer l'environnement

```bash
# Sur le serveur
cd /home/user/AuctionTool

# Créer le fichier .env
nano .env
```

Contenu du `.env`:
```
BLIZZARD_CLIENT_ID=ton_client_id
BLIZZARD_CLIENT_SECRET=ton_client_secret
DEFAULT_REALM=Dalaran
```

### 4. Créer le dossier data

```bash
mkdir -p data
# Si tu as déjà une base de données, copie-la
# scp housing_data.db user@ton-serveur:/home/user/AuctionTool/data/
```

### 5. Lancer l'application

```bash
# Build et démarrage
docker compose up -d --build

# Vérifier les logs
docker compose logs -f

# Vérifier que tout tourne
docker compose ps
```

### 6. Accéder à l'application

Ouvre ton navigateur : `http://IP-DE-TON-SERVEUR:8501`

## Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f

# Logs du scheduler uniquement
docker compose logs -f scheduler

# Redémarrer les services
docker compose restart

# Arrêter tout
docker compose down

# Mettre à jour après modification du code
docker compose up -d --build
```

## Sécurité (optionnel mais recommandé)

### Ajouter HTTPS avec Nginx + Let's Encrypt

```bash
# Installer Nginx
sudo apt install nginx certbot python3-certbot-nginx

# Configurer le proxy
sudo nano /etc/nginx/sites-available/wow-housing
```

```nginx
server {
    listen 80;
    server_name ton-domaine.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
# Activer le site et HTTPS
sudo ln -s /etc/nginx/sites-available/wow-housing /etc/nginx/sites-enabled/
sudo certbot --nginx -d ton-domaine.com
sudo systemctl restart nginx
```

## Résolution de problèmes

### Le scheduler ne se lance pas
```bash
docker compose logs scheduler
# Vérifier que le fichier .env est présent
```

### La base de données est vide
```bash
# Copier ta base existante
scp housing_data.db user@ton-serveur:/home/user/AuctionTool/data/
docker compose restart
```

### Erreur de permissions
```bash
sudo chown -R $USER:$USER data/
chmod 755 data/
```

---

## Architecture

```
┌─────────────────────────────────────────────┐
│                   VPS                        │
│                                              │
│  ┌──────────────┐    ┌──────────────────┐   │
│  │  scheduler   │    │   web (8501)     │   │
│  │  (toutes     │    │   Streamlit      │   │
│  │  les heures) │    │                  │   │
│  └──────┬───────┘    └────────┬─────────┘   │
│         │                     │             │
│         ▼                     ▼             │
│  ┌─────────────────────────────────────┐    │
│  │           data/housing_data.db      │    │
│  │         (volume partagé)            │    │
│  └─────────────────────────────────────┘    │
│                                              │
└──────────────────────────────────────────────┘
```
