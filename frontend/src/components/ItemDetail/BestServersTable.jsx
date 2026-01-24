import PriceDisplay from '../PriceDisplay'

export function BestServersTable({ bestServers, styles }) {
    if (bestServers.length === 0) {
        return <p className="text-muted">Aucune donnée disponible</p>
    }

    const topServers = bestServers.slice(0, 10)

    return (
        <>
            {/* Desktop Table */}
            <div className={styles.tableContainer} style={{ maxHeight: '500px' }}>
                <table className={styles.table}>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Serveur</th>
                            <th>Prix</th>
                            <th>Ventes (3j)</th>
                            <th>Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {topServers.map((server, i) => (
                            <tr key={server.realm_name || i}>
                                <td>
                                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                                </td>
                                <td>{server.realm_name}</td>
                                <td><PriceDisplay value={server.min_price} /></td>
                                <td>
                                    {server.sales_3d ?? 'N/A'}
                                </td>
                                <td>
                                    <span className={`${styles.scoreBadge} ${server.score >= 70 ? styles.scoreHigh : server.score >= 40 ? styles.scoreMedium : styles.scoreLow}`}>
                                        {server.score > 0 ? `${Math.round(server.score)}%` : '⚠'}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Mobile List View */}
            <div className={styles.mobileModalGrid}>
                {topServers.map((server, i) => (
                    <div className={styles.mobileListItem} key={server.realm_name || i}>
                        <div className={styles.mobileListHeader}>
                            <div className={styles.realmInfo}>
                                <span className={styles.rankEmoji}>
                                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}
                                </span>
                                <span className="realm-name">{server.realm_name}</span>
                            </div>
                            <span className={`${styles.scoreBadge} ${server.score >= 70 ? styles.scoreHigh : server.score >= 40 ? styles.scoreMedium : styles.scoreLow}`}>
                                {server.score > 0 ? `${Math.round(server.score)}%` : '⚠'}
                            </span>
                        </div>
                        <div className={styles.mobileListRow}>
                            <PriceDisplay value={server.min_price} />
                            <span>
                                Ventes: {server.sales_3d ?? 'N/A'}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </>
    )
}
