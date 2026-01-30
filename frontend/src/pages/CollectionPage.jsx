import { useState, useEffect } from 'react'
import { useRealm } from '../context/RealmContext'
import PriceDisplay from '../components/PriceDisplay'
import PetDetailModal from '../components/PetDetailModal'
import './CollectionPage.css'

function CollectionPage() {
    const { realms, selectedRealm } = useRealm()
    const [characterName, setCharacterName] = useState('')
    const [selectedRealmSlug, setSelectedRealmSlug] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [collection, setCollection] = useState(null)
    const [selectedPet, setSelectedPet] = useState(null)

    // Pre-fill realm
    useEffect(() => {
        if (selectedRealm && !selectedRealmSlug) {
            // Convert 'Hyjal' -> 'hyjal'
            const slug = selectedRealm.name.toLowerCase().replace(/ /g, '-').replace(/'/g, '')
            setSelectedRealmSlug(slug)
        }
    }, [selectedRealm, realms])

    const handleSearch = async (e) => {
        e.preventDefault()

        if (!characterName.trim() || !selectedRealmSlug) {
            setError("Veuillez remplir tous les champs")
            return
        }

        setLoading(true)
        setError(null)
        setCollection(null)

        try {
            const params = new URLSearchParams({
                realm_slug: selectedRealmSlug,
                character_name: characterName.trim()
            })

            // Add realm_id if available to get prices for this specific realm
            if (selectedRealmSlug) {
                // Find realm ID from slug
                const targetRealm = realms.find(r =>
                    r.name.toLowerCase().replace(/ /g, '-').replace(/'/g, '') === selectedRealmSlug
                )
                if (targetRealm) {
                    params.append('realm_id', targetRealm.id)
                }
            }

            const response = await fetch(`/api/collection/pets?${params}`)

            if (!response.ok) {
                const data = await response.json()
                throw new Error(data.detail || "Erreur lors de la récupération de la collection")
            }

            const data = await response.json()
            setCollection(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
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

    // Convert realm name to slug
    const getRealmSlug = (name) => {
        return name.toLowerCase().replace(/ /g, '-').replace(/'/g, '')
    }

    return (
        <div className="collection-page">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">👤</span>
                    Ma Collection de Pets
                </h1>
                <p className="page-subtitle">
                    Consultez votre collection de pets Battle.net et estimez sa valeur
                </p>
                <p className="page-subtitle">
                    💡 Cliquez sur un pet pour voir les détails
                </p>
            </div>

            {/* Search Form */}
            <form className="collection-form" onSubmit={handleSearch}>
                <div className="form-row">
                    <div className="form-group">
                        <label className="filter-label">🌍 Serveur</label>
                        <select
                            className="select"
                            value={selectedRealmSlug}
                            onChange={(e) => setSelectedRealmSlug(e.target.value)}
                            required
                        >
                            <option value="">Choisir un serveur</option>
                            {realms.map((realm) => (
                                <option key={realm.id} value={getRealmSlug(realm.name)}>
                                    {realm.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label className="filter-label">👤 Nom du personnage</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="Ex: Jaina"
                            value={characterName}
                            onChange={(e) => setCharacterName(e.target.value)}
                            required
                        />
                    </div>

                    <div className="form-group form-action">
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading}
                        >
                            {loading ? '⏳ Chargement...' : '🔍 Rechercher'}
                        </button>
                    </div>
                </div>
            </form>

            {/* Error Message */}
            {error && (
                <div className="error-message">
                    <span className="error-icon">❌</span>
                    <span>{error}</span>
                    <p className="error-hint">
                        💡 Assurez-vous que le nom est correct et que le profil n'est pas privé dans les options Battle.net
                    </p>
                </div>
            )}

            {/* Loading State */}
            {loading && (
                <div className="loading-state" style={{ textAlign: 'center', padding: '40px' }}>
                    <div className="spinner" style={{ margin: '0 auto 20px', width: 40, height: 40, border: '4px solid rgba(255,255,255,0.1)', borderLeftColor: '#ffd100', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 500 }}>🔍 Récupération des données Battle.net...</div>
                    <p className="text-muted" style={{ marginTop: 10 }}>Cela peut prendre quelques secondes selon la taille de votre collection.</p>
                </div>
            )}

            {/* Collection Results */}
            {collection && (
                <>
                    {/* Stats */}
                    <div className="collection-stats">
                        <div className="stat-card">
                            <div className="stat-icon">📊</div>
                            <div className="stat-value">{collection.total_pets}</div>
                            <div className="stat-label">Total pets</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-icon">💰</div>
                            <div className="stat-value">{collection.tradable_count}</div>
                            <div className="stat-label">Échangeables</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-icon">🏆</div>
                            <div className="stat-value">
                                <PriceDisplay value={collection.total_value} />
                            </div>
                            <div className="stat-label">Valeur totale</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-icon">
                                <img
                                    src="https://wow.zamimg.com/images/wow/icons/large/inv_misc_coin_02.jpg"
                                    alt="Or"
                                    style={{ width: 32, height: 32, verticalAlign: 'middle', borderRadius: '50%' }}
                                />
                            </div>
                            <div className="stat-value">
                                {Math.floor(collection.total_value / 10000).toLocaleString()}
                                <img
                                    src="https://wow.zamimg.com/images/icons/money-gold.gif"
                                    alt="g"
                                    style={{ width: 16, height: 16, verticalAlign: 'middle', marginLeft: 4, transform: 'translateY(-2px)' }}
                                />
                            </div>
                            <div className="stat-label">En or</div>
                        </div>
                    </div>

                    {/* Mobile Grid View (Visible only on mobile) */}
                    <div className="mobile-grid">
                        {collection.pets.map((pet, index) => (
                            <div
                                className="mobile-card vertical"
                                key={`card-${pet.pet_id}-${index}`}
                                onClick={() => setSelectedPet(pet)}
                            >
                                <div className="mobile-card-header">
                                    <div className="mobile-card-icon-wrapper">
                                        {pet.icon_url ? (
                                            <img src={pet.icon_url} alt="" className="mobile-card-icon" loading="lazy" />
                                        ) : (
                                            <div className="mobile-card-icon placeholder">🐾</div>
                                        )}
                                    </div>
                                    <div className="mobile-card-title-row">
                                        <div className="mobile-card-name" style={{ color: getQualityColor(pet.quality) }}>
                                            {pet.name}
                                        </div>
                                        {pet.is_tradable && <span title="Échangeable">✅</span>}
                                    </div>
                                </div>


                                <div className="mobile-card-body">
                                    <div className="mobile-card-row">
                                        <div className="mobile-card-meta">
                                            <span>Niv. {pet.level}</span>
                                            <span>•</span>
                                            <span style={{ color: getQualityColor(pet.quality) }}>{pet.quality}</span>
                                        </div>
                                    </div>

                                    <div className="mobile-card-row">
                                        <span className="mobile-card-label">Source</span>
                                        <span className="text-muted" style={{ fontSize: '0.85rem' }}>{pet.source || 'Inconnue'}</span>
                                    </div>

                                    <div className="mobile-card-row">
                                        <span className="mobile-card-label">Prix</span>
                                        <PriceDisplay value={pet.min_price} />
                                    </div>

                                    <div className="mobile-card-row">
                                        <span className="mobile-card-label">Ventes (3j)</span>
                                        <span>{pet.sales_3d ?? 0}</span>
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
                    </div>

                    {/* Desktop Table View (Hidden on mobile) */}
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th style={{ width: 50 }}></th>
                                    <th>Nom</th>
                                    <th>Niveau</th>
                                    <th>Source</th>
                                    <th>Qualité</th>
                                    <th>Type</th>
                                    <th>Prix</th>
                                    <th>Ventes (3j)</th>
                                    <th>Échangeable</th>
                                    <th style={{ width: 50 }}>Lien</th>
                                </tr>
                            </thead>
                            <tbody>
                                {collection.pets.map((pet, index) => (
                                    <tr
                                        key={`${pet.pet_id}-${index}`}
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
                                        <td>{pet.level}</td>
                                        <td className="text-muted" style={{ fontSize: '0.85rem', maxWidth: '150px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={pet.source}>
                                            {pet.source || '-'}
                                        </td>
                                        <td>
                                            <span style={{ color: getQualityColor(pet.quality) }}>
                                                {pet.quality}
                                            </span>
                                        </td>
                                        <td>{pet.creature_type}</td>
                                        <td>
                                            <PriceDisplay value={pet.min_price} />
                                        </td>
                                        <td>{pet.sales_3d ?? 0}</td>
                                        <td>{pet.is_tradable ? '✅' : '❌'}</td>
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
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            {/* Pet Detail Modal */}
            {selectedPet && (
                <PetDetailModal
                    pet={selectedPet}
                    realmId={realms.find(r => getRealmSlug(r.name) === selectedRealmSlug)?.id || selectedRealm?.id}
                    onClose={() => setSelectedPet(null)}
                />
            )}
        </div>
    )
}

export default CollectionPage
