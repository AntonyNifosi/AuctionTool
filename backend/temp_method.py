
    def get_pet_best_sales_candidates(self, pet_id: int, days: int = 3) -> List[Dict]:
        """
        Récupère les données consolidées pour les meilleures ventes de pets (prix min sur X jours).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            WITH Latest AS (
                SELECT realm_id, total_quantity, min_price,
                       ROW_NUMBER() OVER (PARTITION BY realm_id ORDER BY recorded_at DESC) as rn
                FROM pet_price_history
                WHERE pet_id = ?
            ),
            MinPriceWindow AS (
                SELECT realm_id, MIN(min_price) as min_price_window
                FROM pet_price_history
                WHERE pet_id = ? AND recorded_at >= ?
                GROUP BY realm_id
            )
            SELECT 
                r.name as realm_name,
                r.population,
                r.region,
                l.realm_id,
                COALESCE(mp.min_price_window, l.min_price) as min_price,
                l.total_quantity
            FROM Latest l
            JOIN realms r ON l.realm_id = r.realm_id
            LEFT JOIN MinPriceWindow mp ON l.realm_id = mp.realm_id
            WHERE l.rn = 1
        """, (pet_id, pet_id, start_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
