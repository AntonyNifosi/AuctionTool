import { useState, useEffect, useMemo } from 'react'
import {
    LineChart, Line, AreaChart, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import PriceDisplay from './PriceDisplay'
import { formatTimeDiff, getFlagUrl } from '../utils/formatters'
import styles from './PetDetail/PetDetail.module.css'

function PetDetailModal({ pet, realmId, onClose }) {
    const [activeTab, setActiveTab] = useState('best')
    const [loading, setLoading] = useState(true)
    const [petDetail, setPetDetail] = useState(null)
    const [realmPrices, setRealmPrices] = useState([])

    // Best Servers sale/buy mode
    const [bestMode, setBestMode] = useState('sell') // 'sell' or 'buy'

    // Table sorting state
    const [sortConfig, setSortConfig] = useState({ key: 'min_price', direction: 'desc' })

    // Fetch pet details
    useEffect(() => {
        if (!pet || !realmId) return

        const fetchDetails = async () => {
            setLoading(true)
            try {
                const detailRes = await fetch(`/api/pets/${pet.pet_id}?realm_id=${realmId}`)
                if (detailRes.ok) {
                    const data = await detailRes.json()
                    setPetDetail(data)
                    setRealmPrices(data.realm_prices || [])
                }
            } catch (err) {
                console.error('Failed to fetch pet details:', err)
            } finally {
                setLoading(false)
            }
        }

        fetchDetails()
    }, [pet, realmId])

    if (!pet) return null

    const tabs = [
        { id: 'best', icon: '🏆', label: 'Meilleurs Serveurs' },
        { id: 'prices', icon: '📊', label: 'Prix par Serveur' },
        { id: 'history', icon: '📈', label: 'Historique Prix' },
        { id: 'volume', icon: '📦', label: 'Volume' },
        { id: 'stats', icon: '📉', label: 'Statistiques' },
    ]

    // Prepare chart data from price_history
    const chartData = (petDetail?.price_history || []).map(h => ({
        date: new Date(h.recorded_at).toLocaleDateString(),
        timestamp: new Date(h.recorded_at).getTime(),
        min_price: h.min_price / 10000,
        avg_price: h.avg_price ? h.avg_price / 10000 : null,
        quantity: h.total_quantity,
        dateLabel: new Date(h.recorded_at).toLocaleDateString() // Added for consistent accessing
    })).sort((a, b) => a.timestamp - b.timestamp)

    // Sortable table logic
    const handleSort = (key) => {
        setSortConfig(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
        }))
    }

    const getSortIndicator = (key) => {
        if (sortConfig.key !== key) return ''
        return sortConfig.direction === 'asc' ? ' ▲' : ' ▼'
    }

    // Sorted realm prices
    const sortedRealmPrices = useMemo(() => {
        const filtered = realmPrices.filter(p => p.min_price)
        return [...filtered].sort((a, b) => {
            const aVal = a[sortConfig.key] ?? 0
            const bVal = b[sortConfig.key] ?? 0
            if (sortConfig.direction === 'asc') {
                return aVal - bVal
            }
            return bVal - aVal
        })
    }, [realmPrices, sortConfig])

    // Best servers logic
    const bestServers = useMemo(() => {
        const filtered = realmPrices.filter(p => p.min_price && p.region !== 'ru_RU')
        if (filtered.length < 2) return filtered

        const prices = filtered.map(p => p.min_price)
        // Use sales_3d instead of total_quantity
        const sales = filtered.map(p => p.sales_3d || 0)

        const maxPrice = Math.max(...prices)
        const minPrice = Math.min(...prices)
        const maxSales = Math.max(...sales) || 1
        const minSales = Math.min(...sales)

        const populationScores = {
            'FULL': 1.0, 'HIGH': 0.8, 'MEDIUM': 0.6, 'LOW': 0.4, 'NEW_PLAYERS': 0.3, 'UNKNOWN': 0.5
        }
        const populationLabels = {
            'FULL': '🔴 Complet', 'HIGH': '🟠 Élevée', 'MEDIUM': '🟡 Moyenne', 'LOW': '🟢 Faible', 'NEW_PLAYERS': '🆕 Nouveaux', 'UNKNOWN': '❓ Inconnu'
        }

        const scored = filtered.map(server => {
            const price = server.min_price_3d ?? server.min_price
            const sale = server.sales_3d || 0
            const popType = server.population || 'UNKNOWN'

            const priceNorm = maxPrice !== minPrice ? (price - minPrice) / (maxPrice - minPrice) : 0.5
            // Normalize sales (higher = better to sell)
            const salesNorm = maxSales !== minSales ? (sale - minSales) / (maxSales - minSales) : 0
            const popScore = populationScores[popType] || 0.5

            let score
            if (bestMode === 'sell') {
                // Sell mode: High price, High sales, Good population
                score = (priceNorm * 0.4) + (salesNorm * 0.4) + (popScore * 0.2)
            } else {
                // Buy mode: Low price, (High stock? Sales irrelevant for buy usually, but maybe implies availability?)
                // For buy, we usually want Low Price. Keeping simple for now or reverting to price dominance.
                score = ((1 - priceNorm) * 0.7) + (popScore * 0.3)
            }

            return {
                ...server,
                score,
                scorePercent: Math.round(score * 100),
                populationLabel: populationLabels[popType] || popType
            }
        })

        return scored.sort((a, b) => b.score - a.score).slice(0, 10)
    }, [realmPrices, bestMode])

    // Custom Tooltip
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className={styles.customChartTooltip}>
                    <p className={styles.tooltipDate}>{label}</p>
                    {payload.map((p, i) => (
                        <p key={i} style={{ color: p.color, margin: 0 }}>
                            {p.name}: {
                                p.dataKey === 'min_price' || p.dataKey === 'avg_price' || p.dataKey === 'min_price_3d'
                                    ? `${p.value?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}g`
                                    : p.value?.toLocaleString()
                            }
                        </p>
                    ))}
                </div>
            )
        }
        return null
    }

    const getQualityColor = (quality) => {
        const colors = {
            poor: '#9d9d9d', common: '#ffffff', uncommon: '#1eff00', rare: '#0070dd', epic: '#a335ee', legendary: '#ff8000'
        }
        return colors[quality?.toLowerCase()] || colors.common
    }

    // Helper to get current realm stats
    const currentRealmStats = useMemo(() => {
        return realmPrices.find(r => r.realm_id === parseInt(realmId)) || {}
    }, [realmPrices, realmId])

    return (
        <div className={styles.modalOverlay} onClick={onClose}>
            <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className={styles.modalHeader}>
                    <div className={styles.modalTitleRow}>
                        {pet.icon_url && (
                            <img src={pet.icon_url} alt="" className={styles.modalIcon} />
                        )}
                        <div style={{ minWidth: 0 }}>
                            <h2 className={styles.modalTitle} style={{ color: getQualityColor(pet.quality) }}>
                                🐾 {pet.name}
                            </h2>
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                <span className="badge">{pet.creature_type || 'Battle Pet'}</span>
                                {pet.level && <span className="badge">Lvl {pet.level}</span>}
                            </div>
                        </div>
                    </div>
                    <button className={styles.modalClose} onClick={onClose}>✕</button>
                </div>

                {/* Metrics */}
                <div className={styles.modalMetrics}>
                    <div className={`${styles.statsGrid} stats-grid`}>
                        <div className="stat-card">
                            <div className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                                <PriceDisplay value={currentRealmStats.min_price || pet.min_price} />
                            </div>
                            <div className="stat-label">💰 Prix Minimum</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{currentRealmStats.sales_3d ?? 'N/A'}</div>
                            <div className="stat-label">📦 Ventes (3j)</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: getQualityColor(pet.quality) }}>
                                {pet.quality || 'N/A'}
                            </div>
                            <div className="stat-label">⭐ Qualité</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{pet.is_tradable ? '✅ Oui' : '❌ Non'}</div>
                            <div className="stat-label">💱 Échangeable</div>
                        </div>
                    </div>
                </div>

                {/* Tabs */}
                <div className={styles.modalTabs}>
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            className={`${styles.modalTab} ${activeTab === tab.id ? styles.activeTab : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            <span>{tab.icon}</span>
                            <span>{tab.label}</span>
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className={styles.modalBody}>
                    {loading ? (
                        <div className={styles.loadingState}>
                            <div className={styles.spinner}></div>
                            <p>Chargement...</p>
                        </div>
                    ) : (
                        <>
                            {/* Meilleurs Serveurs */}
                            {activeTab === 'best' && (
                                <div className={styles.tabContent}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-md)' }}>
                                        <h3 style={{ margin: 0 }}>🏆 Meilleurs Serveurs</h3>
                                        <div className="mode-toggle" style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
                                            <button
                                                className={`btn ${bestMode === 'sell' ? 'btn-primary' : 'btn-secondary'}`}
                                                onClick={() => setBestMode('sell')}
                                                style={{ padding: '6px 12px', fontSize: '0.875rem' }}
                                            >
                                                💰 Vente
                                            </button>
                                            <button
                                                className={`btn ${bestMode === 'buy' ? 'btn-primary' : 'btn-secondary'}`}
                                                onClick={() => setBestMode('buy')}
                                                style={{ padding: '6px 12px', fontSize: '0.875rem' }}
                                            >
                                                🛒 Achat
                                            </button>
                                        </div>
                                    </div>
                                    <p className="text-muted" style={{ marginBottom: 'var(--spacing-md)', fontSize: '0.875rem' }}>
                                        {bestMode === 'sell'
                                            ? '📈 Serveurs où ce pet se vend le plus cher'
                                            : '📉 Serveurs où ce pet est le moins cher à acheter'}
                                    </p>

                                    {bestServers.length === 0 ? (
                                        <p className="text-muted">Aucune donnée disponible.</p>
                                    ) : (
                                        <>
                                            <p className="text-muted" style={{ fontSize: '0.75rem', marginBottom: 'var(--spacing-sm)' }}>
                                                Score basé sur : Prix (40%) + Ventes (40%) + Population (20%)
                                            </p>

                                            {/* Desktop Table */}
                                            <div className={styles.tableContainer} style={{ maxHeight: '400px' }}>
                                                <table className={styles.table}>
                                                    <thead>
                                                        <tr>
                                                            <th style={{ width: 40 }}>#</th>
                                                            <th>Serveur</th>
                                                            <th>Population</th>
                                                            <th>Prix</th>
                                                            <th>Ventes (3j)</th>
                                                            <th>Score</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {bestServers.map((server, i) => (
                                                            <tr key={server.realm_id}>
                                                                <td style={{ fontWeight: 600 }}>
                                                                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                                                                </td>
                                                                <td>
                                                                    {server.region && (
                                                                        <img
                                                                            src={getFlagUrl(server.region)}
                                                                            alt=""
                                                                            style={{ width: 20, marginRight: 8, verticalAlign: 'middle' }}
                                                                        />
                                                                    )}
                                                                    {server.realm_name}
                                                                </td>
                                                                <td style={{ fontSize: '0.85rem' }}>
                                                                    {server.populationLabel || server.population || 'N/A'}
                                                                </td>
                                                                <td><PriceDisplay value={server.min_price} /></td>
                                                                <td>{server.sales_3d ?? '0'}</td>
                                                                <td style={{ fontWeight: 600, color: 'var(--accent)' }}>
                                                                    {server.scorePercent}%
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>

                                            {/* Mobile List View */}
                                            <div className={styles.mobileModalGrid}>
                                                {bestServers.map((server, i) => (
                                                    <div className={styles.mobileListItem} key={server.realm_id}>
                                                        <div className={styles.mobileListHeader}>
                                                            <div className={styles.realmInfo}>
                                                                <span className={styles.rankEmoji}>
                                                                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}
                                                                </span>
                                                                {server.region && (
                                                                    <img
                                                                        src={getFlagUrl(server.region)}
                                                                        alt=""
                                                                        className={styles.realmFlag}
                                                                    />
                                                                )}
                                                                <span className="realm-name">{server.realm_name}</span>
                                                            </div>
                                                            <span style={{ fontWeight: 600, color: 'var(--accent)' }}>
                                                                {server.scorePercent}%
                                                            </span>
                                                        </div>
                                                        <div className={styles.mobileListRow}>
                                                            <span>Prix (3j): <PriceDisplay value={server.min_price_3d ?? server.min_price} /></span>
                                                            <span className="text-muted">Pop: {server.populationLabel || transformPop(server.population)}</span>
                                                        </div>
                                                        <div className={styles.mobileListRow}>
                                                            <span className="text-muted">Ventes: {server.sales_3d ?? '0'}</span>
                                                            <span className="text-muted">{bestMode === 'sell' ? 'Vente' : 'Achat'}</span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            {/* Prix par Serveur */}
                            {activeTab === 'prices' && (
                                <div className={styles.tabContent}>
                                    <h3>📊 Prix sur tous les serveurs</h3>
                                    <p className="text-muted" style={{ marginBottom: 'var(--spacing-sm)', fontSize: '0.75rem' }}>
                                        💡 Cliquez sur un en-tête de colonne pour trier
                                    </p>
                                    {sortedRealmPrices.length === 0 ? (
                                        <p className="text-muted">Aucune donnée de prix disponible pour ce pet.</p>
                                    ) : (
                                        <>
                                            {/* Desktop Table */}
                                            <div className={styles.tableContainer} style={{ maxHeight: '500px' }}>
                                                <table className={styles.table}>
                                                    <thead>
                                                        <tr>
                                                            <th onClick={() => handleSort('realm_name')} style={{ cursor: 'pointer' }}>
                                                                Serveur{getSortIndicator('realm_name')}
                                                            </th>
                                                            <th onClick={() => handleSort('min_price_3d')} style={{ cursor: 'pointer' }}>
                                                                Prix Min (3j){getSortIndicator('min_price_3d')}
                                                            </th>
                                                            <th onClick={() => handleSort('min_price')} style={{ cursor: 'pointer' }}>
                                                                Prix Actuel{getSortIndicator('min_price')}
                                                            </th>
                                                            <th onClick={() => handleSort('sales_3d')} style={{ cursor: 'pointer' }}>
                                                                Ventes (3j){getSortIndicator('sales_3d')}
                                                            </th>
                                                            <th>Maj</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {sortedRealmPrices.map((price) => (
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
                                                                <td>{price.sales_3d ?? 0}</td>
                                                                <td className="text-muted">{formatTimeDiff(price.recorded_at)}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>

                                            {/* Mobile List View */}
                                            <div className={styles.mobileModalGrid}>
                                                {sortedRealmPrices.map((price) => (
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
                                                            <div className="flex flex-col items-end">
                                                                <span className="text-xs text-muted">3j:</span>
                                                                <PriceDisplay value={price.min_price_3d ?? price.min_price} />
                                                            </div>
                                                        </div>
                                                        <div className={styles.mobileListRow}>
                                                            <span>Actuel: <PriceDisplay value={price.min_price} /></span>
                                                            <span className="text-muted">Ventes: {price.sales_3d ?? 0}</span>
                                                            <span className="text-muted">{formatTimeDiff(price.recorded_at)}</span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            {/* Historique Prix */}
                            {activeTab === 'history' && (
                                <div className={styles.tabContent}>
                                    <h3>📈 Historique des prix (21 jours)</h3>
                                    {chartData.length > 0 ? (
                                        <div style={{ width: '100%', height: 400 }}>
                                            <ResponsiveContainer>
                                                <LineChart
                                                    data={chartData}
                                                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                                                >
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                                    <XAxis dataKey="date" stroke="#888" tick={{ fontSize: 12 }} />
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
                                        <p className="text-muted">Aucun historique disponible. Les données s'accumuleront au fil des scans.</p>
                                    )}
                                </div>
                            )}

                            {/* Volume */}
                            {activeTab === 'volume' && (
                                <div className={styles.tabContent}>
                                    <h3>📦 Évolution du volume</h3>
                                    {chartData.length > 0 ? (
                                        <div style={{ width: '100%', height: 400 }}>
                                            <ResponsiveContainer>
                                                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                                    <XAxis dataKey="date" stroke="#888" tick={{ fontSize: 12 }} />
                                                    <YAxis stroke="#888" />
                                                    <Tooltip content={<CustomTooltip />} />
                                                    <Legend />
                                                    <Area
                                                        type="monotone"
                                                        dataKey="quantity"
                                                        name="Quantité totale"
                                                        fill="#4CAF50"
                                                        stroke="#4CAF50"
                                                        fillOpacity={0.3}
                                                    />
                                                </AreaChart>
                                            </ResponsiveContainer>
                                        </div>
                                    ) : (
                                        <p className="text-muted">Aucune donnée de volume disponible.</p>
                                    )}
                                </div>
                            )}

                            {/* Statistiques */}
                            {activeTab === 'stats' && (
                                <div className={styles.tabContent}>
                                    <h3>📉 Statistiques</h3>
                                    <div className={`${styles.statsGrid} stats-grid`}>
                                        <div className="stat-card">
                                            <div className="stat-value">{realmPrices.filter(p => p.min_price).length}</div>
                                            <div className="stat-label">Serveurs avec stock</div>
                                        </div>
                                        <div className="stat-card">
                                            <div className="stat-value">
                                                {realmPrices.filter(p => p.min_price).length > 0 ? (
                                                    <PriceDisplay value={Math.min(...realmPrices.filter(p => p.min_price).map(p => p.min_price))} />
                                                ) : 'N/A'}
                                            </div>
                                            <div className="stat-label">Prix min global</div>
                                        </div>
                                        <div className="stat-card">
                                            <div className="stat-value">
                                                {realmPrices.filter(p => p.min_price).length > 0 ? (
                                                    <PriceDisplay value={Math.max(...realmPrices.filter(p => p.min_price).map(p => p.min_price))} />
                                                ) : 'N/A'}
                                            </div>
                                            <div className="stat-label">Prix max global</div>
                                        </div>
                                        <div className="stat-card">
                                            <div className="stat-value">{petDetail?.price_history?.length || 0}</div>
                                            <div className="stat-label">Points d'historique</div>
                                        </div>
                                    </div>

                                    {/* Additional Info */}
                                    <div style={{ marginTop: 'var(--spacing-lg)' }}>
                                        <h4>ℹ️ Informations</h4>
                                        <ul style={{ color: 'var(--text-muted)', listStyle: 'none', padding: 0 }}>
                                            <li>🏷️ <strong>Source :</strong> {pet.source || 'Inconnue'}</li>
                                            <li>🐾 <strong>Type :</strong> {pet.creature_type || 'Inconnue'}</li>
                                            <li>🔢 <strong>ID :</strong> {pet.pet_id}</li>
                                        </ul>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

export default PetDetailModal
