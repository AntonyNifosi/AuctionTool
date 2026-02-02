import { useState, useEffect } from 'react'
import { useItemDetail } from '../hooks/useItemDetail'
import { PriceChart, VolumeChart } from './ItemDetail/PriceChart'
import { RealmPriceTable } from './ItemDetail/RealmPriceTable'
import { BestServersTable } from './ItemDetail/BestServersTable'
import { ItemMetrics } from './ItemDetail/ItemMetrics'
import { CraftInfo } from './ItemDetail/CraftInfo'
import styles from './ItemDetail/ItemDetail.module.css'

function ItemDetailModal({ item, realmId, onClose }) {
    const {
        activeTab, setActiveTab,
        loading,
        itemDetail,
        realmPrices,
        bestServers,
        chartData
    } = useItemDetail(item, realmId)

    const [timeRange, setTimeRange] = useState('3d')

    // Filter chart data based on time range
    const getFilteredChartData = () => {
        if (timeRange === 'all') return chartData

        const now = Date.now()
        const ranges = {
            '24h': 24 * 60 * 60 * 1000,
            '3d': 3 * 24 * 60 * 60 * 1000,
            '7d': 7 * 24 * 60 * 60 * 1000
        }

        const cutoff = now - (ranges[timeRange] || 0)
        return chartData.filter(d => d.timestamp >= cutoff)
    }

    const filteredData = getFilteredChartData()

    const TimeRangeControls = () => (
        <div className={styles.timeControls} style={{ marginBottom: '1rem', display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            {['24h', '3d', '7d', 'all'].map(range => (
                <button
                    key={range}
                    className={`btn btn-sm ${timeRange === range ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setTimeRange(range)}
                    style={{
                        opacity: timeRange === range ? 1 : 0.8,
                        border: timeRange === range ? '1px solid var(--primary)' : '1px solid rgba(255,255,255,0.3)',
                        background: timeRange === range ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
                        color: '#fff',
                        padding: '4px 12px',
                        cursor: 'pointer',
                        borderRadius: '4px',
                        transition: 'all 0.2s'
                    }}
                >
                    {range === 'all' ? 'Max' : range}
                </button>
            ))}
        </div>
    )

    // Responsive check
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768)

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768)
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])

    // Default to Overview on mobile if just opened
    useEffect(() => {
        if (isMobile && activeTab === 'prices') {
            setActiveTab('overview')
        }
    }, [isMobile])

    // Swipe Logic
    const [touchStart, setTouchStart] = useState(null)
    const [touchEnd, setTouchEnd] = useState(null)

    // Minimum distance for swipe
    const minSwipeDistance = 50

    const onTouchStart = (e) => {
        setTouchEnd(null)
        setTouchStart({ x: e.targetTouches[0].clientX, y: e.targetTouches[0].clientY })
    }

    const onTouchMove = (e) => {
        setTouchEnd({ x: e.targetTouches[0].clientX, y: e.targetTouches[0].clientY })
    }

    const onTouchEnd = () => {
        if (!touchStart || !touchEnd) return

        const distanceX = touchStart.x - touchEnd.x
        const distanceY = touchStart.y - touchEnd.y
        const isLeftSwipe = distanceX > minSwipeDistance
        const isRightSwipe = distanceX < -minSwipeDistance

        // Check if horizontal distance is dominant to avoid scroll interference
        if (Math.abs(distanceX) > Math.abs(distanceY) && Math.abs(distanceX) > minSwipeDistance) {

            const currentIndex = tabs.findIndex(t => t.id === activeTab)

            if (isLeftSwipe) {
                // Swipe Left -> Next Tab
                if (currentIndex < tabs.length - 1) {
                    setActiveTab(tabs[currentIndex + 1].id)
                }
            }

            if (isRightSwipe) {
                // Swipe Right -> Prev Tab
                if (currentIndex > 0) {
                    setActiveTab(tabs[currentIndex - 1].id)
                }
            }
        }
    }

    if (!item) return null

    const tabs = []

    if (isMobile) {
        tabs.push({ id: 'overview', icon: '👁️', label: 'Aperçu' })
    }

    tabs.push(
        { id: 'prices', icon: '📊', label: 'Prix par Serveur' },
        { id: 'history', icon: '📈', label: 'Historique Prix' },
        { id: 'volume', icon: '📦', label: 'Volume' },
        { id: 'best', icon: '🏆', label: 'Meilleurs Serveurs' },
        { id: 'stats', icon: '📉', label: 'Statistiques' },
        { id: 'craft', icon: '🔨', label: 'Craft' },
    )

    // Ensure activeTab is valid
    if (!isMobile && activeTab === 'overview') {
        setActiveTab('prices')
    }

    return (
        <div className={styles.modalOverlay} onClick={onClose}>
            <div
                className={styles.modalContent}
                onClick={(e) => e.stopPropagation()}
                onTouchStart={onTouchStart}
                onTouchMove={onTouchMove}
                onTouchEnd={onTouchEnd}
            >
                {/* Header */}
                <div className={styles.modalHeader}>
                    <div className={styles.modalTitleRow}>
                        {item.icon_url && item.icon_url !== 'NONE' && (
                            <img src={item.icon_url} alt="" className={styles.modalIcon} />
                        )}
                        <div style={{ minWidth: 0 }}>
                            <h2 className={styles.modalTitle}>
                                📋 {item.name}
                            </h2>
                            <span className="badge">{item.category || 'Housing'}</span>
                        </div>
                    </div>
                    <button className={styles.modalClose} onClick={onClose}>✕</button>
                </div>

                {/* Metrics - DESKTOP ONLY */}
                {!isMobile && (
                    <div className={styles.modalMetrics}>
                        <ItemMetrics
                            item={item}
                            itemDetail={itemDetail}
                            sales3d={itemDetail?.sales_3d ?? realmPrices.find(r => r.realm_id === parseInt(realmId))?.sales_3d}
                            styles={styles}
                        />
                    </div>
                )}

                {/* Tabs */}
                <div className={styles.modalTabs}>
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            className={`${styles.modalTab} ${activeTab === tab.id ? styles.activeTab : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            <span>{tab.icon}</span>
                            <span>{tab.label}</span>
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className={styles.modalBody}>
                    {loading ? (
                        <div className={styles.loadingState}>
                            <div className={styles.spinner}></div>
                            <p>Chargement...</p>
                        </div>
                    ) : (
                        <>
                            {/* Aperçu (Mobile Only) */}
                            {activeTab === 'overview' && isMobile && (
                                <div className={styles.tabContent}>
                                    <div className={styles.modalMetrics} style={{ padding: 0, border: 'none' }}>
                                        <ItemMetrics
                                            item={item}
                                            itemDetail={itemDetail}
                                            sales3d={itemDetail?.sales_3d ?? realmPrices.find(r => r.realm_id === parseInt(realmId))?.sales_3d}
                                            styles={styles}
                                        />
                                    </div>
                                    <div style={{ marginTop: '1rem' }}>
                                        <h3>🏆 Top 3 Meilleurs Serveurs</h3>
                                        <BestServersTable bestServers={bestServers ? bestServers.slice(0, 3) : []} styles={styles} />
                                    </div>
                                </div>
                            )}

                            {/* Prix par Serveur */}
                            {activeTab === 'prices' && (
                                <div className={styles.tabContent}>
                                    <h3>📊 Prix sur tous les serveurs</h3>
                                    <RealmPriceTable realmPrices={realmPrices} styles={styles} />
                                </div>
                            )}

                            {/* Historique Prix */}
                            {activeTab === 'history' && (
                                <div className={styles.tabContent}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <h3>📈 Historique des prix</h3>
                                        <TimeRangeControls />
                                    </div>
                                    <PriceChart data={filteredData} styles={styles} />
                                </div>
                            )}

                            {/* Volume */}
                            {activeTab === 'volume' && (
                                <div className={styles.tabContent}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <h3>📦 Évolution du volume</h3>
                                        <TimeRangeControls />
                                    </div>
                                    <VolumeChart data={filteredData} styles={styles} />
                                </div>
                            )}

                            {/* Meilleurs Serveurs */}
                            {activeTab === 'best' && (
                                <div className={styles.tabContent}>
                                    <h3>🏆 Meilleurs serveurs pour vendre</h3>
                                    <BestServersTable bestServers={bestServers} styles={styles} />
                                </div>
                            )}

                            {/* Statistiques */}
                            {activeTab === 'stats' && (
                                <div className={styles.tabContent}>
                                    <h3>📉 Statistiques détaillées</h3>
                                    <div className={`${styles.statsGrid} stats-grid`}>
                                        {/* Reuse ItemMetrics logic or custom stats */}
                                        <div className="stat-card">
                                            <div className="stat-value">{realmPrices.filter(p => p.min_price).length}</div>
                                            <div className="stat-label">Serveurs avec stock</div>
                                        </div>
                                        <div className="stat-card">
                                            <div className="stat-value">
                                                {itemDetail?.price_history?.length || 0}
                                            </div>
                                            <div className="stat-label">Points d'historique</div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Craft */}
                            {activeTab === 'craft' && (
                                <div className={styles.tabContent}>
                                    <h3>🔨 Informations de craft</h3>
                                    <CraftInfo item={item} itemDetail={itemDetail} styles={styles} />
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

export default ItemDetailModal
