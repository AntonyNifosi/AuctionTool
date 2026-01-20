import { NavLink, useLocation } from 'react-router-dom'
import { useRealm } from '../../context/RealmContext'
import './Sidebar.css'

function Sidebar() {
    const location = useLocation()
    const {
        realms,
        selectedRealm,
        selectRealm,
        loading,
        updateStatus,
        startUpdate,
        toggleFavoriteRealm,
        isFavoriteRealm
    } = useRealm()

    const navItems = [
        { path: '/', icon: '🏠', label: 'Items Housing', group: 'Housing' },
        { path: '/profits', icon: '💰', label: 'Profits Craft', group: 'Housing' },
        { path: '/pets', icon: '🐾', label: 'Pets', group: 'Pets' },
        { path: '/collection', icon: '👤', label: 'Ma Collection', group: 'Pets' },
    ]

    const groupedItems = navItems.reduce((acc, item) => {
        if (!acc[item.group]) acc[item.group] = []
        acc[item.group].push(item)
        return acc
    }, {})

    const formatLastUpdate = () => {
        if (!updateStatus.lastUpdateTime) return null
        // API returns UTC timestamp, ensure we parse it as UTC
        let dateStr = updateStatus.lastUpdateTime
        if (!dateStr.endsWith('Z') && !dateStr.includes('+')) {
            dateStr += 'Z' // Append Z to indicate UTC
        }
        const date = new Date(dateStr)
        const now = new Date()
        const diffMs = now - date
        const diffMin = Math.floor(diffMs / 60000)

        if (diffMin < 1) return "moins d'1 min"
        if (diffMin < 60) return `${diffMin} min`

        const hours = Math.floor(diffMin / 60)
        const mins = diffMin % 60

        if (mins === 0) return `${hours}h`
        return `${hours}h ${mins}min`
    }

    return (
        <aside className="sidebar">
            {/* Logo */}
            <div className="sidebar-header">
                <div className="logo">
                    <span className="logo-icon">🏠</span>
                    <span className="logo-text">WoW Housing</span>
                </div>
            </div>

            {/* Navigation */}
            <nav className="sidebar-nav">
                {Object.entries(groupedItems).map(([group, items]) => (
                    <div key={group} className="nav-group">
                        <div className="nav-group-title">{group === 'Housing' ? '🏡 Housing' : '🐾 Pets'}</div>
                        {items.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            >
                                <span className="nav-icon">{item.icon}</span>
                                <span className="nav-label">{item.label}</span>
                            </NavLink>
                        ))}
                    </div>
                ))}
            </nav>

            {/* Realm Selector */}
            <div className="sidebar-section">
                <div className="section-title">⚙️ Configuration</div>
                <div className="realm-selector">
                    <label className="filter-label">🌍 Serveur</label>
                    <div className="realm-select-row">
                        <select
                            className="select"
                            value={selectedRealm?.id || ''}
                            onChange={(e) => {
                                const realm = realms.find(r => r.id === parseInt(e.target.value))
                                if (realm) selectRealm(realm)
                            }}
                            disabled={loading}
                        >
                            {realms.map((realm) => (
                                <option key={realm.id} value={realm.id}>
                                    {isFavoriteRealm(realm.id) ? '⭐ ' : ''}{realm.name}
                                </option>
                            ))}
                        </select>
                        {selectedRealm && (
                            <button
                                className={`favorite-btn ${isFavoriteRealm(selectedRealm.id) ? 'active' : ''}`}
                                onClick={() => toggleFavoriteRealm(selectedRealm.id)}
                                title={isFavoriteRealm(selectedRealm.id) ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                            >
                                {isFavoriteRealm(selectedRealm.id) ? '⭐' : '☆'}
                            </button>
                        )}
                    </div>
                    <p className="realm-hint">💡 Les serveurs favoris apparaissent en premier</p>
                </div>
            </div>

            {/* Update Controls */}
            <div className="sidebar-section">
                <button
                    className="btn btn-primary refresh-btn"
                    onClick={() => startUpdate(true)}
                    disabled={updateStatus.isRunning}
                >
                    {updateStatus.isRunning ? (
                        <>
                            <span className="spinner"></span>
                            Mise à jour...
                        </>
                    ) : (
                        <>🔄 Rafraîchir les données</>
                    )}
                </button>

                {updateStatus.isRunning && (
                    <div className="update-progress">
                        <div className="progress-text">{updateStatus.statusMessage}</div>
                        <div className="progress-bar">
                            <div
                                className="progress-bar-fill"
                                style={{ width: `${updateStatus.progress * 100}%` }}
                            />
                        </div>
                    </div>
                )}

                {formatLastUpdate() && (
                    <div className="last-update">
                        🕒 Dernière mise à jour il y a {formatLastUpdate()}
                    </div>
                )}
            </div>

            {/* Info Panel */}
            <div className="sidebar-info">
                <div className="info-title">📊 Légende</div>
                <div className="info-item">
                    <span className="trend trend-up">📈 +5%</span> Prix en hausse
                </div>
                <div className="info-item">
                    <span className="trend trend-down">📉 -5%</span> Prix en baisse
                </div>
                <div className="info-item">
                    <span className="trend trend-stable">➡️ 0%</span> Prix stable
                </div>
            </div>
        </aside>
    )
}

export default Sidebar
