import { useState, useEffect } from 'react'
import { useRealm } from '../context/RealmContext'
import PriceDisplay from '../components/PriceDisplay'

function PetsPage() {
    const { selectedRealm } = useRealm()
    const [pets, setPets] = useState([])
    const [loading, setLoading] = useState(true)

    // Filters
    const [search, setSearch] = useState('')
    const [tradableOnly, setTradableOnly] = useState(false)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const pageSize = 50

    useEffect(() => {
        if (!selectedRealm) return

        const fetchPets = async () => {
            setLoading(true)

            try {
                const params = new URLSearchParams({
                    realm_id: selectedRealm.id,
                    page: page.toString(),
                    page_size: pageSize.toString(),
                    tradable_only: tradableOnly.toString()
                })

                if (search) params.append('search', search)

                const response = await fetch(`/api/pets?${params}`)
                if (response.ok) {
                    const data = await response.json()
                    setPets(data.pets || [])
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
    }, [selectedRealm, search, tradableOnly, page])

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
                        onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                    />
                </div>

                <div className="filter-group">
                    <label className="filter-label">💱 Options</label>
                    <label className="checkbox-label">
                        <input
                            type="checkbox"
                            checked={tradableOnly}
                            onChange={(e) => { setTradableOnly(e.target.checked); setPage(1); }}
                        />
                        <span>Échangeables uniquement</span>
                    </label>
                </div>
            </div>

            {/* Results */}
            <div className="results-info">
                <span className="results-count">🐾 {total.toLocaleString()} pets</span>
            </div>

            {/* Table */}
            <div className="table-container">
                <table className="table">
                    <thead>
                        <tr>
                            <th style={{ width: 50 }}></th>
                            <th>Nom</th>
                            <th>Niveau</th>
                            <th>Qualité</th>
                            <th>Type</th>
                            <th>Prix (min)</th>
                            <th>Échangeable</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            Array.from({ length: 10 }).map((_, i) => (
                                <tr key={i}>
                                    {Array.from({ length: 7 }).map((_, j) => (
                                        <td key={j}><div className="skeleton" style={{ width: j === 1 ? 200 : 80, height: 20 }} /></td>
                                    ))}
                                </tr>
                            ))
                        ) : pets.length === 0 ? (
                            <tr>
                                <td colSpan="7" style={{ textAlign: 'center', padding: '2rem' }}>
                                    Aucun pet trouvé
                                </td>
                            </tr>
                        ) : (
                            pets.map((pet) => (
                                <tr key={pet.pet_id}>
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
                                    <td>
                                        <span style={{ color: getQualityColor(pet.quality) }}>
                                            {pet.quality || 'N/A'}
                                        </span>
                                    </td>
                                    <td>{pet.creature_type || 'N/A'}</td>
                                    <td>
                                        <PriceDisplay value={pet.min_price} />
                                    </td>
                                    <td>
                                        {pet.is_tradable ? '✅' : '❌'}
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
                    <button className="pagination-btn" onClick={() => setPage(1)} disabled={page === 1}>««</button>
                    <button className="pagination-btn" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>«</button>
                    <span style={{ padding: '0 1rem', color: 'var(--text-muted)' }}>Page {page} / {totalPages}</span>
                    <button className="pagination-btn" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>»</button>
                    <button className="pagination-btn" onClick={() => setPage(totalPages)} disabled={page === totalPages}>»»</button>
                </div>
            )}
        </div>
    )
}

export default PetsPage
