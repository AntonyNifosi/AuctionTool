#!/bin/bash
# Script de déploiement automatique
# Usage: ./deploy.sh

echo "🚀 Début du déploiement..."

# 1. Récupérer les dernières modifications
echo "📥 Git Pull..."
git pull

# 2. Reconstruire et redémarrer les conteneurs
echo "🔄 Reconstruction des conteneurs..."
docker compose up -d --build

# 3. Nettoyage des images inutilisées (optionnel)
echo "🧹 Nettoyage..."
docker image prune -f

echo "✅ Déploiement terminé avec succès !"
echo "🌐 Frontend accessible sur le port 8501"
