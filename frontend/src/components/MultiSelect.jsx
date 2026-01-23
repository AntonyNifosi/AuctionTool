import React, { useState, useRef, useEffect } from 'react'

function MultiSelect({
    options,
    value = [],
    onChange,
    placeholder = "Sélectionner...",
    label = "Options"
}) {
    const [isOpen, setIsOpen] = useState(false)
    const dropdownRef = useRef(null)

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false)
            }
        }

        document.addEventListener('mousedown', handleClickOutside)
        return () => {
            document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [])

    const toggleOption = (option) => {
        const newValue = value.includes(option)
            ? value.filter(v => v !== option)
            : [...value, option]
        onChange(newValue)
    }

    const removeOption = (option, e) => {
        e.stopPropagation()
        onChange(value.filter(v => v !== option))
    }

    return (
        <div className="relative" ref={dropdownRef} style={{ position: 'relative', width: '100%' }}>
            {/* Input / Trigger */}
            <div
                className="input select-trigger"
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '4px',
                    minHeight: '42px',
                    paddingRight: '30px'
                }}
            >
                {value.length === 0 ? (
                    <span className="placeholder" style={{ color: 'var(--text-muted)' }}>{placeholder}</span>
                ) : (
                    value.map((v) => (
                        <span
                            key={v}
                            style={{
                                background: 'var(--bg-tertiary)',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                fontSize: '0.85rem',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                border: '1px solid var(--border-color)'
                            }}
                        >
                            {v}
                            <span
                                onClick={(e) => removeOption(v, e)}
                                style={{ cursor: 'pointer', fontWeight: 'bold', color: 'var(--text-muted)' }}
                            >
                                ×
                            </span>
                        </span>
                    ))
                )}

                {/* Arrow Icon */}
                <div style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M6 9l6 6 6-6" />
                    </svg>
                </div>
            </div>

            {/* Dropdown Menu */}
            {isOpen && (
                <div
                    className="dropdown-menu"
                    style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        backgroundColor: 'var(--bg-secondary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-md)',
                        marginTop: '4px',
                        maxHeight: '250px',
                        overflowY: 'auto',
                        zIndex: 100,
                        boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
                    }}
                >
                    {options.length === 0 ? (
                        <div style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>Aucun choix</div>
                    ) : (
                        options.map((option) => (
                            <div
                                key={option}
                                onClick={() => toggleOption(option)}
                                style={{
                                    padding: '8px 12px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    background: value.includes(option) ? 'var(--bg-tertiary)' : 'transparent',
                                    borderBottom: '1px solid var(--border-color)'
                                }}
                                onMouseEnter={(e) => {
                                    if (!value.includes(option)) e.currentTarget.style.background = 'var(--bg-tertiary)'
                                }}
                                onMouseLeave={(e) => {
                                    if (!value.includes(option)) e.currentTarget.style.background = 'transparent'
                                }}
                            >
                                <input
                                    type="checkbox"
                                    checked={value.includes(option)}
                                    readOnly
                                    style={{ pointerEvents: 'none' }}
                                />
                                <span>{option}</span>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}

export default MultiSelect
