import { useState } from 'react'
import { useItemDetail } from '../hooks/useItemDetail'
import { PriceChart, VolumeChart } from './ItemDetail/PriceChart'
import { RealmPriceTable } from './ItemDetail/RealmPriceTable'
import { BestServersTable } from './ItemDetail/BestServersTable'
import { ItemMetrics } from './ItemDetail/ItemMetrics'
import { CraftInfo } from './ItemDetail/CraftInfo'
import './ItemDetailModal.css'

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
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="modal-title-row" style={{ flexWrap: 'nowrap' }}>
                        {item.icon_url && item.icon_url !== 'NONE' && (
                            <img src={item.icon_url} alt="" className="modal-icon" style={{ flexShrink: 0 }} />
                        )}
                        <div style={{ minWidth: 0 }}>
                            <h2 className="modal-title" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                📋 {item.name}
                            </h2>
                            <span className="badge">{item.category || 'Housing'}</span>
                        </div>
                    </div>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>

                {/* Metrics */}
                <ItemMetrics item={item} itemDetail={itemDetail} />

                {/* Tabs */}
                <div className="modal-tabs">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            className={`modal-tab ${activeTab === tab.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            <span>{tab.icon}</span>
                            <span>{tab.label}</span>
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className="modal-body">
                    {loading ? (
                        <div className="loading-state">
                            <div className="spinner"></div>
                            <p>Chargement...</p>
                        </div>
                    ) : (
                        <>
                            {/* Prix par Serveur */}
                            {activeTab === 'prices' && (
                                <div className="tab-content">
                                    <h3>📊 Prix sur tous les serveurs</h3>
                                    <RealmPriceTable realmPrices={realmPrices} />
                                </div>
                            )}

                            {/* Historique Prix */}
                            {activeTab === 'history' && (
                                <div className="tab-content">
                                    <h3>📈 Historique des prix (21 jours)</h3>
                                    <PriceChart data={chartData} />
                                </div>
                            )}

                            {/* Volume */}
                            {activeTab === 'volume' && (
                                <div className="tab-content">
                                    <h3>📦 Évolution du volume</h3>
                                    <VolumeChart data={chartData} />
                                </div>
                            )}

                            {/* Meilleurs Serveurs */}
                            {activeTab === 'best' && (
                                <div className="tab-content">
                                    <h3>🏆 Meilleurs serveurs pour vendre</h3>
                                    <BestServersTable bestServers={bestServers} />
                                </div>
                            )}

                            {/* Statistiques */}
                            {activeTab === 'stats' && (
                                <div className="tab-content">
                                    <h3>📉 Statistiques détaillées</h3>
                                    <div className="stats-grid">
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
                                <div className="tab-content">
                                    <h3>🔨 Informations de craft</h3>
                                    <CraftInfo item={item} itemDetail={itemDetail} />
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
