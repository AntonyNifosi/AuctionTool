import { useState } from 'react'
import { useRealm } from '../context/RealmContext'

function CollectionPage() {
    const { selectedRealm } = useRealm()
    const [characterName, setCharacterName] = useState('')
    const [realmName, setRealmName] = useState('')

    if (!selectedRealm) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">🌍</div>
                <p>Veuillez sélectionner un serveur</p>
            </div>
        )
    }

    return (
        <div className="collection-page">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">👤</span>
                    Ma Collection
                </h1>
                <p className="page-subtitle">
                    Consultez votre collection de pets Battle.net
                </p>
            </div>

            {/* Character Input */}
            <div className="card" style={{ maxWidth: 600 }}>
                <div className="card-header">
                    <h3>🔗 Lier un personnage</h3>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                    <div className="filter-group">
                        <label className="filter-label">🌍 Serveur du personnage</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="Ex: Hyjal"
                            value={realmName}
                            onChange={(e) => setRealmName(e.target.value)}
                        />
                    </div>

                    <div className="filter-group">
                        <label className="filter-label">👤 Nom du personnage</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="Ex: Arthas"
                            value={characterName}
                            onChange={(e) => setCharacterName(e.target.value)}
                        />
                    </div>

                    <button className="btn btn-primary" disabled>
                        🔍 Charger la collection (bientôt disponible)
                    </button>
                </div>
            </div>

            {/* Info */}
            <div className="card" style={{ maxWidth: 600, marginTop: 'var(--spacing-lg)' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--spacing-md)' }}>
                    <span style={{ fontSize: '2rem' }}>💡</span>
                    <div>
                        <h4 style={{ marginBottom: 'var(--spacing-xs)' }}>Fonctionnalité à venir</h4>
                        <p className="text-muted" style={{ fontSize: '0.875rem' }}>
                            Cette page permettra bientôt de charger votre collection de pets depuis l'API Battle.net
                            et de comparer les prix avec l'Hôtel des Ventes pour identifier les meilleures opportunités
                            de vente.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default CollectionPage
