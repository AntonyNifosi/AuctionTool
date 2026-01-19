import { createContext, useContext, useState, useEffect } from 'react'

const RealmContext = createContext()

export function RealmProvider({ children }) {
    const [realms, setRealms] = useState([])
    const [selectedRealm, setSelectedRealm] = useState(null)
    const [loading, setLoading] = useState(true)
    const [updateStatus, setUpdateStatus] = useState({
        isRunning: false,
        progress: 0,
        statusMessage: '',
        lastUpdateTime: null
    })

    // Load realms on mount
    useEffect(() => {
        fetchRealms()
        // Poll update status every 3 seconds
        const interval = setInterval(fetchUpdateStatus, 3000)
        return () => clearInterval(interval)
    }, [])

    const fetchRealms = async () => {
        try {
            const response = await fetch('/api/realms')
            if (response.ok) {
                const data = await response.json()
                setRealms(data)
                // Set default realm (first one or saved preference)
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
            }
        } catch (error) {
            console.error('Failed to fetch realms:', error)
        } finally {
            setLoading(false)
        }
    }

    const fetchUpdateStatus = async () => {
        try {
            const response = await fetch('/api/update/status')
            if (response.ok) {
                const data = await response.json()
                setUpdateStatus({
                    isRunning: data.is_running,
                    progress: data.progress,
                    statusMessage: data.status_message,
                    lastUpdateTime: data.last_update_time
                })
            }
        } catch (error) {
            // Silent fail for status check
        }
    }

    const selectRealm = (realm) => {
        setSelectedRealm(realm)
        localStorage.setItem('selectedRealmId', realm.id.toString())
    }

    const startUpdate = async (force = false) => {
        try {
            const params = new URLSearchParams({ force: force.toString() })
            if (selectedRealm) {
                params.append('priority_realm_id', selectedRealm.id.toString())
            }
            const response = await fetch(`/api/update/start?${params}`, { method: 'POST' })
            if (response.ok) {
                fetchUpdateStatus()
            }
        } catch (error) {
            console.error('Failed to start update:', error)
        }
    }

    return (
        <RealmContext.Provider value={{
            realms,
            selectedRealm,
            selectRealm,
            loading,
            updateStatus,
            startUpdate,
            refreshStatus: fetchUpdateStatus
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
