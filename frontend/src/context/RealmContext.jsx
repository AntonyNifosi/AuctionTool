import { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../services/api'

const RealmContext = createContext()

export function RealmProvider({ children }) {
    const [realms, setRealms] = useState([])
    const [selectedRealm, setSelectedRealm] = useState(null)
    const [favoriteRealmIds, setFavoriteRealmIds] = useState([])
    const [loading, setLoading] = useState(true)
    const [updateStatus, setUpdateStatus] = useState({
        isRunning: false,
        progress: 0,
        statusMessage: '',
        lastUpdateTime: null
    })

    // Load favorites from localStorage on mount
    useEffect(() => {
        const savedFavorites = localStorage.getItem('favoriteRealmIds')
        if (savedFavorites) {
            try {
                setFavoriteRealmIds(JSON.parse(savedFavorites))
            } catch {
                setFavoriteRealmIds([])
            }
        }
    }, [])

    // Load realms on mount
    useEffect(() => {
        fetchRealms()
        // Poll update status every 3 seconds
        const interval = setInterval(fetchUpdateStatus, 3000)
        return () => clearInterval(interval)
    }, [])

    const fetchRealms = async () => {
        try {
            const data = await api.realms.getAll()
            setRealms(data)
            const savedRealmId = localStorage.getItem('selectedRealmId')
            if (savedRealmId) {
                const saved = data.find(r => r.id === parseInt(savedRealmId))
                if (saved) {
                    setSelectedRealm(saved)
                } else if (data.length > 0) {
                    setSelectedRealm(data[0])
                }
            } else if (data.length > 0) {
                setSelectedRealm(data[0])
            }
        } catch (error) {
            console.error('Failed to fetch realms:', error)
        } finally {
            setLoading(false)
        }
    }

    const fetchUpdateStatus = async () => {
        try {
            const data = await api.update.getStatus()
            setUpdateStatus({
                isRunning: data.is_running,
                progress: data.progress,
                statusMessage: data.status_message,
                lastUpdateTime: data.last_update_time
            })
        } catch (error) {
            // Silent fail for status check
        }
    }

    const selectRealm = (realm) => {
        setSelectedRealm(realm)
        localStorage.setItem('selectedRealmId', realm.id.toString())
    }

    const toggleFavoriteRealm = (realmId) => {
        setFavoriteRealmIds(prev => {
            const newFavorites = prev.includes(realmId)
                ? prev.filter(id => id !== realmId)
                : [...prev, realmId]
            localStorage.setItem('favoriteRealmIds', JSON.stringify(newFavorites))
            return newFavorites
        })
    }

    const isFavoriteRealm = (realmId) => {
        return favoriteRealmIds.includes(realmId)
    }

    // Sort realms with favorites first
    const sortedRealms = [...realms].sort((a, b) => {
        const aFav = favoriteRealmIds.includes(a.id)
        const bFav = favoriteRealmIds.includes(b.id)
        if (aFav && !bFav) return -1
        if (!aFav && bFav) return 1
        return a.name.localeCompare(b.name)
    })

    const startUpdate = async (force = false) => {
        try {
            const params = { force: force }
            if (selectedRealm) {
                params.priority_realm_id = selectedRealm.id
            }
            await api.update.start(params)
            fetchUpdateStatus()
        } catch (error) {
            console.error('Failed to start update:', error)
        }
    }

    return (
        <RealmContext.Provider value={{
            realms: sortedRealms,
            selectedRealm,
            selectRealm,
            loading,
            updateStatus,
            startUpdate,
            refreshStatus: fetchUpdateStatus,
            favoriteRealmIds,
            toggleFavoriteRealm,
            isFavoriteRealm
        }}>
            {children}
        </RealmContext.Provider>
    )
}

export function useRealm() {
    const context = useContext(RealmContext)
    if (!context) {
        throw new Error('useRealm must be used within a RealmProvider')
    }
    return context
}
