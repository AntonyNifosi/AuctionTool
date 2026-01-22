import { useState, useEffect, useMemo } from 'react'
import {
    LineChart, Line, AreaChart, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import PriceDisplay from './PriceDisplay'
import { formatTimeDiff, getFlagUrl } from '../utils/formatters'
import './ItemDetailModal.css'

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
    // Prepare chart data from price_history
    const chartData = (petDetail?.price_history || []).map(h => ({
        date: new Date(h.recorded_at).toLocaleDateString(),
        timestamp: new Date(h.recorded_at).getTime(),
        min_price: h.min_price / 10000,
        avg_price: h.avg_price ? h.avg_price / 10000 : null,
        quantity: h.total_quantity,
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

    // Best servers for buy or sell - using consistent scoring algorithm
    // Score = (Price × 40%) + (Quantity × 40%) + (Population × 20%)
    const bestServers = useMemo(() => {
        // Filter servers with valid prices and exclude Russian servers (like Streamlit)
        const filtered = realmPrices.filter(p => p.min_price && p.region !== 'ru_RU')

        if (filtered.length < 2) return filtered

        // Get min/max for normalization
        const prices = filtered.map(p => p.min_price)
        const quantities = filtered.map(p => p.total_quantity || 0)

        const maxPrice = Math.max(...prices)
        const minPrice = Math.min(...prices)
        const maxQty = Math.max(...quantities) || 1
        const minQty = Math.min(...quantities)

        // Population scores (like Streamlit)
        const populationScores = {
            'FULL': 1.0,
            'HIGH': 0.8,
            'MEDIUM': 0.6,
            'LOW': 0.4,
            'NEW_PLAYERS': 0.3,
            'UNKNOWN': 0.5
        }

        const populationLabels = {
            'FULL': '🔴 Complet',
            'HIGH': '🟠 Élevée',
            'MEDIUM': '🟡 Moyenne',
            'LOW': '🟢 Faible',
            'NEW_PLAYERS': '🆕 Nouveaux',
            'UNKNOWN': '❓ Inconnu'
        }

        // Calculate scores for each server
        const scored = filtered.map(server => {
            const price = server.min_price
            const qty = server.total_quantity || 0
            const popType = server.population || 'UNKNOWN'

            // Normalize 0-1
            const priceNorm = maxPrice !== minPrice
                ? (price - minPrice) / (maxPrice - minPrice)
                : 0.5
            const qtyNorm = maxQty !== minQty
                ? (qty - minQty) / (maxQty - minQty)
                : 0.5
            const popScore = populationScores[popType] || 0.5

            let score
            if (bestMode === 'sell') {
                // For selling: high price is good, high quantity means competition (bad)
                score = (priceNorm * 0.4) + ((1 - qtyNorm) * 0.4) + (popScore * 0.2)
            } else {
                // For buying: low price is good, high quantity means more choice (good)
                score = ((1 - priceNorm) * 0.4) + (qtyNorm * 0.4) + (popScore * 0.2)
            }

            // Penalty if no quantity (item not available)
            if (qty === 0) {
                score = score * 0.1
            }

            return {
                ...server,
                score,
                scorePercent: Math.round(score * 100),
                populationLabel: populationLabels[popType] || popType
            }
        })

        // Sort by score descending and take top 10
        return scored.sort((a, b) => b.score - a.score).slice(0, 10)
    }, [realmPrices, bestMode])

    // Custom Tooltip
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="custom-chart-tooltip">
                    <p className="tooltip-date">{label}</p>
                    {payload.map((p, i) => (
                        <p key={i} style={{ color: p.color }}>
                            {p.name}: {
                                p.dataKey === 'min_price' || p.dataKey === 'avg_price'
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
            poor: '#9d9d9d',
            common: '#ffffff',
            uncommon: '#1eff00',
            rare: '#0070dd',
            epic: '#a335ee',
            legendary: '#ff8000'
        }
        return colors[quality?.toLowerCase()] || colors.common
    }

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="modal-title-row" style={{ flexWrap: 'nowrap' }}>
                        {pet.icon_url && (
                            <img src={pet.icon_url} alt="" className="modal-icon" style={{ flexShrink: 0 }} />
                        )}
                        <div style={{ minWidth: 0 }}>
                            <h2 className="modal-title" style={{ color: getQualityColor(pet.quality), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                🐾 {pet.name}
                            </h2>
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                <span className="badge">{pet.creature_type || 'Battle Pet'}</span>
                                {pet.level && <span className="badge">Lvl {pet.level}</span>}
                            </div>
                        </div>
                    </div>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>

                {/* Metrics */}
                <div className="stats-grid modal-metrics">
                    <div className="stat-card">
                        <div className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                            <PriceDisplay value={pet.min_price} />
                        </div>
                        <div className="stat-label">💰 Prix Minimum</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{pet.total_quantity ?? 'N/A'}</div>
                        <div className="stat-label">📦 Quantité dispo</div>
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
                            {/* Meilleurs Serveurs */}
                            {activeTab === 'best' && (
                                <div className="tab-content">
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
                                                Score basé sur : Prix (40%) + Quantité (40%) + Population (20%)
                                            </p>

                                            {/* Desktop Table */}
                                            <div className="table-container" style={{ maxHeight: '400px' }}>
                                                <table className="table">
                                                    <thead>
                                                        <tr>
                                                            <th style={{ width: 40 }}>#</th>
                                                            <th>Serveur</th>
                                                            <th>Population</th>
                                                            <th>Prix</th>
                                                            <th>Quantité</th>
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
                                                                <td>{server.total_quantity ?? 'N/A'}</td>
                                                                <td style={{ fontWeight: 600, color: 'var(--accent)' }}>
                                                                    {server.scorePercent}%
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>

                                            {/* Mobile List View */}
                                            <div className="mobile-modal-grid">
                                                {bestServers.map((server, i) => (
                                                    <div className="mobile-list-item" key={server.realm_id}>
                                                        {/* Header: Rank + Server + Score */}
                                                        <div className="mobile-list-header">
                                                            <div className="realm-info">
                                                                <span className="rank-emoji">
                                                                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}
                                                                </span>
                                                                {server.region && (
                                                                    <img
                                                                        src={getFlagUrl(server.region)}
                                                                        alt=""
                                                                        className="realm-flag"
                                                                    />
                                                                )}
                                                                <span className="realm-name">{server.realm_name}</span>
                                                            </div>
                                                            <span style={{ fontWeight: 600, color: 'var(--accent)' }}>
                                                                {server.scorePercent}%
                                                            </span>
                                                        </div>

                                                        {/* Details: Price, Qty, Pop */}
                                                        <div className="mobile-list-row">
                                                            <span>Prix: <PriceDisplay value={server.min_price} /></span>
                                                            <span className="text-muted">Pop: {server.populationLabel || transformPop(server.population)}</span>
                                                        </div>
                                                        <div className="mobile-list-row">
                                                            <span className="text-muted">Qté: {server.total_quantity ?? 'N/A'}</span>
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
                                <div className="tab-content">
                                    <h3>📊 Prix sur tous les serveurs</h3>
                                    <p className="text-muted" style={{ marginBottom: 'var(--spacing-sm)', fontSize: '0.75rem' }}>
                                        💡 Cliquez sur un en-tête de colonne pour trier
                                    </p>
                                    {sortedRealmPrices.length === 0 ? (
                                        <p className="text-muted">Aucune donnée de prix disponible pour ce pet.</p>
                                    ) : (
                                        <>
                                            {/* Desktop Table */}
                                            <div className="table-container" style={{ maxHeight: '500px' }}>
                                                <table className="table">
                                                    <thead>
                                                        <tr>
                                                            <th onClick={() => handleSort('realm_name')} style={{ cursor: 'pointer' }}>
                                                                Serveur{getSortIndicator('realm_name')}
                                                            </th>
                                                            <th onClick={() => handleSort('min_price')} style={{ cursor: 'pointer' }}>
                                                                Prix Min{getSortIndicator('min_price')}
                                                            </th>
                                                            <th onClick={() => handleSort('total_quantity')} style={{ cursor: 'pointer' }}>
                                                                Quantité{getSortIndicator('total_quantity')}
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
                                                                <td><PriceDisplay value={price.min_price} /></td>
                                                                <td>{price.total_quantity ?? 'N/A'}</td>
                                                                <td className="text-muted">{formatTimeDiff(price.recorded_at)}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>

                                            {/* Mobile List View */}
                                            <div className="mobile-modal-grid">
                                                {sortedRealmPrices.map((price) => (
                                                    <div className="mobile-list-item" key={price.realm_id}>
                                                        <div className="mobile-list-header">
                                                            <div className="realm-info">
                                                                {price.region && (
                                                                    <img
                                                                        src={getFlagUrl(price.region)}
                                                                        alt=""
                                                                        className="realm-flag"
                                                                    />
                                                                )}
                                                                <span className="realm-name">{price.realm_name}</span>
                                                            </div>
                                                            <PriceDisplay value={price.min_price} />
                                                        </div>
                                                        <div className="mobile-list-row">
                                                            <span className="text-muted">Qté: {price.total_quantity ?? 'N/A'}</span>
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
                                <div className="tab-content">
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
                                <div className="tab-content">
                                    <h3>📉 Statistiques</h3>
                                    <div className="stats-grid">
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
