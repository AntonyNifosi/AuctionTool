import { useState, useEffect } from 'react'
import { useRealm } from '../context/RealmContext'
import PriceDisplay from '../components/PriceDisplay'
import PetDetailModal from '../components/PetDetailModal'
import InfiniteScrollTrigger from '../components/InfiniteScrollTrigger'
import './PetsPage.css'

function PetsPage() {
    const { selectedRealm } = useRealm()
    const [pets, setPets] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedPet, setSelectedPet] = useState(null)

    // Filters
    const [search, setSearch] = useState('')
    const [tradableOnly, setTradableOnly] = useState(false)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const pageSize = 50

    // Sorting - default by price descending (highest first)
    const [sortConfig, setSortConfig] = useState({ key: 'min_price', direction: 'desc' })

    useEffect(() => {
        if (!selectedRealm) return

        const fetchPets = async () => {
            setLoading(true)

            try {
                const params = new URLSearchParams({
                    realm_id: selectedRealm.id,
                    page: page.toString(),
                    page_size: pageSize.toString(),
                    tradable_only: tradableOnly.toString(),
                    sort_by: sortConfig.key,
                    sort_order: sortConfig.direction
                })

                if (search) params.append('search', search)

                const response = await fetch(`/api/pets?${params}`)
                if (response.ok) {
                    const data = await response.json()

                    setPets(prev => {
                        if (page === 1) return data.pets || []
                        const existingIds = new Set(prev.map(p => p.pet_id))
                        const newPets = (data.pets || []).filter(p => !existingIds.has(p.pet_id))
                        return [...prev, ...newPets]
                    })

                    setTotal(data.total || 0)
                    setTotalPages(Math.ceil((data.total || 0) / pageSize))
                }
            } catch (err) {
                console.error('Failed to fetch pets:', err)
            } finally {
                setLoading(false)
            }
        }

        fetchPets()
    }, [selectedRealm, search, tradableOnly, page, sortConfig])

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

    // Sorting logic
    const handleSort = (key) => {
        setSortConfig(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
        }))
        setPage(1)
        setLoading(true)
        setPets([])
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
        <div className="pets-page">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">🐾</span>
                    Battle Pets
                </h1>
                <p className="page-subtitle">
                    Prix des familiers par serveur
                </p>
                <p className="page-subtitle">
                    💡 Cliquez sur un pet pour voir les détails • Cliquez sur un en-tête pour trier
                </p>
            </div>

            {/* Filters */}
            <div className="filter-bar">
                <div className="filter-group" style={{ flex: 2 }}>
                    <label className="filter-label">🔍 Rechercher</label>
                    <input
                        type="text"
                        className="input"
                        placeholder="Nom du pet..."
                        value={search}
                        onChange={(e) => { setSearch(e.target.value); setPage(1); setLoading(true); setPets([]); }}
                    />
                </div>

                <div className="filter-group">
                    <label className="filter-label">💱 Options</label>
                    <label className="checkbox-label" style={{ display: 'flex', alignItems: 'center', gap: '8px', height: '42px', cursor: 'pointer' }}>
                        <input
                            type="checkbox"
                            checked={tradableOnly}
                            onChange={(e) => { setTradableOnly(e.target.checked); setPage(1); setLoading(true); setPets([]); }}
                        />
                        <span>Échangeables uniquement</span>
                    </label>
                </div>
            </div>

            {/* Results */}
            <div className="results-info">
                <span className="results-count">🐾 {total.toLocaleString()} pets</span>
                <span className="results-hint" style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                    💡 Cliquez sur une ligne pour voir les détails
                </span>
            </div>

            {/* Mobile Grid View */}
            <div className="mobile-grid">
                {pets.map((pet) => (
                    <div
                        key={pet.pet_id}
                        className="mobile-card vertical"
                        onClick={() => setSelectedPet(pet)}
                    >
                        <div className="mobile-card-header">
                            {pet.icon_url ? (
                                <img src={pet.icon_url} alt="" className="mobile-card-icon" loading="lazy" />
                            ) : (
                                <div className="mobile-card-icon" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🐾</div>
                            )}
                            <div className="mobile-card-title-row">
                                <div className="mobile-card-title" style={{ color: getQualityColor(pet.quality) }}>
                                    {pet.name}
                                </div>
                                <div className="mobile-card-subtitle">{pet.creature_type || 'N/A'} • Niv {pet.level || '-'}</div>
                            </div>
                        </div>

                        <div className="mobile-card-body">
                            <div className="mobile-card-row">
                                <span className="mobile-card-label">Prix (min)</span>
                                <PriceDisplay value={pet.min_price} />
                            </div>
                            <div className="mobile-card-row">
                                <span className="mobile-card-label">Échangeable</span>
                                <span>{pet.is_tradable ? '✅' : '❌'}</span>
                            </div>
                            <div className="mobile-card-row">
                                <span className="mobile-card-label">Lien</span>
                                <a
                                    href={`https://fr.wowhead.com/battle-pet/${pet.pet_id}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    title="Voir sur Wowhead"
                                    className="wowhead-link"
                                    style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        width: 24,
                                        height: 24,
                                        background: '#2b323d',
                                        borderRadius: 4,
                                        textDecoration: 'none',
                                        fontSize: 12,
                                        fontWeight: 'bold',
                                        color: '#f9b617'
                                    }}
                                >
                                    W
                                </a>
                            </div>
                        </div>
                    </div>
                ))}
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
                            <th onClick={() => handleSort('level')} style={{ cursor: 'pointer' }}>
                                Niveau{getSortIndicator('level')}
                            </th>
                            <th>Type</th>
                            <th onClick={() => handleSort('min_price')} style={{ cursor: 'pointer' }}>
                                Prix (min){getSortIndicator('min_price')}
                            </th>
                            <th>Échangeable</th>
                            <th style={{ width: 50 }}>Lien</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && page === 1 ? (
                            Array.from({ length: 10 }).map((_, i) => (
                                <tr key={i}>
                                    {Array.from({ length: 7 }).map((_, j) => (
                                        <td key={j}><div className="skeleton" style={{ width: j === 1 ? 200 : 80, height: 20 }} /></td>
                                    ))}
                                </tr>
                            ))
                        ) : pets.length === 0 && !loading ? (
                            <tr>
                                <td colSpan="7" style={{ textAlign: 'center', padding: '2rem' }}>
                                    Aucun pet trouvé
                                </td>
                            </tr>
                        ) : (
                            pets.map((pet) => (
                                <tr
                                    key={pet.pet_id}
                                    className="clickable-row"
                                    onClick={() => setSelectedPet(pet)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <td>
                                        {pet.icon_url ? (
                                            <img src={pet.icon_url} alt="" className="item-icon" loading="lazy" />
                                        ) : (
                                            <div className="item-icon-placeholder">🐾</div>
                                        )}
                                    </td>
                                    <td>
                                        <div className="item-name" style={{ color: getQualityColor(pet.quality) }}>
                                            {pet.name}
                                        </div>
                                    </td>
                                    <td>{pet.level || '-'}</td>
                                    <td>{pet.creature_type || 'N/A'}</td>
                                    <td>
                                        <PriceDisplay value={pet.min_price} />
                                    </td>
                                    <td>
                                        {pet.is_tradable ? '✅' : '❌'}
                                    </td>
                                    <td>
                                        <a
                                            href={`https://fr.wowhead.com/battle-pet/${pet.pet_id}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            onClick={(e) => e.stopPropagation()}
                                            title="Voir sur Wowhead"
                                            className="wowhead-link"
                                            style={{
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                width: 24,
                                                height: 24,
                                                background: '#2b323d',
                                                borderRadius: 4,
                                                textDecoration: 'none',
                                                fontSize: 12,
                                                fontWeight: 'bold',
                                                color: '#f9b617'
                                            }}
                                        >
                                            W
                                        </a>
                                    </td>
                                </tr>
                            ))
                        )}
                        {/* Loading more row */}
                        {loading && page > 1 && (
                            <tr>
                                <td colSpan="7" style={{ textAlign: 'center', padding: '1rem' }}>
                                    <div className="spinner-inline"></div> Chargement de la suite...
                                </td>
                            </tr>
                        )}
                        {/* Trigger for Desktop */}
                        {pets.length > 0 && (
                            <tr style={{ height: '20px', border: 'none' }}>
                                <td colSpan="7" style={{ padding: 0, border: 'none' }}>
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

            {/* Pet Detail Modal */}
            {
                selectedPet && (
                    <PetDetailModal
                        pet={selectedPet}
                        realmId={selectedRealm.id}
                        onClose={() => setSelectedPet(null)}
                    />
                )
            }
        </div >
    )
}

export default PetsPage
