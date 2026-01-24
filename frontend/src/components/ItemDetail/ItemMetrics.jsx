import PriceDisplay from '../PriceDisplay'
import TrendBadge from '../TrendBadge'

export function ItemMetrics({ item, itemDetail, sales3d, styles }) {
    // Note: styles prop passed from parent (ItemDetailModal)
    // We also use 'stats-grid' and 'stat-card' global classes if we want to reuse index.css styles,
    // or we define them in module. Based on our module file, we need to decide.
    // In our module we defined .statsGrid override inside .modalMetrics, but ideally we use scoped classes entirely if possible.
    // But PriceDisplay uses global 'price'. 

    // Let's rely on global 'stat-card' for the look, as we didn't fully port it to module (or we should).
    // Actually, in step 205 we DID port statCard? Not explicitly in the CSS I wrote above?
    // Wait, I see ".modalMetrics .statsGrid" but do I see ".statCard"? 
    // Ah, I missed copying .stat-card styles into the module in my previous thought process?
    // Let's check the CSS content I generated in Step 205...
    // I see ".modalMetrics .statsGrid", ".scoreBadge"... I do not see .statCard explicit definition except relying on global?
    // Actually, Step 194 had .stat-card in ItemDetailModal.css? No, Step 199 (index.css) has .stat-card.
    // Step 194 (ItemDetailModal.css) has overrides. 

    // To be safe, let's stick to global classes where possible for generic cards, 
    // BUT wrap them in our container.

    return (
        <div className={`${styles?.statsGrid || 'stats-grid'} stats-grid`}>
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
                    {sales3d != null ? sales3d : 'N/A'}
                </div>
                <div className="stat-label">📦 Ventes (3j)</div>
            </div>
        </div>
    )
}
