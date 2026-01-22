import PriceDisplay from '../PriceDisplay'

export function CraftInfo({ item, itemDetail, styles }) {
    if (!item.profession_name) {
        return <p className="text-muted">🔨 Cet item n'est pas craftable ou la recette n'a pas encore été synchronisée.</p>
    }

    return (
        <div className={styles.craftInfo}>
            <p><strong>Métier :</strong> {item.profession_name}</p>
            {item.craft_cost && (
                <p><strong>Coût de craft :</strong> <PriceDisplay value={item.craft_cost} /></p>
            )}
            {item.min_price && item.craft_cost && (
                <p>
                    <strong>Profit estimé :</strong>{' '}
                    <span className={item.min_price > item.craft_cost ? 'text-success' : 'text-danger'}>
                        <PriceDisplay value={item.min_price - item.craft_cost} />
                    </span>
                </p>
            )}

            {itemDetail?.reagents && itemDetail.reagents.length > 0 && (
                <div className={styles.reagentsSection}>
                    <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        🧩 Composants nécessaires
                    </h4>
                    <div className={styles.reagentsList}>
                        {itemDetail.reagents.map(r => (
                            <div key={r.item_id} className={styles.reagentItem}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                    {r.icon_url ? (
                                        <img src={r.icon_url} alt="" style={{ width: 32, height: 32, borderRadius: 4, border: '1px solid var(--border-color)' }} />
                                    ) : (
                                        <div style={{ width: 32, height: 32, borderRadius: 4, background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>📦</div>
                                    )}
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span style={{ fontWeight: 500 }}>{r.name}</span>
                                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Qté: {r.quantity}</span>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div style={{ fontSize: '0.85rem' }}>PU: <PriceDisplay value={r.unit_price} /></div>
                                    <div style={{ fontWeight: 500 }}>Total: <PriceDisplay value={(r.unit_price || 0) * r.quantity} /></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
