"""
Scheduler - Service de scan automatique du marché
Tourne en arrière-plan et lance les scans toutes les heures
"""
import sys

# Force UTF-8 for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import schedule
import time
import logging
from datetime import datetime

# Configuration du logging
# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def run_market_scan():
    """Lance un scan complet du marché"""
    try:
        logger.info("Démarrage du scan automatique du marché...")
        
        # Importer ici pour éviter les problèmes de circular import
        from update_manager import UpdateManager
        from data_manager import get_data_manager
        
        # Créer une instance et lancer le scan
        mgr = UpdateManager()
        
        # Run process synchronously
        logger.info("Scan en cours (cela peut prendre plusieurs minutes)...")
        mgr._run_process()
        
        # Nettoyer les anciennes données (garder 7 jours)
        logger.info("Nettoyage des données anciennes...")
        dm = get_data_manager()
        dm.cleanup_old_data(days=7)
        dm.cleanup_old_pet_data(days=7)
        
        logger.info("Scan du marché terminé avec succès!")
        
    except Exception as e:
        logger.error(f"Erreur lors du scan: {str(e)}")


def main():
    """Point d'entrée du scheduler"""
    logger.info("=" * 50)
    logger.info("Démarrage du Scheduler WoW Housing Price Tracker")
    logger.info("=" * 50)
    
    # Planifier le scan toutes les heures
    schedule.every(1).hour.do(run_market_scan)
    
    # Afficher le prochain scan prévu
    logger.info(f"Prochain scan prévu: dans 1 heure")
    logger.info("Le scheduler tourne en permanence. Ctrl+C pour arrêter.")
    
    # Lancer un premier scan au démarrage
    logger.info("Lancement du scan initial...")
    run_market_scan()
    
    # Boucle principale
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes


if __name__ == "__main__":
    main()
