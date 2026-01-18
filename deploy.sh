#!/bin/bash
# Script de déploiement - WoW Housing Price Tracker
# Usage: ./deploy.sh

# Configuration
SERVER_IP="46.224.219.107"
SERVER_USER="root"
LOCAL_PATH="/c/Users/Antony/Documents/Workspace/AuctionTool"
REMOTE_PATH="/root/wow-housing"

echo "🚀 Déploiement vers $SERVER_IP..."
echo ""

# Copier tous les fichiers en une seule commande
echo "📁 Copie des fichiers..."
scp "$LOCAL_PATH/app.py" \
    "$LOCAL_PATH/blizzard_api.py" \
    "$LOCAL_PATH/config.py" \
    "$LOCAL_PATH/data_manager.py" \
    "$LOCAL_PATH/update_manager.py" \
    "$LOCAL_PATH/scheduler.py" \
    "$LOCAL_PATH/requirements.txt" \
    "$LOCAL_PATH/Dockerfile" \
    "$LOCAL_PATH/docker-compose.yml" \
    "$SERVER_USER@$SERVER_IP:$REMOTE_PATH/"

echo ""
echo "🔄 Redémarrage des services Docker..."
ssh "$SERVER_USER@$SERVER_IP" "cd $REMOTE_PATH && docker compose up -d --build"

echo ""
echo "✅ Déploiement terminé !"
echo "🌐 Accès: http://$SERVER_IP:8501"
