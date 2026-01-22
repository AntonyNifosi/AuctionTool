import { useState } from 'react'
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

    if (!item) return null

    const tabs = [
        { id: 'prices', icon: '📊', label: 'Prix par Serveur' },
        { id: 'history', icon: '📈', label: 'Historique Prix' },
        { id: 'volume', icon: '📦', label: 'Volume' },
        { id: 'best', icon: '🏆', label: 'Meilleurs Serveurs' },
        { id: 'stats', icon: '📉', label: 'Statistiques' },
        { id: 'craft', icon: '🔨', label: 'Craft' },
    ]

    return (
        <div className={styles.modalOverlay} onClick={onClose}>
            <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
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

                {/* Metrics */}
                <div className={styles.modalMetrics}>
                    <ItemMetrics item={item} itemDetail={itemDetail} styles={styles} />
                </div>

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
                                    <h3>📈 Historique des prix (21 jours)</h3>
                                    <PriceChart data={chartData} styles={styles} />
                                </div>
                            )}

                            {/* Volume */}
                            {activeTab === 'volume' && (
                                <div className={styles.tabContent}>
                                    <h3>📦 Évolution du volume</h3>
                                    <VolumeChart data={chartData} styles={styles} />
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
