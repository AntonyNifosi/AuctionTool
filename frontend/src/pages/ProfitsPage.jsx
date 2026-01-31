import { useState, useEffect } from 'react'
import { useRealm } from '../context/RealmContext'
import PriceDisplay from '../components/PriceDisplay'
import ItemDetailModal from '../components/ItemDetailModal'
import InfiniteScrollTrigger from '../components/InfiniteScrollTrigger'
import './ProfitsPage.css'

const PROFESSIONS = {
    164: 'Forge',
    165: 'Travail du cuir',
    171: 'Alchimie',
    197: 'Couture',
    202: 'Ingénierie',
    333: 'Enchantement',
    755: 'Joaillerie',
    773: 'Calligraphie',
}

function ProfitsPage() {
    const { selectedRealm } = useRealm()
    const [items, setItems] = useState([])
    const [expansions, setExpansions] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedItem, setSelectedItem] = useState(null)

    // Filters
    const [selectedProfessions, setSelectedProfessions] = useState([])
    const [selectedExpansions, setSelectedExpansions] = useState([])
    const [minProfitGold, setMinProfitGold] = useState(0)
    const [minVolume, setMinVolume] = useState(0)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const pageSize = 50

    // Sorting - default by score descending
    const [sortConfig, setSortConfig] = useState({ key: 'score', direction: 'desc' })

    // Fetch profits data
    useEffect(() => {
        if (!selectedRealm) return

        const controller = new AbortController()
        const signal = controller.signal

        const fetchProfits = async () => {
            setLoading(true)

            try {
                const params = new URLSearchParams({
                    realm_id: selectedRealm.id,
                    page: page.toString(),
                    page_size: pageSize.toString(),
                    min_profit: (minProfitGold * 10000).toString(),
                    min_volume: minVolume.toString(),
                    sort_by: sortConfig.key,
                    sort_order: sortConfig.direction
                })

                if (selectedProfessions.length > 0) {
                    params.append('professions', selectedProfessions.join(','))
                }
                if (selectedExpansions.length > 0) {
                    params.append('expansions', selectedExpansions.join(','))
                }

                const response = await fetch(`/api/profits?${params}`, { signal })
                if (response.ok) {
                    const data = await response.json()

                    setItems(prev => {
                        if (page === 1) return data.items || []
                        const existingIds = new Set(prev.map(i => i.item_id))
                        const newItems = (data.items || []).filter(i => !existingIds.has(i.item_id))
                        return [...prev, ...newItems]
                    })

                    setTotal(data.total || 0)
                    setTotalPages(Math.ceil((data.total || 0) / pageSize))
                }
            } catch (err) {
                if (err.name === 'AbortError') return
                console.error('Failed to fetch profits:', err)
            } finally {
                if (!signal.aborted) {
                    setLoading(false)
                }
            }
        }

        fetchProfits()

        return () => {
            controller.abort()
        }
    }, [selectedRealm, selectedProfessions, selectedExpansions, minProfitGold, minVolume, page, sortConfig])

    // Fetch expansions
    useEffect(() => {
        if (!selectedRealm) return

        const fetchExpansions = async () => {
            try {
                const response = await fetch(`/api/profits/expansions?realm_id=${selectedRealm.id}`)
                if (response.ok) {
                    const data = await response.json()
                    setExpansions(data.expansions || [])
                }
            } catch (err) {
                console.error('Failed to fetch expansions:', err)
            }
        }

        fetchExpansions()
    }, [selectedRealm])

    const getScoreBadgeClass = (score) => {
        if (!score) return 'score-low'
        if (score >= 70) return 'score-high'
        if (score >= 40) return 'score-medium'
        return 'score-low'
    }



    const toggleProfession = (id) => {
        setSelectedProfessions(prev =>
            prev.includes(id)
                ? prev.filter(p => p !== id)
                : [...prev, id]
        )
        setPage(1)
        setLoading(true)
        setItems([])
    }

    const toggleExpansion = (exp) => {
        setSelectedExpansions(prev =>
            prev.includes(exp)
                ? prev.filter(e => e !== exp)
                : [...prev, exp]
        )
        setPage(1)
        setLoading(true)
        setItems([])
    }

    const getProfitIndicator = (item) => {
        if (!item.profit) return { icon: '⚪', class: '' }
        if (item.profit > 0) return { icon: '🟢', class: 'profit-positive' }
        return { icon: '🔴', class: 'profit-negative' }
    }

    // Sorting logic
    const handleSort = (key) => {
        setSortConfig(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
        }))
        setPage(1)
        setLoading(true)
        setItems([])
    }

    const getSortIndicator = (key) => {
        if (sortConfig.key !== key) return ''
        return sortConfig.direction === 'asc' ? ' ▲' : ' ▼'
    }

    // Note: Sorting is now done server-side via API params

    if (!selectedRealm) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">🌍</div>
                <p>Veuillez sélectionner un serveur</p>
            </div>
        )
    }

    return (
        <div className="profits-page">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">💰</span>
                    Analyse des Profits de Craft
                </h1>
                <p className="page-subtitle">
                    Identifiez les items les plus rentables à crafter sur {selectedRealm.name}
                </p>
                <p className="page-subtitle">
                    💡 La prix de vente affiché est le <strong>prix minimum observé sur les 3 derniers jours</strong> • Cliquez sur un en-tête pour trier
                </p>
            </div>

            {/* Filters */}
            <div className="filter-bar">
                <div className="filter-group" style={{ flex: 2 }}>
                    <label className="filter-label">🔧 Métiers</label>
                    <div className="profession-chips">
                        {Object.entries(PROFESSIONS).map(([id, name]) => (
                            <button
                                key={id}
                                className={`chip ${selectedProfessions.includes(parseInt(id)) ? 'active' : ''}`}
                                onClick={() => toggleProfession(parseInt(id))}
                            >
                                {name}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <div className="filter-bar">
                <div className="filter-group" style={{ flex: 2 }}>
                    <label className="filter-label">📅 Extensions</label>
                    <div className="profession-chips">
                        {expansions.map((exp) => (
                            <button
                                key={exp}
                                className={`chip ${selectedExpansions.includes(exp) ? 'active' : ''}`}
                                onClick={() => toggleExpansion(exp)}
                            >
                                {exp}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="filter-group">
                    <label className="filter-label">💰 Profit min (or)</label>
                    <input
                        type="number"
                        className="input"
                        value={minProfitGold}
                        onChange={(e) => { setMinProfitGold(parseInt(e.target.value) || 0); setPage(1); setLoading(true); setItems([]); }}
                        min="0"
                        step="100"
                    />
                </div>

                <div className="filter-group">
                    <label className="filter-label">📦 Ventes min</label>
                    <input
                        type="number"
                        className="input"
                        value={minVolume}
                        onChange={(e) => { setMinVolume(parseInt(e.target.value) || 0); setPage(1); setLoading(true); setItems([]); }}
                        min="0"
                    />
                </div>
            </div>

            {/* Results Results */}
            <div className="results-info">
                <span className="results-count">💰 {total.toLocaleString()} items craftables</span>
                <span className="results-hint">💡 Cliquez sur une ligne pour voir les détails</span>
            </div>

            {/* Mobile Grid View */}
            <div className="mobile-grid">
                {items.map((item) => {
                    const indicator = getProfitIndicator(item)
                    return (
                        <div
                            key={item.item_id}
                            className="mobile-card vertical"
                            onClick={() => setSelectedItem(item)}
                        >
                            <div className="mobile-card-header">
                                {item.icon_url && item.icon_url !== 'NONE' ? (
                                    <img src={item.icon_url} alt="" className="mobile-card-icon" loading="lazy" />
                                ) : (
                                    <div className="mobile-card-icon" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🔨</div>
                                )}
                                <div className="mobile-card-title-row">
                                    <div className="mobile-card-title">{item.name}</div>
                                    <div className="mobile-card-subtitle">{item.profession_name} • {item.expansion}</div>
                                </div>
                                <span className={`score-badge ${getScoreBadgeClass(item.score)}`}>
                                    {item.score ? Math.round(item.score) : 0}%
                                </span>
                            </div>

                            <div className="mobile-card-body">
                                <div className="mobile-card-row">
                                    <span className="mobile-card-label">Coût</span>
                                    <PriceDisplay value={item.craft_cost} />
                                </div>
                                <div className="mobile-card-row">
                                    <span className="mobile-card-label">Vente</span>
                                    <PriceDisplay value={item.sell_price} />
                                </div>
                                <div className="mobile-card-row">
                                    <span className="mobile-card-label">Marge</span>
                                    <span className={item.profit_margin > 0 ? 'text-success' : item.profit_margin < 0 ? 'text-danger' : ''}>
                                        {item.profit_margin != null ? `${(item.profit_margin * 100).toFixed(1)}%` : 'N/A'}
                                    </span>
                                </div>
                                <div className="mobile-card-row">
                                    <span className="mobile-card-label">Profit</span>
                                    <span className={indicator.class} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                        {indicator.icon} <PriceDisplay value={item.profit} />
                                    </span>
                                </div>
                            </div>
                        </div>
                    )
                })}
                {/* Infinite Scroll Trigger Mobile */}
                {loading && page > 1 && (
                    <div className="loading-more">
                        <div className="spinner-inline"></div> Chargement...
                    </div>
                )}
                {page < totalPages && !loading && (
                    <InfiniteScrollTrigger onIntersect={() => setPage(prev => prev + 1)} />
                )}
            </div>

            {/* Table */}
            <div className="table-container">
                <table className="table">
                    <thead>
                        <tr>
                            <th style={{ width: 50 }}></th>
                            <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>
                                Nom{getSortIndicator('name')}
                            </th>
                            <th onClick={() => handleSort('profession_name')} style={{ cursor: 'pointer' }}>
                                Métier{getSortIndicator('profession_name')}
                            </th>

                            <th onClick={() => handleSort('expansion')} style={{ cursor: 'pointer' }}>
                                Extension{getSortIndicator('expansion')}
                            </th>
                            <th onClick={() => handleSort('craft_cost')} style={{ cursor: 'pointer' }}>
                                Coût Craft{getSortIndicator('craft_cost')}
                            </th>
                            <th onClick={() => handleSort('sell_price')} style={{ cursor: 'pointer' }}>
                                Prix Vente{getSortIndicator('sell_price')}
                            </th>
                            <th onClick={() => handleSort('profit')} style={{ cursor: 'pointer' }}>
                                Profit{getSortIndicator('profit')}
                            </th>
                            <th onClick={() => handleSort('profit_margin')} style={{ cursor: 'pointer' }}>
                                Marge{getSortIndicator('profit_margin')}
                            </th>
                            <th onClick={() => handleSort('volume')} style={{ cursor: 'pointer', textAlign: 'right' }}>
                                Ventes{getSortIndicator('volume')}
                            </th>
                            <th onClick={() => handleSort('cancels_3d')} style={{ cursor: 'pointer', textAlign: 'right' }}>
                                🔄 Cancels{getSortIndicator('cancels_3d')}
                            </th>
                            <th onClick={() => handleSort('score')} style={{ cursor: 'pointer', textAlign: 'center' }}>
                                Score{getSortIndicator('score')}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && page === 1 ? (
                            Array.from({ length: 10 }).map((_, i) => (
                                <tr key={i}>
                                    {Array.from({ length: 9 }).map((_, j) => (
                                        <td key={j}><div className="skeleton" style={{ width: j === 1 ? 200 : 80, height: 20 }} /></td>
                                    ))}
                                </tr>
                            ))
                        ) : items.length === 0 && !loading ? (
                            <tr>
                                <td colSpan="9" style={{ textAlign: 'center', padding: '2rem' }}>
                                    Aucun item craftable trouvé
                                </td>
                            </tr>
                        ) : (
                            items.map((item) => {
                                const indicator = getProfitIndicator(item)
                                return (
                                    <tr
                                        key={item.item_id}
                                        className="clickable-row"
                                        onClick={() => setSelectedItem(item)}
                                    >
                                        <td>
                                            {item.icon_url && item.icon_url !== 'NONE' ? (
                                                <img src={item.icon_url} alt="" className="item-icon" loading="lazy" />
                                            ) : (
                                                <div className="item-icon-placeholder">🔨</div>
                                            )}
                                        </td>
                                        <td>
                                            <div className="item-name">{item.name}</div>
                                        </td>
                                        <td>
                                            <span className="badge">{item.profession_name}</span>
                                        </td>

                                        <td>
                                            <span className="text-muted">{item.expansion || 'N/A'}</span>
                                        </td>
                                        <td>
                                            <PriceDisplay value={item.craft_cost} />
                                        </td>
                                        <td>
                                            <PriceDisplay value={item.sell_price} />
                                        </td>
                                        <td className={indicator.class}>
                                            {indicator.icon} <PriceDisplay value={item.profit} />
                                        </td>
                                        <td>
                                            <span className={item.profit_margin > 0 ? 'text-success' : item.profit_margin < 0 ? 'text-danger' : ''}>
                                                {item.profit_margin != null ? `${(item.profit_margin * 100).toFixed(1)}%` : 'N/A'}
                                            </span>
                                        </td>
                                        <td>{item.volume ?? 'N/A'}</td>
                                        <td style={{ color: (item.cancels_3d ?? 0) > 10 ? 'var(--warning)' : 'inherit' }}>
                                            {item.cancels_3d ?? 0}
                                        </td>
                                        <td style={{ textAlign: 'center' }}>
                                            <span className={`score-badge ${getScoreBadgeClass(item.score)}`}>
                                                {item.score ? `${Math.round(item.score)}%` : '0%'}
                                            </span>
                                        </td>
                                    </tr>
                                )
                            })
                        )}
                        {/* Loading more row */}
                        {loading && page > 1 && (
                            <tr>
                                <td colSpan="9" style={{ textAlign: 'center', padding: '1rem' }}>
                                    <div className="spinner-inline"></div> Chargement de la suite...
                                </td>
                            </tr>
                        )}
                        {/* Trigger for Desktop */}
                        {items.length > 0 && (
                            <tr style={{ height: '20px', border: 'none' }}>
                                <td colSpan="9" style={{ padding: 0, border: 'none' }}>
                                    <InfiniteScrollTrigger
                                        onIntersect={() => setPage(prev => prev + 1)}
                                        enabled={!loading && page < totalPages}
                                    />
                                </td>
                            </tr>
                        )}

                    </tbody>
                </table>
            </div>

            {/* Padding */}
            <div style={{ height: '20px' }}></div>

            {/* Item Detail Modal */}
            {selectedItem && (
                <ItemDetailModal
                    item={selectedItem}
                    realmId={selectedRealm.id}
                    onClose={() => setSelectedItem(null)}
                />
            )}
        </div>
    )
}

export default ProfitsPage
