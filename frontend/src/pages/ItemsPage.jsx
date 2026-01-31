import { useState } from 'react'
import { useRealm } from '../context/RealmContext'
import { useItems } from '../hooks/useItems'
import PriceDisplay from '../components/PriceDisplay'
import TrendBadge from '../components/TrendBadge'
import ItemDetailModal from '../components/ItemDetailModal'
import InfiniteScrollTrigger from '../components/InfiniteScrollTrigger'
import { formatTimeDiff, formatVolumeChange } from '../utils/formatters'
import './ItemsPage.css'

function ItemsPage() {
    const { selectedRealm } = useRealm()
    const [selectedItem, setSelectedItem] = useState(null)

    const {
        items, loading, error, categories,
        total, totalPages,
        search, setSearch,
        category, setCategory,
        sortBy, setSortBy,
        sortOrder, setSortOrder,
        page, setPage,
        handleSort, getSortIcon
    } = useItems(selectedRealm)

    // Helper for quality colors
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
                        onChange={(e) => setCategory(e.target.value)}
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
                {/* Show initial loading skeletons only on first page */}
                {loading && page === 1 ? (
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
                ) : items.length === 0 && !loading ? (
                    <div className="empty-state">
                        <p>Aucun item trouvé</p>
                    </div>
                ) : (
                    <>
                        {items.map((item) => (
                            <div
                                key={`card-${item.item_id}`}
                                className="mobile-card horizontal"
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
                                        <span>Ventes: {item.sales_3d ?? 0}</span>
                                        <span style={{ color: (item.cancels_3d ?? 0) > 10 ? 'var(--warning)' : 'inherit' }}>🔄 {item.cancels_3d ?? 0}</span>
                                    </div>

                                    <div className="mobile-card-footer">
                                        <PriceDisplay value={item.min_price} />
                                        {item.profession_name && (
                                            <span className="text-muted" style={{ fontSize: '0.7rem' }}>Item {item.profession_name}</span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                        {/* Loading indicator for infinite scroll on mobile */}
                        {loading && page > 1 && (
                            <div className="loading-more">
                                <div className="spinner-inline"></div> Chargement...
                            </div>
                        )}
                        {/* Infinite Scroll Trigger */}
                        <InfiniteScrollTrigger
                            onIntersect={() => setPage(prev => prev + 1)}
                            enabled={!loading && page < totalPages}
                        />
                    </>
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
                            <th>Métier</th>
                            <th
                                className="sortable"
                                onClick={() => handleSort('sales_3d')}
                            >
                                Ventes{getSortIcon('sales_3d')}
                            </th>
                            <th
                                className="sortable"
                                onClick={() => handleSort('cancels_3d')}
                            >
                                🔄 Cancels{getSortIcon('cancels_3d')}
                            </th>
                            <th
                                className="sortable"
                                onClick={() => handleSort('trend')}
                            >
                                Tendance{getSortIcon('trend')}
                            </th>
                            <th>Maj</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && page === 1 ? (
                            // Loading skeletons
                            Array.from({ length: 10 }).map((_, i) => (
                                <tr key={i}>
                                    <td><div className="skeleton" style={{ width: 40, height: 40 }} /></td>
                                    <td><div className="skeleton" style={{ width: 200, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 100, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 80, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 70, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 50, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 70, height: 20 }} /></td>
                                    <td><div className="skeleton" style={{ width: 50, height: 20 }} /></td>
                                </tr>
                            ))
                        ) : items.length === 0 && !loading ? (
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
                                    <td>
                                        <span className="text-muted">{item.profession_name || '-'}</span>
                                    </td>
                                    <td>{item.sales_3d ?? 0}</td>
                                    <td style={{ color: (item.cancels_3d ?? 0) > 10 ? 'var(--warning)' : 'inherit' }}>{item.cancels_3d ?? 0}</td>
                                    <td>
                                        <TrendBadge value={item.trend} />
                                    </td>
                                    <td>
                                        <span className="text-muted">{formatTimeDiff(item.recorded_at)}</span>
                                    </td>
                                </tr>
                            ))
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

            {/* Padding at bottom to avoid content being hidden behind triggers or edges */}
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

export default ItemsPage
