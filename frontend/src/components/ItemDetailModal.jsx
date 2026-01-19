import { useState, useEffect } from 'react'
import PriceDisplay from './PriceDisplay'
import TrendBadge from './TrendBadge'
import { formatTimeDiff, formatPriceString, getFlagUrl } from '../utils/formatters'
import './ItemDetailModal.css'

function ItemDetailModal({ item, realmId, onClose }) {
    const [activeTab, setActiveTab] = useState('prices')
    const [loading, setLoading] = useState(true)
    const [itemDetail, setItemDetail] = useState(null)
    const [realmPrices, setRealmPrices] = useState([])
    const [bestServers, setBestServers] = useState([])

    // Fetch item details
    useEffect(() => {
        if (!item || !realmId) return

        const fetchDetails = async () => {
            setLoading(true)
            try {
                // Fetch item detail with history
                const detailRes = await fetch(`/api/items/${item.item_id}?realm_id=${realmId}`)
                if (detailRes.ok) {
                    const data = await detailRes.json()
                    setItemDetail(data)
                }

                // Fetch realm prices
                const pricesRes = await fetch(`/api/items/${item.item_id}/realms`)
                if (pricesRes.ok) {
                    const data = await pricesRes.json()
                    setRealmPrices(data.realm_prices || [])
                }

                // Fetch best servers
                const bestRes = await fetch(`/api/prices/${realmId}/${item.item_id}/best-servers`)
                if (bestRes.ok) {
                    const data = await bestRes.json()
                    setBestServers(data.servers || [])
                }
            } catch (err) {
                console.error('Failed to fetch item details:', err)
            } finally {
                setLoading(false)
            }
        }

        fetchDetails()
    }, [item, realmId])

    if (!item) return null

    const tabs = [
        { id: 'prices', icon: '📊', label: 'Prix par Serveur' },
        { id: 'history', icon: '📈', label: 'Historique Prix' },
        { id: 'volume', icon: '📦', label: 'Volume' },
        { id: 'best', icon: '🏆', label: 'Meilleurs Serveurs' },
        { id: 'stats', icon: '📉', label: 'Statistiques' },
        { id: 'craft', icon: '🔨', label: 'Craft' },
    ]

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="modal-title-row">
                        {item.icon_url && item.icon_url !== 'NONE' && (
                            <img src={item.icon_url} alt="" className="modal-icon" />
                        )}
                        <div>
                            <h2 className="modal-title">📋 {item.name}</h2>
                            <span className="badge">{item.category || 'Housing'}</span>
                        </div>
                    </div>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>

                {/* Metrics */}
                <div className="stats-grid modal-metrics">
                    <div className="stat-card">
                        <div className="stat-value"><PriceDisplay value={item.min_price} /></div>
                        <div className="stat-label">💰 Prix Minimum</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value"><PriceDisplay value={item.avg_price} /></div>
                        <div className="stat-label">📊 Prix Moyen</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value"><TrendBadge value={item.trend} /></div>
                        <div className="stat-label">📈 Tendance</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">
                            {item.volume_change != null ? (item.volume_change > 0 ? `+${item.volume_change}` : item.volume_change) : 'N/A'}
                        </div>
                        <div className="stat-label">📦 Volume Δ Semaine</div>
                    </div>
                </div>

                {/* Tabs */}
                <div className="modal-tabs">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            className={`modal-tab ${activeTab === tab.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            <span>{tab.icon}</span>
                            <span>{tab.label}</span>
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className="modal-body">
                    {loading ? (
                        <div className="loading-state">
                            <div className="spinner"></div>
                            <p>Chargement...</p>
                        </div>
                    ) : (
                        <>
                            {/* Prix par Serveur */}
                            {activeTab === 'prices' && (
                                <div className="tab-content">
                                    <h3>📊 Prix sur tous les serveurs</h3>
                                    {realmPrices.length === 0 ? (
                                        <p className="text-muted">Aucune donnée de prix disponible</p>
                                    ) : (
                                        <div className="table-container" style={{ maxHeight: '400px' }}>
                                            <table className="table">
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
                                                    {realmPrices
                                                        .filter(p => p.min_price)
                                                        .sort((a, b) => (a.min_price || Infinity) - (b.min_price || Infinity))
                                                        .map((price) => (
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
                                    )}
                                </div>
                            )}

                            {/* Historique Prix */}
                            {activeTab === 'history' && (
                                <div className="tab-content">
                                    <h3>📈 Historique des prix (21 jours)</h3>
                                    {itemDetail?.price_history?.length > 0 ? (
                                        <div className="chart-placeholder">
                                            <div className="table-container" style={{ maxHeight: '400px' }}>
                                                <table className="table">
                                                    <thead>
                                                        <tr>
                                                            <th>Date</th>
                                                            <th>Prix Min</th>
                                                            <th>Prix Moy</th>
                                                            <th>Enchères</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {itemDetail.price_history.map((h, i) => (
                                                            <tr key={i}>
                                                                <td>{new Date(h.recorded_at).toLocaleDateString()}</td>
                                                                <td><PriceDisplay value={h.min_price} /></td>
                                                                <td><PriceDisplay value={h.avg_price} /></td>
                                                                <td>{h.auction_count}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    ) : (
                                        <p className="text-muted">Aucun historique disponible</p>
                                    )}
                                </div>
                            )}

                            {/* Volume */}
                            {activeTab === 'volume' && (
                                <div className="tab-content">
                                    <h3>📦 Évolution du volume</h3>
                                    {itemDetail?.price_history?.length > 0 ? (
                                        <div className="table-container" style={{ maxHeight: '400px' }}>
                                            <table className="table">
                                                <thead>
                                                    <tr>
                                                        <th>Date</th>
                                                        <th>Quantité</th>
                                                        <th>Enchères</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {itemDetail.price_history.map((h, i) => (
                                                        <tr key={i}>
                                                            <td>{new Date(h.recorded_at).toLocaleDateString()}</td>
                                                            <td>{h.total_quantity}</td>
                                                            <td>{h.auction_count}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <p className="text-muted">Aucune donnée de volume disponible</p>
                                    )}
                                </div>
                            )}

                            {/* Meilleurs Serveurs */}
                            {activeTab === 'best' && (
                                <div className="tab-content">
                                    <h3>🏆 Meilleurs serveurs pour vendre</h3>
                                    {bestServers.length > 0 ? (
                                        <div className="table-container" style={{ maxHeight: '400px' }}>
                                            <table className="table">
                                                <thead>
                                                    <tr>
                                                        <th>#</th>
                                                        <th>Serveur</th>
                                                        <th>Prix</th>
                                                        <th>Volume Δ</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {bestServers.slice(0, 10).map((server, i) => (
                                                        <tr key={server.realm_id}>
                                                            <td>
                                                                {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                                                            </td>
                                                            <td>{server.realm_name}</td>
                                                            <td><PriceDisplay value={server.min_price} /></td>
                                                            <td className={server.volume_diff > 0 ? 'text-success' : server.volume_diff < 0 ? 'text-danger' : ''}>
                                                                {server.volume_diff != null ? (server.volume_diff > 0 ? `+${server.volume_diff}` : server.volume_diff) : 'N/A'}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <p className="text-muted">Aucune donnée disponible</p>
                                    )}
                                </div>
                            )}

                            {/* Statistiques */}
                            {activeTab === 'stats' && (
                                <div className="tab-content">
                                    <h3>📉 Statistiques</h3>
                                    <div className="stats-grid">
                                        <div className="stat-card">
                                            <div className="stat-value">{realmPrices.filter(p => p.min_price).length}</div>
                                            <div className="stat-label">Serveurs avec stock</div>
                                        </div>
                                        <div className="stat-card">
                                            <div className="stat-value">
                                                <PriceDisplay value={Math.min(...realmPrices.filter(p => p.min_price).map(p => p.min_price))} />
                                            </div>
                                            <div className="stat-label">Prix min global</div>
                                        </div>
                                        <div className="stat-card">
                                            <div className="stat-value">
                                                <PriceDisplay value={Math.max(...realmPrices.filter(p => p.min_price).map(p => p.min_price))} />
                                            </div>
                                            <div className="stat-label">Prix max global</div>
                                        </div>
                                        <div className="stat-card">
                                            <div className="stat-value">
                                                {itemDetail?.price_history?.length || 0}
                                            </div>
                                            <div className="stat-label">Points d'historique</div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Craft */}
                            {activeTab === 'craft' && (
                                <div className="tab-content">
                                    <h3>🔨 Informations de craft</h3>
                                    {item.profession_name ? (
                                        <div className="craft-info">
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
                                        </div>
                                    ) : (
                                        <p className="text-muted">🔨 Cet item n'est pas craftable ou la recette n'a pas encore été synchronisée.</p>
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

export default ItemDetailModal
