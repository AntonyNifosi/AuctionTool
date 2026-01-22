import {
    LineChart, Line, AreaChart, Area, ComposedChart,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'

export function PriceChart({ data, styles }) {
    if (!data || data.length === 0) {
        return <p className="text-muted">Aucun historique disponible</p>
    }

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className={styles.customChartTooltip}>
                    <p className={styles.tooltipDate}>{label}</p>
                    {payload.map((p, i) => (
                        <p key={i} style={{ color: p.color, margin: 0 }}>
                            {p.name}: {
                                p.dataKey === 'min_price' || p.dataKey === 'avg_price'
                                    ? `${p.value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}g`
                                    : p.value.toLocaleString()
                            }
                        </p>
                    ))}
                </div>
            )
        }
        return null
    }

    return (
        <div style={{ width: '100%', height: 400 }}>
            <ResponsiveContainer>
                <LineChart
                    data={data}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                >
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis
                        dataKey="dateLabel"
                        stroke="#888"
                        tick={{ fontSize: 10 }}
                        interval="preserveStartEnd"
                    />
                    <YAxis
                        stroke="#888"
                        tickFormatter={(value) => {
                            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
                            if (value >= 1000) return `${(value / 1000).toFixed(0)}k`
                            return value
                        }}
                        width={40}
                        tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                        content={<CustomTooltip />}
                        cursor={{ stroke: '#666', strokeDasharray: '3 3' }}
                    />
                    <Legend />
                    <Line
                        type="monotone"
                        dataKey="min_price"
                        name="Prix Min"
                        stroke="#00ff00"
                        strokeWidth={2}
                        dot={{ r: 4, fill: '#00ff00' }}
                        activeDot={{ r: 8, fill: '#00ff00', stroke: '#fff', strokeWidth: 2 }}
                        connectNulls
                    />
                    <Line
                        type="monotone"
                        dataKey="avg_price"
                        name="Prix Moyen"
                        stroke="#FFD100"
                        strokeWidth={2}
                        dot={{ r: 4, fill: '#FFD100' }}
                        activeDot={{ r: 8, fill: '#FFD100', stroke: '#fff', strokeWidth: 2 }}
                        connectNulls
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    )
}

export function VolumeChart({ data, styles }) {
    if (!data || data.length === 0) {
        return <p className="text-muted">Aucune donnée de volume disponible</p>
    }

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className={styles.customChartTooltip}>
                    <p className={styles.tooltipDate}>{label}</p>
                    {payload.map((p, i) => (
                        <p key={i} style={{ color: p.color, margin: 0 }}>
                            {p.name}: {p.value.toLocaleString()}
                        </p>
                    ))}
                </div>
            )
        }
        return null
    }

    return (
        <div style={{ width: '100%', height: 400 }}>
            <ResponsiveContainer>
                <ComposedChart
                    data={data}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                >
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis
                        dataKey="dateLabel"
                        stroke="#888"
                        tick={{ fontSize: 10 }}
                        interval="preserveStartEnd"
                    />
                    <YAxis
                        stroke="#888"
                        tickFormatter={(value) => {
                            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
                            if (value >= 1000) return `${(value / 1000).toFixed(0)}k`
                            return value
                        }}
                        width={40}
                        tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                        content={<CustomTooltip />}
                        cursor={{ stroke: '#666', strokeDasharray: '3 3' }}
                    />
                    <Legend />
                    <Area
                        type="monotone"
                        dataKey="quantity"
                        name="Quantité totale"
                        fill="#4CAF50"
                        stroke="#4CAF50"
                        fillOpacity={0.3}
                        dot={{ r: 4, fill: '#4CAF50' }}
                        activeDot={{ r: 8, fill: '#4CAF50', stroke: '#fff', strokeWidth: 2 }}
                    />
                    <Line
                        type="monotone"
                        dataKey="auctions"
                        name="Nombre d'enchères"
                        stroke="#FF9800"
                        strokeDasharray="5 5"
                        strokeWidth={2}
                        dot={{ r: 4, fill: '#FF9800' }}
                        activeDot={{ r: 8, fill: '#FF9800', stroke: '#fff', strokeWidth: 2 }}
                    />
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    )
}
