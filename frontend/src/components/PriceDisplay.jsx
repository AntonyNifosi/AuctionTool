import { formatPrice } from '../utils/formatters'

// WoW coin icons from Wowhead CDN
const GOLD_ICON = 'https://wow.zamimg.com/images/icons/money-gold.gif'
const SILVER_ICON = 'https://wow.zamimg.com/images/icons/money-silver.gif'
const COPPER_ICON = 'https://wow.zamimg.com/images/icons/money-copper.gif'

const coinStyle = {
    width: 12,
    height: 12,
    marginLeft: 1,
    marginRight: 3,
    verticalAlign: 'middle'
}

/**
 * Price display component with gold/silver/copper coin icons
 */
function PriceDisplay({ value, className = '' }) {
    const price = formatPrice(value)

    if (!price) {
        return <span className={`price price-na ${className}`}>N/A</span>
    }

    return (
        <span className={`price ${className}`}>
            {price.gold > 0 && (
                <span className="price-gold">
                    {price.gold.toLocaleString()}
                    <img src={GOLD_ICON} alt="g" style={coinStyle} />
                </span>
            )}
            {price.silver > 0 && (
                <span className="price-silver">
                    {price.silver}
                    <img src={SILVER_ICON} alt="s" style={coinStyle} />
                </span>
            )}
            {(price.copper > 0 || (price.gold === 0 && price.silver === 0)) && (
                <span className="price-copper">
                    {price.copper}
                    <img src={COPPER_ICON} alt="c" style={coinStyle} />
                </span>
            )}
        </span>
    )
}

export default PriceDisplay
