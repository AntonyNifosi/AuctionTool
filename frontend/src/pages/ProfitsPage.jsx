import { useState, useEffect } from 'react'
import { useRealm } from '../context/RealmContext'
import PriceDisplay from '../components/PriceDisplay'
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

    // Filters
    const [selectedProfessions, setSelectedProfessions] = useState([])
    const [selectedExpansion, setSelectedExpansion] = useState('')
    const [minProfitGold, setMinProfitGold] = useState(0)
    const [minVolume, setMinVolume] = useState(0)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const pageSize = 50

    // Fetch profits data
    useEffect(() => {
        if (!selectedRealm) return

        const fetchProfits = async () => {
            setLoading(true)

            try {
                const params = new URLSearchParams({
                    realm_id: selectedRealm.id,
                    page: page.toString(),
                    page_size: pageSize.toString(),
                    min_profit: (minProfitGold * 10000).toString(),
                    min_volume: minVolume.toString()
                })

                if (selectedProfessions.length > 0) {
                    params.append('professions', selectedProfessions.join(','))
                }
                if (selectedExpansion) {
                    params.append('expansion', selectedExpansion)
                }

                const response = await fetch(`/api/profits?${params}`)
                if (response.ok) {
                    const data = await response.json()
                    setItems(data.items || [])
                    setTotal(data.total || 0)
                    setTotalPages(Math.ceil((data.total || 0) / pageSize))
                }
            } catch (err) {
                console.error('Failed to fetch profits:', err)
            } finally {
                setLoading(false)
            }
        }

        fetchProfits()
    }, [selectedRealm, selectedProfessions, selectedExpansion, minProfitGold, minVolume, page])

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

    const toggleProfession = (id) => {
        setSelectedProfessions(prev =>
            prev.includes(id)
                ? prev.filter(p => p !== id)
                : [...prev, id]
        )
        setPage(1)
    }

    const getProfitIndicator = (item) => {
        if (!item.profit) return { icon: '⚪', class: '' }
        if (item.profit > 0) return { icon: '🟢', class: 'profit-positive' }
        return { icon: '🔴', class: 'profit-negative' }
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
                    💡 Le prix de vente affiché est le <strong>prix minimum observé sur les 3 derniers jours</strong>
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
                <div className="filter-group">
                    <label className="filter-label">📅 Extension</label>
                    <select
                        className="select"
                        value={selectedExpansion}
                        onChange={(e) => { setSelectedExpansion(e.target.value); setPage(1); }}
                    >
                        <option value="">Toutes les extensions</option>
                        {expansions.map((exp) => (
                            <option key={exp} value={exp}>{exp}</option>
                        ))}
                    </select>
                </div>

                <div className="filter-group">
                    <label className="filter-label">💰 Profit min (or)</label>
                    <input
                        type="number"
                        className="input"
                        value={minProfitGold}
                        onChange={(e) => { setMinProfitGold(parseInt(e.target.value) || 0); setPage(1); }}
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
                        onChange={(e) => { setMinVolume(parseInt(e.target.value) || 0); setPage(1); }}
                        min="0"
                    />
                </div>
            </div>

            {/* Results */}
            <div className="results-info">
                <span className="results-count">💰 {total.toLocaleString()} items craftables</span>
            </div>

            {/* Table */}
            <div className="table-container">
                <table className="table">
                    <thead>
                        <tr>
                            <th style={{ width: 50 }}></th>
                            <th>Nom</th>
                            <th>Métier</th>
                            <th>Extension</th>
                            <th>Coût Craft</th>
                            <th>Prix Vente</th>
                            <th>Profit</th>
                            <th>Marge</th>
                            <th>Volume</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            Array.from({ length: 10 }).map((_, i) => (
                                <tr key={i}>
                                    {Array.from({ length: 9 }).map((_, j) => (
                                        <td key={j}><div className="skeleton" style={{ width: j === 1 ? 200 : 80, height: 20 }} /></td>
                                    ))}
                                </tr>
                            ))
                        ) : items.length === 0 ? (
                            <tr>
                                <td colSpan="9" style={{ textAlign: 'center', padding: '2rem' }}>
                                    Aucun item craftable trouvé
                                </td>
                            </tr>
                        ) : (
                            items.map((item) => {
                                const indicator = getProfitIndicator(item)
                                return (
                                    <tr key={item.item_id}>
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
                                    </tr>
                                )
                            })
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="pagination">
                    <button className="pagination-btn" onClick={() => setPage(1)} disabled={page === 1}>««</button>
                    <button className="pagination-btn" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>«</button>
                    <span className="pagination-info">Page {page} / {totalPages}</span>
                    <button className="pagination-btn" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>»</button>
                    <button className="pagination-btn" onClick={() => setPage(totalPages)} disabled={page === totalPages}>»»</button>
                </div>
            )}
        </div>
    )
}

export default ProfitsPage
