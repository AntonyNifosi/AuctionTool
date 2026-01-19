import { formatPrice } from '../utils/formatters'

/**
 * Price display component with gold/silver/copper formatting
 */
function PriceDisplay({ value, className = '' }) {
    const price = formatPrice(value)

    if (!price) {
        return <span className={`price price-na ${className}`}>N/A</span>
    }

    return (
        <span className={`price ${className}`}>
            {price.gold > 0 && (
                <span className="price-gold">{price.gold.toLocaleString()}g</span>
            )}
            {price.silver > 0 && (
                <span className="price-silver">{price.silver}s</span>
            )}
            {(price.copper > 0 || (price.gold === 0 && price.silver === 0)) && (
                <span className="price-copper">{price.copper}c</span>
            )}
        </span>
    )
}

export default PriceDisplay
