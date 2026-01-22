import PriceDisplay from '../PriceDisplay'
import { formatTimeDiff, getFlagUrl } from '../../utils/formatters'

export function RealmPriceTable({ realmPrices, styles }) {
    if (realmPrices.length === 0) {
        return <p className="text-muted">Aucune donnée de prix disponible</p>
    }

    const sortedPrices = realmPrices
        .filter(p => p.min_price)
        .sort((a, b) => (a.min_price || Infinity) - (b.min_price || Infinity))

    return (
        <>
            {/* Desktop Table */}
            <div className={styles.tableContainer} style={{ maxHeight: '500px' }}>
                <table className={styles.table}>
                    <thead>
                        <tr>
                            <th>Serveur</th>
                            <th>Prix Min</th>
                            <th>Prix Moy</th>
                            <th>Quantité</th>
                            <th>Maj</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedPrices.map((price) => (
                            <tr key={price.realm_id}>
                                <td>
                                    {price.region && (
                                        <img
                                            src={getFlagUrl(price.region)}
                                            alt=""
                                            style={{ width: 20, marginRight: 8, verticalAlign: 'middle' }}
                                        />
                                    )}
                                    {price.realm_name}
                                </td>
                                <td><PriceDisplay value={price.min_price} /></td>
                                <td><PriceDisplay value={price.avg_price} /></td>
                                <td>{price.total_quantity ?? 'N/A'}</td>
                                <td className="text-muted">{formatTimeDiff(price.recorded_at)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Mobile List View */}
            <div className={styles.mobileModalGrid}>
                {sortedPrices.map((price) => (
                    <div className={styles.mobileListItem} key={price.realm_id}>
                        <div className={styles.mobileListHeader}>
                            <div className={styles.realmInfo}>
                                {price.region && (
                                    <img
                                        src={getFlagUrl(price.region)}
                                        alt=""
                                        className={styles.realmFlag}
                                    />
                                )}
                                <span className="realm-name">{price.realm_name}</span>
                            </div>
                            <PriceDisplay value={price.min_price} />
                        </div>
                        <div className={styles.mobileListRow}>
                            <span className="text-muted">Moy: <PriceDisplay value={price.avg_price} /></span>
                            <span className="text-muted">Qté: {price.total_quantity ?? 'N/A'}</span>
                        </div>
                    </div>
                ))}
            </div>
        </>
    )
}
