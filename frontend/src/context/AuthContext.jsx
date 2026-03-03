import { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../services/api'

const AuthContext = createContext()

export function AuthProvider({ children }) {
    const [isAdmin, setIsAdmin] = useState(false)
    const [loading, setLoading] = useState(true)

    // Check token validity on mount
    useEffect(() => {
        const token = localStorage.getItem('adminToken')
        if (token) {
            api.auth.verify(token)
                .then(data => {
                    setIsAdmin(data.valid === true)
                    if (!data.valid) localStorage.removeItem('adminToken')
                })
                .catch(() => {
                    setIsAdmin(false)
                    localStorage.removeItem('adminToken')
                })
                .finally(() => setLoading(false))
        } else {
            setLoading(false)
        }
    }, [])

    const login = async (password) => {
        const data = await api.auth.login(password)
        if (data.token) {
            localStorage.setItem('adminToken', data.token)
            setIsAdmin(true)
            return { success: true }
        }
        return { success: false, error: 'Login failed' }
    }

    const logout = () => {
        localStorage.removeItem('adminToken')
        setIsAdmin(false)
    }

    const getToken = () => localStorage.getItem('adminToken')

    return (
        <AuthContext.Provider value={{ isAdmin, loading, login, logout, getToken }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
