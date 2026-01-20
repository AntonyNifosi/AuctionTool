import { useState } from 'react'
import { useRealm } from '../context/RealmContext'
import PriceDisplay from '../components/PriceDisplay'
import './CollectionPage.css'

function CollectionPage() {
    const { realms } = useRealm()
    const [characterName, setCharacterName] = useState('')
    const [selectedRealmSlug, setSelectedRealmSlug] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [collection, setCollection] = useState(null)

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
                            <div className="stat-icon">🪙</div>
                            <div className="stat-value">
                                {Math.floor(collection.total_value / 10000).toLocaleString()}g
                            </div>
                            <div className="stat-label">En or</div>
                        </div>
                    </div>

                    {/* Pets Table */}
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th style={{ width: 50 }}></th>
                                    <th>Nom</th>
                                    <th>Niveau</th>
                                    <th>Qualité</th>
                                    <th>Type</th>
                                    <th>Prix</th>
                                    <th>Échangeable</th>
                                </tr>
                            </thead>
                            <tbody>
                                {collection.pets.map((pet, index) => (
                                    <tr key={`${pet.pet_id}-${index}`}>
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
                                        <td>
                                            <span style={{ color: getQualityColor(pet.quality) }}>
                                                {pet.quality}
                                            </span>
                                        </td>
                                        <td>{pet.creature_type}</td>
                                        <td>
                                            <PriceDisplay value={pet.min_price} />
                                        </td>
                                        <td>{pet.is_tradable ? '✅' : '❌'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    )
}

export default CollectionPage
