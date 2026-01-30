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
                    <div className={styles.reagentsTableContainer}>
                        <table className={styles.reagentsTable}>
                            <thead>
                                <tr>
                                    <th style={{ width: 48 }}></th>
                                    <th>Composant</th>
                                    <th style={{ textAlign: 'right' }}>Qté</th>
                                    <th style={{ textAlign: 'right' }}>Prix Unit.</th>
                                    <th style={{ textAlign: 'right' }}>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {itemDetail.reagents.map(r => (
                                    <tr key={r.item_id}>
                                        <td style={{ textAlign: 'center', padding: '4px' }}>
                                            {r.icon_url ? (
                                                <img src={r.icon_url} alt="" style={{ width: 32, height: 32, borderRadius: 4, border: '1px solid var(--border-color)', display: 'block', margin: '0 auto' }} />
                                            ) : (
                                                <div style={{ width: 32, height: 32, borderRadius: 4, background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' }}>📦</div>
                                            )}
                                        </td>
                                        <td style={{ fontWeight: 500 }}>{r.name}</td>
                                        <td style={{ textAlign: 'right' }}>{r.quantity}</td>
                                        <td style={{ textAlign: 'right', fontSize: '0.85rem' }}><PriceDisplay value={r.unit_price} /></td>
                                        <td style={{ textAlign: 'right', fontWeight: 600 }}><PriceDisplay value={(r.unit_price || 0) * r.quantity} /></td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot>
                                <tr>
                                    <td colSpan="4" style={{ textAlign: 'right', fontWeight: 'bold', borderTop: '2px solid var(--border-color)' }}>Coût Total Estimé</td>
                                    <td style={{ textAlign: 'right', fontWeight: 'bold', borderTop: '2px solid var(--border-color)', color: 'var(--text-primary)' }}>
                                        <PriceDisplay value={item.craft_cost || 0} />
                                    </td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            )}
        </div>
    )
}
