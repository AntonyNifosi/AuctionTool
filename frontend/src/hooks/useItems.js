import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'
import { debounce } from '../utils/formatters'

export function useItems(selectedRealm) {
    const [items, setItems] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [categories, setCategories] = useState([])

    // Filters & Pagination State
    const [search, setSearch] = useState('')
    const [debouncedSearch, setDebouncedSearch] = useState('')
    const [category, setCategory] = useState('')
    const [sortBy, setSortBy] = useState('min_price')
    const [sortOrder, setSortOrder] = useState('desc')
    const [page, setPage] = useState(1)

    // Pagination Metadata
    const [total, setTotal] = useState(0)
    const [totalPages, setTotalPages] = useState(1)
    const pageSize = 50

    // Debounce search input
    const debouncedSetSearch = useCallback(
        debounce((value) => {
            setDebouncedSearch(value)
            setPage(1)
        }, 300),
        []
    )

    useEffect(() => {
        debouncedSetSearch(search)
    }, [search, debouncedSetSearch])

    // Load Categories (Only once)
    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const data = await api.items.getCategories()
                setCategories(data.categories || [])
            } catch (err) {
                console.error('Failed to fetch categories:', err)
            }
        }
        fetchCategories()
    }, [])

    // Load Items
    useEffect(() => {
        if (!selectedRealm) return

        const fetchItems = async () => {
            setLoading(true)
            setError(null)

            try {
                const params = {
                    realm_id: selectedRealm.id,
                    page,
                    page_size: pageSize,
                    sort_by: sortBy,
                    sort_order: sortOrder
                }

                if (debouncedSearch) params.search = debouncedSearch
                if (category) params.category = category

                const data = await api.items.list(params)
                setItems(data.items || [])
                setTotal(data.total || 0)
                setTotalPages(Math.ceil((data.total || 0) / pageSize))
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }

        fetchItems()
    }, [selectedRealm, debouncedSearch, category, sortBy, sortOrder, page])

    // Actions
    const handleSort = (column) => {
        if (sortBy === column) {
            setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
        } else {
            setSortBy(column)
            setSortOrder(column === 'min_price' || column === 'trend' ? 'desc' : 'asc')
        }
        setPage(1)
    }

    const resetPage = () => setPage(1)

    return {
        // Data
        items,
        loading,
        error,
        categories,
        total,
        totalPages,

        // State
        search,
        category,
        sortBy,
        sortOrder,
        page,

        // Setters & Actions
        setSearch,
        setCategory: (cat) => { setCategory(cat); resetPage(); },
        setPage,
        handleSort,
        getSortIcon: (column) => {
            if (sortBy !== column) return ' ⇅'
            return sortOrder === 'asc' ? ' ↑' : ' ↓'
        }
    }
}
