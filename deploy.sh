#!/bin/bash

# Configuration
SERVER_IP="46.224.219.107"
SERVER_USER="root"
REMOTE_DIR="/root/wow-housing"
ARCHIVE_NAME="deploy_package.tar.gz"

echo "🚀 Début du déploiement vers $SERVER_IP..."

# 1. Créer une archive locale (en excluant les dossiers lourds/inutiles)
echo "📦 Création de l'archive..."
tar --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='housing_data.db' \
    --exclude='housing_data_old.db' \
    --exclude='scheduler.log' \
    --exclude='deploy_package.tar.gz' \
    -czf $ARCHIVE_NAME .

echo "✅ Archive créée ($ARCHIVE_NAME)"

# 2. Copier l'archive sur le serveur
echo "📤 Envoi des fichiers vers le serveur..."
scp $ARCHIVE_NAME $SERVER_USER@$SERVER_IP:/root/$ARCHIVE_NAME

# 3. Exécuter les commandes sur le serveur via SSH
echo "🔧 Exécution des commandes sur le serveur..."
ssh $SERVER_USER@$SERVER_IP << EOF
    # Créer le dossier s'il n'existe pas
    mkdir -p $REMOTE_DIR
    
    # Déplacer l'archive
    mv /root/$ARCHIVE_NAME $REMOTE_DIR/
    
    # Aller dans le dossier
    cd $REMOTE_DIR
    
    # Extraire l'archive (écrase les anciens fichiers sauf la DB qui a été exclue de l'archive)
    tar -xzf $ARCHIVE_NAME
    
    # Supprimer l'archive
    rm $ARCHIVE_NAME
    
    # Reconstruire et relancer les containers
    echo "🔄 Reconstruction des containers..."
    docker compose down
    docker compose up -d --build
    
    # Nettoyage
    docker image prune -f
EOF

# 4. Nettoyage local
rm $ARCHIVE_NAME

echo "✅ Déploiement terminé avec succès !"
