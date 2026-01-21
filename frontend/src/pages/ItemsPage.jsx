import { useState, useEffect, useCallback } from 'react'
import { useRealm } from '../context/RealmContext'
import PriceDisplay from '../components/PriceDisplay'
import TrendBadge from '../components/TrendBadge'
import ItemDetailModal from '../components/ItemDetailModal'
import { formatTimeDiff, formatVolumeChange, debounce } from '../utils/formatters'
import './ItemsPage.css'

function ItemsPage() {
    const { selectedRealm } = useRealm()
    const [items, setItems] = useState([])
    const [categories, setCategories] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [selectedItem, setSelectedItem] = useState(null)

    // Filters & Pagination
    const [search, setSearch] = useState('')
    const [debouncedSearch, setDebouncedSearch] = useState('')
    const [category, setCategory] = useState('')
    const [sortBy, setSortBy] = useState('min_price')
    const [sortOrder, setSortOrder] = useState('desc')
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const pageSize = 50

    // Debounce search input
    const debouncedSetSearch = useCallback(
        debounce((value) => {
            setDebouncedSearch(value)
            setPage(1)
        }, 300),
        []
    )

    useEffect(() => {
        debouncedSetSearch(search)
    }, [search, debouncedSetSearch])

    // Fetch items
    useEffect(() => {
        if (!selectedRealm) return

        const fetchItems = async () => {
            setLoading(true)
            setError(null)

            try {
                const params = new URLSearchParams({
                    realm_id: selectedRealm.id,
                    page: page.toString(),
                    page_size: pageSize.toString(),
                    sort_by: sortBy,
                    sort_order: sortOrder
                })

                if (debouncedSearch) params.append('search', debouncedSearch)
                if (category) params.append('category', category)

                const response = await fetch(`/api/items?${params}`)
                if (!response.ok) throw new Error('Failed to fetch items')

                const data = await response.json()
                setItems(data.items || [])
                setTotal(data.total || 0)
                setTotalPages(Math.ceil((data.total || 0) / pageSize))
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }

        fetchItems()
    }, [selectedRealm, debouncedSearch, category, sortBy, sortOrder, page])

    // Fetch categories
    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const response = await fetch('/api/items/categories')
                if (response.ok) {
                    const data = await response.json()
                    setCategories(data.categories || [])
                }
            } catch (err) {
                console.error('Failed to fetch categories:', err)
            }
        }
        fetchCategories()
    }, [])

    // Helper for quality colors (reused from CollectionPage)
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

    // Handle sort column click
    const handleSort = (column) => {
        if (sortBy === column) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
        } else {
            setSortBy(column)
            setSortOrder(column === 'min_price' || column === 'trend' ? 'desc' : 'asc')
        }
        setPage(1)
    }

    const getSortIcon = (column) => {
        if (sortBy !== column) return ' ⇅'
        return sortOrder === 'asc' ? ' ↑' : ' ↓'
    }

    if (!selectedRealm) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">🌍</div>
                <p>Veuillez sélectionner un serveur</p>
            </div>
        )
    }

    return (
        <div className="items-page">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">🏠</span>
                    Items Housing
                </h1>
                <p className="page-subtitle">
                    💡 Le prix affiché est le <strong>prix minimum observé sur les 3 derniers jours</strong>
                </p>
            </div>

            {/* Filters */}
            <div className="filter-bar">
                <div className="filter-group" style={{ flex: 2 }}>
                    <label className="filter-label">🔍 Rechercher</label>
                    <div className="input-group">
                        <span className="input-icon">🔍</span>
                        <input
                            type="text"
                            className="input input-with-icon"
                            placeholder="Nom de l'item..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                </div>

                <div className="filter-group">
                    <label className="filter-label">📁 Catégorie</label>
                    <select
                        className="select"
                        value={category}
                        onChange={(e) => { setCategory(e.target.value); setPage(1); }}
                    >
                        <option value="">Toutes</option>
                        {categories.map((cat) => (
                            <option key={cat} value={cat}>{cat}</option>
                        ))}
                    </select>
                </div>

                <div className="filter-group">
                    <label className="filter-label">📊 Trier par</label>
                    <select
                        className="select"
                        value={`${sortBy}-${sortOrder}`}
                        onChange={(e) => {
                            const [field, order] = e.target.value.split('-')
                            setSortBy(field)
                            setSortOrder(order)
                            setPage(1)
                        }}
                    >
                        <option value="name-asc">Nom (A-Z)</option>
                        <option value="name-desc">Nom (Z-A)</option>
                        <option value="min_price-asc">Prix (croissant)</option>
                        <option value="min_price-desc">Prix (décroissant)</option>
                        <option value="trend-desc">Tendance (hausse)</option>
                        <option value="trend-asc">Tendance (baisse)</option>
                    </select>
                </div>
            </div>

            {/* Results count */}
            <div className="results-info">
                <span className="results-count">📦 {total.toLocaleString()} items</span>
                <span className="results-server">sur {selectedRealm.name}</span>
                <span className="results-hint">💡 Cliquez sur une ligne pour voir les détails</span>
            </div>

            {/* Error state */}
            {error && (
                <div className="error-banner">
                    ⚠️ {error}
                </div>
            )}

            {/* Mobile Grid View (Visible only on mobile) */}
            <div className="mobile-grid">
                {loading ? (
                    // Loading skeletons for grid (3 items)
                    Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="mobile-card">
                            <div className="skeleton" style={{ width: 48, height: 48, borderRadius: 6 }} />
                            <div className="mobile-card-content">
                                <div className="skeleton" style={{ width: '60%', height: 20, marginBottom: 8 }} />
                                <div className="skeleton" style={{ width: '40%', height: 16 }} />
                            </div>
                        </div>
                    ))
                ) : items.length === 0 ? (
                    <div className="empty-state">
                        <p>Aucun item trouvé</p>
                    </div>
                ) : (
                    items.map((item) => (
                        <div
                            key={`card-${item.item_id}`}
                            className="mobile-card"
                            onClick={() => setSelectedItem(item)}
                        >
                            <div className="mobile-card-icon-wrapper">
                                {item.icon_url && item.icon_url !== 'NONE' ? (
                                    <img src={item.icon_url} alt="" className="mobile-card-icon" loading="lazy" />
                                ) : (
                                    <div className="mobile-card-icon placeholder" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-tertiary)' }}>📦</div>
                                )}
                            </div>
                            <div className="mobile-card-content">
                                <div className="mobile-card-header">
                                    <div className="mobile-card-name" style={{ color: item.quality ? getQualityColor(item.quality) : 'inherit' }}>
                                        {item.name}
                                    </div>
                                    <div className="mobile-card-trend">
                                        <TrendBadge value={item.trend} />
                                    </div>
                                </div>

                                <div className="mobile-card-meta">
                                    <span className="badge">{item.category}</span>
                                    <span>Qté: {item.total_quantity}</span>
                                    {item.volume_change !== 0 && (
                                        <span className={item.volume_change > 0 ? 'text-success' : 'text-danger'} style={{ fontSize: '0.75rem' }}>
                                            ({formatVolumeChange(item.volume_change)})
                                        </span>
                                    )}
                                </div>

                                <div className="mobile-card-footer">
                                    <PriceDisplay value={item.min_price} />
                                    {item.profession_name && (
                                        <span className="text-muted" style={{ fontSize: '0.7rem' }}>Item {item.profession_name}</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Table */}
            <div className="table-container">
                <table className="table">
                    <thead>
                        <tr>
                            <th style={{ width: 50 }}></th>
                            <th
                                className="sortable"
                                onClick={() => handleSort('name')}
                            >
                                Nom{getSortIcon('name')}
                            </th>
                            <th>Catégorie</th>
                            <th
                                className="sortable"
                                onClick={() => handleSort('min_price')}
                            >
                                Prix Min{getSortIcon('min_price')}
                            </th>
                            <th
                                className="sortable"
                                onClick={() => handleSort('total_quantity')}
                            >
                                Quantité{getSortIcon('total_quantity')}
                            </th>
                            <th
                                className="sortable"
                                onClick={() => handleSort('trend')}
                            >
                                Tendance{getSortIcon('trend')}
                            </th>
                            <th>Vol. Δ</th>
                            <th>Métier</th>
                            <th>Maj</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            // Loading skeletons
                            Array.from({ length: 10 }).map((_, i) => (
                                <tr key={i}>
                                    <td><div className="skeleton" style={{ width: 40, height: 40 }} /></td>
                                    <td><div className="skeleton" style={{ width: 200, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 100, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 80, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 50, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 70, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 50, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 70, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 50, height: 20 }} /></td>
                                </tr>
                            ))
                        ) : items.length === 0 ? (
                            <tr>
                                <td colSpan="9" style={{ textAlign: 'center', padding: '2rem' }}>
                                    Aucun item trouvé
                                </td>
                            </tr>
                        ) : (
                            items.map((item) => (
                                <tr
                                    key={item.item_id}
                                    className="clickable-row"
                                    onClick={() => setSelectedItem(item)}
                                >
                                    <td>
                                        {item.icon_url && item.icon_url !== 'NONE' ? (
                                            <img
                                                src={item.icon_url}
                                                alt=""
                                                className="item-icon"
                                                loading="lazy"
                                            />
                                        ) : (
                                            <div className="item-icon-placeholder">📦</div>
                                        )}
                                    </td>
                                    <td>
                                        <div className="item-name">{item.name}</div>
                                    </td>
                                    <td>
                                        <span className="badge">{item.category || 'N/A'}</span>
                                    </td>
                                    <td>
                                        <PriceDisplay value={item.min_price} />
                                    </td>
                                    <td>{item.total_quantity ?? 'N/A'}</td>
                                    <td>
                                        <TrendBadge value={item.trend} />
                                    </td>
                                    <td>
                                        <span className={item.volume_change > 0 ? 'text-success' : item.volume_change < 0 ? 'text-danger' : ''}>
                                            {formatVolumeChange(item.volume_change)}
                                        </span>
                                    </td>
                                    <td>
                                        <span className="text-muted">{item.profession_name || '-'}</span>
                                    </td>
                                    <td>
                                        <span className="text-muted">{formatTimeDiff(item.recorded_at)}</span>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="pagination">
                    <button
                        className="pagination-btn"
                        onClick={() => setPage(1)}
                        disabled={page === 1}
                    >
                        ««
                    </button>
                    <button
                        className="pagination-btn"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                    >
                        «
                    </button>

                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum
                        if (totalPages <= 5) {
                            pageNum = i + 1
                        } else if (page <= 3) {
                            pageNum = i + 1
                        } else if (page >= totalPages - 2) {
                            pageNum = totalPages - 4 + i
                        } else {
                            pageNum = page - 2 + i
                        }

                        return (
                            <button
                                key={pageNum}
                                className={`pagination-btn ${page === pageNum ? 'active' : ''}`}
                                onClick={() => setPage(pageNum)}
                            >
                                {pageNum}
                            </button>
                        )
                    })}

                    <button
                        className="pagination-btn"
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                    >
                        »
                    </button>
                    <button
                        className="pagination-btn"
                        onClick={() => setPage(totalPages)}
                        disabled={page === totalPages}
                    >
                        »»
                    </button>
                </div>
            )}

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

export default ItemsPage
