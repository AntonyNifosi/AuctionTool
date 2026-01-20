import { formatPrice } from '../utils/formatters'

// WoW coin icons from Wowhead CDN
const GOLD_ICON = 'https://wow.zamimg.com/images/icons/money-gold.gif'
const SILVER_ICON = 'https://wow.zamimg.com/images/icons/money-silver.gif'
const COPPER_ICON = 'https://wow.zamimg.com/images/icons/money-copper.gif'

const coinStyle = {
    width: 14, // Slightly larger for better visibility
    height: 14,
    marginLeft: 2,
    marginRight: 4,
    verticalAlign: 'middle',
    transform: 'translateY(-1px)' // Optical alignment
}

const groupStyle = {
    whiteSpace: 'nowrap',
    display: 'inline-flex',
    alignItems: 'center'
}

/**
 * Price display component with gold/silver/copper coin icons
 */
function PriceDisplay({ value, className = '' }) {
    const price = formatPrice(value)

    if (!price) {
        return <span className={`price price-na ${className}`}>N/A</span>
    }

    // Main container uses flex-wrap to allow breaking ONLY between currency groups
    // but keeps number+icon glued together via groupStyle
    return (
        <span className={`price ${className}`} style={{ display: 'inline-flex', flexWrap: 'wrap', alignItems: 'center', gap: '2px' }}>
            {price.gold > 0 && (
                <span className="price-gold" style={groupStyle}>
                    {price.gold.toLocaleString()}
                    <img src={GOLD_ICON} alt="g" style={coinStyle} />
                </span>
            )}
            {price.silver > 0 && (
                <span className="price-silver" style={groupStyle}>
                    {price.silver}
                    <img src={SILVER_ICON} alt="s" style={coinStyle} />
                </span>
            )}
            {(price.copper > 0 || (price.gold === 0 && price.silver === 0)) && (
                <span className="price-copper" style={groupStyle}>
                    {price.copper}
                    <img src={COPPER_ICON} alt="c" style={coinStyle} />
                </span>
            )}
        </span>
    )
}

export default PriceDisplay
