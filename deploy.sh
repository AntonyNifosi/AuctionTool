#!/bin/bash

# Configuration
SERVER_IP="46.224.219.107"
SERVER_USER="root"
REMOTE_DIR="/root/wow-housing"
ARCHIVE_NAME="deploy_package.tar.gz"

echo "🚀 Début du déploiement vers $SERVER_IP..."

# 1. & 2. & 3. Créer l'archive, l'envoyer et déployer en UNE SEULE connexion SSH (1 seul mot de passe)
echo "📦 Création de l'archive et déploiement en cours..."

# On pipe la sortie de tar (stdout) directement dans l'entrée de ssh (stdin)
# Sur le serveur, 'cat > ...' lit ce flux pour créer le fichier
tar --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='housing_data.db' \
    --exclude='housing_data_old.db' \
    --exclude='scheduler.log' \
    --exclude='deploy_package.tar.gz' \
    -czf - . | ssh $SERVER_USER@$SERVER_IP "
        # 1. Récupérer l'archive depuis le flux
        echo \"📥 Réception de l'archive sur le serveur...\"
        cat > /root/$ARCHIVE_NAME

        # 2. Préparer le dossier
        echo \"📂 Préparation des dossiers...\"
        mkdir -p $REMOTE_DIR
        mv /root/$ARCHIVE_NAME $REMOTE_DIR/
        cd $REMOTE_DIR
        
        # 3. Extraire
        echo \"📦 Extraction...\"
        tar -xzf $ARCHIVE_NAME
        rm $ARCHIVE_NAME
        
        # 4. Docker
        echo \"🔄 Reconstruction des containers...\"
        docker compose down
        docker compose up -d --build
        
        # 5. Nettoyage
        docker image prune -f
        echo \"✨ Déploiement terminé sur le serveur !\"
"

echo "✅ Déploiement terminé avec succès !"
