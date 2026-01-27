import { useState } from 'react'
import PriceDisplay from '../PriceDisplay'
import { formatTimeDiff, getFlagUrl } from '../../utils/formatters'

export function RealmPriceTable({ realmPrices, styles }) {
    const [sortConfig, setSortConfig] = useState({ key: 'min_price_3d', direction: 'asc' })

    if (realmPrices.length === 0) {
        return <p className="text-muted">Aucune donnée de prix disponible</p>
    }

    const sortData = (data) => {
        return [...data].sort((a, b) => {
            let aValue = a[sortConfig.key]
            let bValue = b[sortConfig.key]

            // Handle special cases
            if (sortConfig.key === 'min_price_3d') {
                aValue = a.min_price_3d ?? a.min_price
                bValue = b.min_price_3d ?? b.min_price
            }

            if (aValue === null || aValue === undefined) return 1
            if (bValue === null || bValue === undefined) return -1

            if (typeof aValue === 'string') {
                aValue = aValue.toLowerCase()
                bValue = bValue.toLowerCase()
            }

            if (aValue < bValue) {
                return sortConfig.direction === 'asc' ? -1 : 1
            }
            if (aValue > bValue) {
                return sortConfig.direction === 'asc' ? 1 : -1
            }
            return 0
        })
    }

    const requestSort = (key) => {
        let direction = 'asc'
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc'
        }
        setSortConfig({ key, direction })
    }

    const getSortIndicator = (key) => {
        if (sortConfig.key !== key) return '↕️'
        return sortConfig.direction === 'asc' ? '⬆️' : '⬇️'
    }

    // Filter out items with no min_price for display safety, 
    // but we can also display them if needed. 
    // Original logic filtered them: .filter(p => p.min_price)
    // We will keep it but maybe it hides "out of stock" servers?
    // Let's keep existing behavior.
    const filteredPrices = realmPrices.filter(p => p.min_price)
    const sortedPrices = sortData(filteredPrices)

    return (
        <>
            {/* Desktop Table */}
            <div className={styles.tableContainer} style={{ maxHeight: '500px' }}>
                <table className={styles.table}>
                    <thead>
                        <tr>
                            <th onClick={() => requestSort('realm_name')} style={{ cursor: 'pointer' }}>
                                Serveur {getSortIndicator('realm_name')}
                            </th>
                            <th onClick={() => requestSort('min_price_3d')} style={{ cursor: 'pointer' }}>
                                Prix Min (3j) {getSortIndicator('min_price_3d')}
                            </th>
                            <th onClick={() => requestSort('min_price')} style={{ cursor: 'pointer' }}>
                                Prix Actuel {getSortIndicator('min_price')}
                            </th>
                            <th onClick={() => requestSort('total_quantity')} style={{ cursor: 'pointer' }}>
                                Quantité {getSortIndicator('total_quantity')}
                            </th>
                            <th onClick={() => requestSort('sales_3d')} style={{ cursor: 'pointer' }}>
                                Ventes (3j) {getSortIndicator('sales_3d')}
                            </th>
                            <th onClick={() => requestSort('recorded_at')} style={{ cursor: 'pointer' }}>
                                Maj {getSortIndicator('recorded_at')}
                            </th>
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
                                <td><PriceDisplay value={price.min_price_3d ?? price.min_price} /></td>
                                <td><PriceDisplay value={price.min_price} /></td>
                                <td>{price.total_quantity ?? 'N/A'}</td>
                                <td>{price.sales_3d ?? 0}</td>
                                <td className="text-muted">{formatTimeDiff(price.recorded_at)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Mobile List View - kept sorted for consistency */}
            <div className={styles.mobileModalGrid}>
                {sortedPrices.map((price) => (
                    <div className={styles.mobileListItem} key={price.realm_id}>
                        <div className={styles.mobileListHeader} style={{ gap: '16px' }}>
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
                            <div className="flex flex-col items-end" style={{ minWidth: 'fit-content' }}>
                                <span className="text-xs text-muted" style={{ marginBottom: '4px' }}>Prix min / 3j:</span>
                                <div style={{ marginTop: '0px' }}>
                                    <PriceDisplay value={price.min_price_3d ?? price.min_price} />
                                </div>
                            </div>
                        </div>
                        <div className={styles.mobileListRow}>
                            <span className="text-muted">Actuel: <PriceDisplay value={price.min_price} /></span>
                            <span className="text-muted">Qté: {price.total_quantity ?? 'N/A'}</span>
                            <span className="text-muted">Ventes (3j): {price.sales_3d ?? 0}</span>
                        </div>
                    </div>
                ))}
            </div>
        </>
    )
}
