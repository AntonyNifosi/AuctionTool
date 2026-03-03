import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useRealm } from '../../context/RealmContext'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../services/api'
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

    const { isAdmin, login, logout } = useAuth()

    const [showLoginModal, setShowLoginModal] = useState(false)
    const [loginPassword, setLoginPassword] = useState('')
    const [loginError, setLoginError] = useState('')
    const [loginLoading, setLoginLoading] = useState(false)

    const navItems = [
        { path: '/', icon: '🏠', label: 'Objets Housing', group: 'Housing' },
        { path: '/profits', icon: '💰', label: 'Rentabilité Artisanat', group: 'Housing' },
        { path: '/pets', icon: '🐾', label: 'Mascottes', group: 'Pets' },
        { path: '/collection', icon: '👤', label: 'Ma Collection', group: 'Pets' },
    ]

    const groupedItems = navItems.reduce((acc, item) => {
        if (!acc[item.group]) acc[item.group] = []
        acc[item.group].push(item)
        return acc
    }, {})

    const formatLastUpdate = () => {
        if (!updateStatus.lastUpdateTime) return null
        let dateStr = updateStatus.lastUpdateTime
        if (!dateStr.endsWith('Z') && !dateStr.includes('+')) {
            dateStr += 'Z'
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

    const [isOpen, setIsOpen] = useState(false)

    // Close sidebar when route changes
    useEffect(() => {
        setIsOpen(false)
    }, [location.pathname])

    const handleLogin = async (e) => {
        e.preventDefault()
        setLoginError('')
        setLoginLoading(true)
        try {
            const result = await login(loginPassword)
            if (result.success) {
                setShowLoginModal(false)
                setLoginPassword('')
            }
        } catch (err) {
            setLoginError(err.message || 'Mot de passe incorrect')
        } finally {
            setLoginLoading(false)
        }
    }

    const handleSyncRecipes = async () => {
        try {
            await api.update.syncRecipes()
        } catch (err) {
            console.error('Failed to sync recipes:', err)
        }
    }

    return (
        <>
            {/* Mobile Toggle Button */}
            <button
                className="mobile-toggle"
                onClick={() => setIsOpen(!isOpen)}
                aria-label="Menu"
            >
                {isOpen ? '✕' : '☰'}
            </button>

            {/* Backdrop for mobile */}
            {isOpen && (
                <div
                    className="sidebar-backdrop"
                    onClick={() => setIsOpen(false)}
                />
            )}

            <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
                {/* Logo */}
                <div className="sidebar-header">
                    <div className="logo">
                        <span className="logo-icon">🏠</span>
                        <span className="logo-text">WoW Housing</span>
                    </div>
                    {/* Close button inside sidebar for convenience */}
                    <button
                        className="sidebar-close-btn"
                        onClick={() => setIsOpen(false)}
                    >
                        ✕
                    </button>
                </div>

                {/* Navigation */}
                <nav className="sidebar-nav">
                    {Object.entries(groupedItems).map(([group, items]) => (
                        <div key={group} className="nav-group">
                            <div className="nav-group-title">{group === 'Housing' ? '🏡 Housing' : '🐾 Mascottes'}</div>
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

                {/* Admin Controls - Only visible when logged in */}
                {isAdmin && (
                    <div className="sidebar-section">
                        <div className="section-title">🔧 Administration</div>
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

                        <button
                            className="btn btn-secondary sync-recipes-btn"
                            onClick={handleSyncRecipes}
                            disabled={updateStatus.isRunning}
                        >
                            📜 Sync Recettes
                        </button>
                    </div>
                )}

                {/* Update Status - Always visible */}
                <div className="sidebar-section">
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

                {/* Login/Logout Button */}
                <div className="sidebar-section sidebar-auth">
                    {isAdmin ? (
                        <button className="btn btn-auth btn-logout" onClick={logout}>
                            🚪 Déconnexion
                        </button>
                    ) : (
                        <button className="btn btn-auth btn-login" onClick={() => setShowLoginModal(true)}>
                            🔑 Admin
                        </button>
                    )}
                </div>
            </aside>

            {/* Login Modal */}
            {showLoginModal && (
                <div className="login-modal-backdrop" onClick={() => setShowLoginModal(false)}>
                    <div className="login-modal" onClick={(e) => e.stopPropagation()}>
                        <h3>🔑 Connexion Admin</h3>
                        <form onSubmit={handleLogin}>
                            <input
                                type="password"
                                className="login-input"
                                placeholder="Mot de passe"
                                value={loginPassword}
                                onChange={(e) => setLoginPassword(e.target.value)}
                                autoFocus
                            />
                            {loginError && <p className="login-error">{loginError}</p>}
                            <div className="login-actions">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => setShowLoginModal(false)}
                                >
                                    Annuler
                                </button>
                                <button
                                    type="submit"
                                    className="btn btn-primary"
                                    disabled={loginLoading || !loginPassword}
                                >
                                    {loginLoading ? 'Connexion...' : 'Se connecter'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </>
    )
}

export default Sidebar
