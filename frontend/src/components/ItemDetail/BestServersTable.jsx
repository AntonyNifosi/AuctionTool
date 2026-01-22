import PriceDisplay from '../PriceDisplay'

export function BestServersTable({ bestServers }) {
    if (bestServers.length === 0) {
        return <p className="text-muted">Aucune donnée disponible</p>
    }

    const topServers = bestServers.slice(0, 10)

    return (
        <>
            {/* Desktop Table */}
            <div className="table-container" style={{ maxHeight: '500px' }}>
                <table className="table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Serveur</th>
                            <th>Prix</th>
                            <th>Volume Δ</th>
                            <th>Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {topServers.map((server, i) => (
                            <tr key={server.realm_name || i}>
                                <td>
                                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                                </td>
                                <td>{server.realm_name}</td>
                                <td><PriceDisplay value={server.min_price} /></td>
                                <td className={(server.volume ?? server.volume_exchanged) > 0 ? 'text-success' : (server.volume ?? server.volume_exchanged) < 0 ? 'text-danger' : ''}>
                                    {(server.volume ?? server.volume_exchanged) != null ? ((server.volume ?? server.volume_exchanged) > 0 ? `+${(server.volume ?? server.volume_exchanged)}` : (server.volume ?? server.volume_exchanged)) : 'N/A'}
                                </td>
                                <td>
                                    <span className={`score-badge ${server.score >= 70 ? 'score-high' : server.score >= 40 ? 'score-medium' : 'score-low'}`}>
                                        {server.score > 0 ? `${Math.round(server.score)}%` : '⚠'}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Mobile List View */}
            <div className="mobile-modal-grid">
                {topServers.map((server, i) => (
                    <div className="mobile-list-item" key={server.realm_name || i}>
                        <div className="mobile-list-header">
                            <div className="realm-info">
                                <span className="rank-emoji">
                                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}
                                </span>
                                <span className="realm-name">{server.realm_name}</span>
                            </div>
                            <span className={`score-badge ${server.score >= 70 ? 'score-high' : server.score >= 40 ? 'score-medium' : 'score-low'}`}>
                                {server.score > 0 ? `${Math.round(server.score)}%` : '⚠'}
                            </span>
                        </div>
                        <div className="mobile-list-row">
                            <PriceDisplay value={server.min_price} />
                            <span className={(server.volume ?? server.volume_exchanged) > 0 ? 'text-success' : (server.volume ?? server.volume_exchanged) < 0 ? 'text-danger' : ''}>
                                Vol: {(server.volume ?? server.volume_exchanged) != null ? ((server.volume ?? server.volume_exchanged) > 0 ? `+${(server.volume ?? server.volume_exchanged)}` : (server.volume ?? server.volume_exchanged)) : 'N/A'}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </>
    )
}
