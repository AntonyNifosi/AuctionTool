/**
 * Format copper value to gold/silver/copper display
 * @param {number|null} copper - Value in copper
 * @returns {object} Formatted price parts or null
 */
export function formatPrice(copper) {
    if (copper === null || copper === undefined || isNaN(copper)) {
        return null
    }

    copper = Math.floor(copper)
    const gold = Math.floor(copper / 10000)
    const silver = Math.floor((copper % 10000) / 100)
    const copperRemainder = copper % 100

    return { gold, silver, copper: copperRemainder }
}

/**
 * Format price as string
 * @param {number|null} copper - Value in copper
 * @returns {string} Formatted string like "1,234g 56s 78c"
 */
export function formatPriceString(copper) {
    const price = formatPrice(copper)
    if (!price) return 'N/A'

    const parts = []
    if (price.gold > 0) parts.push(`${price.gold.toLocaleString()}g`)
    if (price.silver > 0) parts.push(`${price.silver}s`)
    if (price.copper > 0 || parts.length === 0) parts.push(`${price.copper}c`)

    return parts.join(' ')
}

/**
 * Format trend percentage
 * @param {number|null} trend - Trend percentage
 * @returns {object} { value, direction, icon }
 */
export function formatTrend(trend) {
    if (trend === null || trend === undefined || isNaN(trend)) {
        return { value: 'N/A', direction: 'stable', icon: '📊' }
    }

    if (trend > 5) {
        return { value: `+${trend.toFixed(1)}%`, direction: 'up', icon: '📈' }
    } else if (trend < -5) {
        return { value: `${trend.toFixed(1)}%`, direction: 'down', icon: '📉' }
    } else {
        return { value: `${trend.toFixed(1)}%`, direction: 'stable', icon: '➡️' }
    }
}

/**
 * Format volume change
 * @param {number|null} change - Volume change
 * @returns {string} Formatted string
 */
export function formatVolumeChange(change) {
    if (change === null || change === undefined || isNaN(change) || change === 0) {
        return 'N/A'
    }
    return change > 0 ? `+${change}` : `${change}`
}

/**
 * Format time difference to human readable
 * @param {string|Date|null} dateStr - ISO date string or Date object
 * @returns {string} Human readable time diff
 */
export function formatTimeDiff(dateStr) {
    if (!dateStr) return '-'

    try {
        const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr
        const now = new Date()
        const diffMs = now - date
        const diffSeconds = Math.floor(diffMs / 1000)

        if (diffSeconds < 60) return '< 1 min'
        if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} min`
        if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} h`
        return `${Math.floor(diffSeconds / 86400)} j`
    } catch {
        return '-'
    }
}

/**
 * Get flag URL for a region
 * @param {string} region - Region code
 * @returns {string} Flag CDN URL
 */
export function getFlagUrl(region) {
    const mapping = {
        'fr_FR': 'fr',
        'en_GB': 'gb',
        'de_DE': 'de',
        'es_ES': 'es',
        'it_IT': 'it',
        'pt_PT': 'pt',
        'ru_RU': 'ru',
        'ko_KR': 'kr',
        'zh_CN': 'cn',
        'zh_TW': 'tw',
    }
    const code = mapping[region] || 'eu'
    return `https://flagcdn.com/24x18/${code}.png`
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
    let timeout
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout)
            func(...args)
        }
        clearTimeout(timeout)
        timeout = setTimeout(later, wait)
    }
}
