import PriceDisplay from '../PriceDisplay'
import TrendBadge from '../TrendBadge'

export function ItemMetrics({ item, itemDetail }) {
    return (
        <div className="stats-grid modal-metrics">
            <div className="stat-card">
                <div className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                    <PriceDisplay value={itemDetail?.current_price ?? item.min_price} />
                </div>
                <div className="stat-label">💰 Prix Minimum</div>
            </div>
            <div className="stat-card">
                <div className="stat-value"><PriceDisplay value={itemDetail?.avg_price ?? item.avg_price} /></div>
                <div className="stat-label">📊 Prix Moyen</div>
            </div>
            <div className="stat-card">
                <div className="stat-value"><TrendBadge value={itemDetail?.trend ?? item.trend} /></div>
                <div className="stat-label">📈 Tendance</div>
            </div>
            <div className="stat-card">
                <div className="stat-value">
                    {(() => {
                        const raw = itemDetail?.volume_change ?? item.volume_change
                        const val = (raw && typeof raw === 'object') ? raw.change : raw

                        if (val == null) return 'N/A'
                        return val > 0 ? `+${val}` : val
                    })()}
                </div>
                <div className="stat-label">📦 Volume Δ Semaine</div>
            </div>
        </div>
    )
}
