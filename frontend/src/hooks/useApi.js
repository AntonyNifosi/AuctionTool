import { useState, useEffect, useCallback } from 'react'

/**
 * Custom hook for API calls with loading/error states
 * @param {string} url - API endpoint
 * @param {object} options - Fetch options
 * @returns {object} { data, loading, error, refetch }
 */
export function useApi(url, options = {}) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const fetchData = useCallback(async () => {
        if (!url) {
            setLoading(false)
            return
        }

        try {
            setLoading(true)
            setError(null)

            const response = await fetch(url, options)

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }

            const result = await response.json()
            setData(result)
        } catch (err) {
            setError(err.message)
            console.error('API Error:', err)
        } finally {
            setLoading(false)
        }
    }, [url, JSON.stringify(options)])

    useEffect(() => {
        fetchData()
    }, [fetchData])

    return { data, loading, error, refetch: fetchData }
}

/**
 * Hook for paginated API calls
 * @param {string} baseUrl - Base API endpoint
 * @param {object} params - Query parameters
 * @returns {object} { data, loading, error, page, setPage, totalPages }
 */
export function usePaginatedApi(baseUrl, params = {}) {
    const [page, setPage] = useState(1)
    const pageSize = params.page_size || 50

    // Build URL with params
    const searchParams = new URLSearchParams({
        ...params,
        page: page.toString(),
        page_size: pageSize.toString()
    })

    const url = `${baseUrl}?${searchParams.toString()}`
    const { data, loading, error, refetch } = useApi(url)

    const totalPages = data ? Math.ceil(data.total / pageSize) : 1

    return {
        items: data?.items || [],
        total: data?.total || 0,
        loading,
        error,
        page,
        setPage,
        totalPages,
        pageSize,
        refetch
    }
}
