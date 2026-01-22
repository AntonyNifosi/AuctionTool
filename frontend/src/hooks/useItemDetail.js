import { useState, useEffect } from 'react'
import { api } from '../services/api'

export function useItemDetail(item, realmId) {
    const [activeTab, setActiveTab] = useState('prices')
    const [loading, setLoading] = useState(true)
    const [itemDetail, setItemDetail] = useState(null)
    const [realmPrices, setRealmPrices] = useState([])
    const [bestServers, setBestServers] = useState([])

    useEffect(() => {
        if (!item || !realmId) return

        const fetchDetails = async () => {
            setLoading(true)
            try {
                // Parallel fetch for better performance
                const [detailData, pricesData, bestData] = await Promise.all([
                    api.items.getDetails(item.item_id, realmId).catch(err => {
                        console.error('Failed to fetch details', err);
                        return null;
                    }),
                    api.items.getRealmPrices(item.item_id).catch(err => {
                        console.error('Failed to fetch realm prices', err);
                        return { realm_prices: [] };
                    }),
                    api.prices.getBestServers(realmId, item.item_id).catch(err => {
                        console.error('Failed to fetch best servers', err);
                        return { servers: [] };
                    })
                ])

                if (detailData) setItemDetail(detailData)
                if (pricesData) setRealmPrices(pricesData.realm_prices || [])
                if (bestData) setBestServers(bestData.servers || [])

            } catch (err) {
                console.error('Global error fetching item data:', err)
            } finally {
                setLoading(false)
            }
        }

        fetchDetails()
    }, [item, realmId])

    // Derived Data: Chart Data
    const chartData = (itemDetail?.price_history || []).map((h, index) => {
        const dt = new Date(h.recorded_at)
        return {
            dateLabel: `${dt.toLocaleDateString()} ${dt.getHours()}h`,
            date: dt.toLocaleDateString(),
            timestamp: dt.getTime(),
            min_price: h.min_price / 10000, // Gold conversion
            avg_price: h.avg_price ? h.avg_price / 10000 : null,
            quantity: h.total_quantity,
            auctions: h.auction_count
        }
    }).sort((a, b) => a.timestamp - b.timestamp)

    return {
        activeTab,
        setActiveTab,
        loading,
        itemDetail,
        realmPrices,
        bestServers,
        chartData
    }
}
