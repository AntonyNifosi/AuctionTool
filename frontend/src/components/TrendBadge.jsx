import { formatTrend } from '../utils/formatters'

/**
 * Trend badge component with directional styling
 */
function TrendBadge({ value, showIcon = true }) {
    const trend = formatTrend(value)

    const className = {
        up: 'trend trend-up',
        down: 'trend trend-down',
        stable: 'trend trend-stable'
    }[trend.direction]

    return (
        <span className={className}>
            {showIcon && <span>{trend.icon}</span>}
            <span>{trend.value}</span>
        </span>
    )
}

export default TrendBadge
