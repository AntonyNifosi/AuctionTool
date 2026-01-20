import { useState, useEffect } from 'react'
import {
    LineChart, Line, AreaChart, Area, ComposedChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
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

    // Prepare chart data with unique datetime labels
    // Prepare chart data with unique datetime labels
    const chartData = (itemDetail?.price_history || []).map((h, index) => {
        const dt = new Date(h.recorded_at)
        return {
            // Use index-based key for X-axis to ensure uniqueness
            dateLabel: `${dt.toLocaleDateString()} ${dt.getHours()}h`,
            date: dt.toLocaleDateString(),
            timestamp: dt.getTime(),
            min_price: h.min_price / 10000, // Convert to gold
            avg_price: h.avg_price ? h.avg_price / 10000 : null,
            quantity: h.total_quantity,
            auctions: h.auction_count
        }
    }).sort((a, b) => a.timestamp - b.timestamp)

    // Custom Tooltip for charts
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="custom-chart-tooltip">
                    <p className="tooltip-date">{label}</p>
                    {payload.map((p, i) => (
                        <p key={i} style={{ color: p.color }}>
                            {p.name}: {
                                p.dataKey === 'min_price' || p.dataKey === 'avg_price'
                                    ? `${p.value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}g`
                                    : p.value.toLocaleString()
                            }
                        </p>
                    ))}
                </div>
            )
        }
        return null
    }

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="modal-title-row" style={{ flexWrap: 'nowrap' }}>
                        {item.icon_url && item.icon_url !== 'NONE' && (
                            <img src={item.icon_url} alt="" className="modal-icon" style={{ flexShrink: 0 }} />
                        )}
                        <div style={{ minWidth: 0 }}>
                            <h2 className="modal-title" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                📋 {item.name}
                            </h2>
                            <span className="badge">{item.category || 'Housing'}</span>
                        </div>
                    </div>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>

                {/* Metrics */}
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
                                        <div className="table-container" style={{ maxHeight: '500px' }}>
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
                                    {chartData.length > 0 ? (
                                        <div style={{ width: '100%', height: 400 }}>
                                            <ResponsiveContainer>
                                                <LineChart
                                                    data={chartData}
                                                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                                                >
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                                    <XAxis
                                                        dataKey="dateLabel"
                                                        stroke="#888"
                                                        tick={{ fontSize: 10 }}
                                                        interval="preserveStartEnd"
                                                    />
                                                    <YAxis
                                                        stroke="#888"
                                                        tickFormatter={(value) => {
                                                            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
                                                            if (value >= 1000) return `${(value / 1000).toFixed(0)}k`
                                                            return value
                                                        }}
                                                        width={40}
                                                        tick={{ fontSize: 11 }}
                                                    />
                                                    <Tooltip
                                                        content={<CustomTooltip />}
                                                        cursor={{ stroke: '#666', strokeDasharray: '3 3' }}
                                                    />
                                                    <Legend />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="min_price"
                                                        name="Prix Min"
                                                        stroke="#00ff00"
                                                        strokeWidth={2}
                                                        dot={{ r: 4, fill: '#00ff00' }}
                                                        activeDot={{ r: 8, fill: '#00ff00', stroke: '#fff', strokeWidth: 2 }}
                                                        connectNulls
                                                    />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="avg_price"
                                                        name="Prix Moyen"
                                                        stroke="#FFD100"
                                                        strokeWidth={2}
                                                        dot={{ r: 4, fill: '#FFD100' }}
                                                        activeDot={{ r: 8, fill: '#FFD100', stroke: '#fff', strokeWidth: 2 }}
                                                        connectNulls
                                                    />
                                                </LineChart>
                                            </ResponsiveContainer>
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
                                    {chartData.length > 0 ? (
                                        <div style={{ width: '100%', height: 400 }}>
                                            <ResponsiveContainer>
                                                <ComposedChart
                                                    data={chartData}
                                                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                                                >
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                                    <XAxis
                                                        dataKey="dateLabel"
                                                        stroke="#888"
                                                        tick={{ fontSize: 10 }}
                                                        interval="preserveStartEnd"
                                                    />
                                                    <YAxis
                                                        stroke="#888"
                                                        tickFormatter={(value) => {
                                                            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
                                                            if (value >= 1000) return `${(value / 1000).toFixed(0)}k`
                                                            return value
                                                        }}
                                                        width={40}
                                                        tick={{ fontSize: 11 }}
                                                    />
                                                    <Tooltip
                                                        content={<CustomTooltip />}
                                                        cursor={{ stroke: '#666', strokeDasharray: '3 3' }}
                                                    />
                                                    <Legend />
                                                    <Area
                                                        type="monotone"
                                                        dataKey="quantity"
                                                        name="Quantité totale"
                                                        fill="#4CAF50"
                                                        stroke="#4CAF50"
                                                        fillOpacity={0.3}
                                                        dot={{ r: 4, fill: '#4CAF50' }}
                                                        activeDot={{ r: 8, fill: '#4CAF50', stroke: '#fff', strokeWidth: 2 }}
                                                    />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="auctions"
                                                        name="Nombre d'enchères"
                                                        stroke="#FF9800"
                                                        strokeDasharray="5 5"
                                                        strokeWidth={2}
                                                        dot={{ r: 4, fill: '#FF9800' }}
                                                        activeDot={{ r: 8, fill: '#FF9800', stroke: '#fff', strokeWidth: 2 }}
                                                    />
                                                </ComposedChart>
                                            </ResponsiveContainer>
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
                                        <div className="table-container" style={{ maxHeight: '500px' }}>
                                            <table className="table">
                                                <thead>
                                                    <tr>
                                                        <th>#</th>
                                                        <th>Serveur</th>
                                                        <th>Prix</th>
                                                        <th>Volume Δ</th>
                                                        <th>Score</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {bestServers.slice(0, 10).map((server, i) => (
                                                        <tr key={server.realm_name || i}>
                                                            <td>
                                                                {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                                                            </td>
                                                            <td>{server.realm_name}</td>
                                                            <td><PriceDisplay value={server.min_price} /></td>
                                                            <td className={(server.volume ?? server.volume_exchanged) > 0 ? 'text-success' : (server.volume ?? server.volume_exchanged) < 0 ? 'text-danger' : ''}>
                                                                {(server.volume ?? server.volume_exchanged) != null ? ((server.volume ?? server.volume_exchanged) > 0 ? `+${(server.volume ?? server.volume_exchanged)}` : (server.volume ?? server.volume_exchanged)) : 'N/A'}
                                                            </td>
                                                            <td>
                                                                <span className={`score-badge ${server.score >= 70 ? 'score-high' : server.score >= 40 ? 'score-medium' : 'score-low'}`}>
                                                                    {server.score > 0 ? `${Math.round(server.score)}%` : '⚠'}
                                                                </span>
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

                                            {itemDetail?.reagents && itemDetail.reagents.length > 0 && (
                                                <div className="reagents-section" style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                                                    <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                        🧩 Composants nécessaires
                                                    </h4>
                                                    <div className="reagents-list">
                                                        {itemDetail.reagents.map(r => (
                                                            <div key={r.item_id} className="reagent-item" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px', background: 'var(--bg-secondary)', marginBottom: '4px', borderRadius: 'var(--radius-sm)' }}>
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
