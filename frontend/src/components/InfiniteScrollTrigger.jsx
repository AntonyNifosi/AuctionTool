import { useEffect, useRef } from 'react'

export default function InfiniteScrollTrigger({ onIntersect, enabled = true, rootMargin = '100px' }) {
    const triggerRef = useRef(null)

    useEffect(() => {
        if (!enabled) return

        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    onIntersect()
                }
            },
            {
                root: null,
                rootMargin,
                threshold: 0.1
            }
        )

        const currentTrigger = triggerRef.current
        if (currentTrigger) {
            observer.observe(currentTrigger)
        }

        return () => {
            if (currentTrigger) {
                observer.unobserve(currentTrigger)
            }
        }
    }, [onIntersect, enabled, rootMargin])

    return <div ref={triggerRef} className="infinite-scroll-trigger" style={{ height: '20px', width: '100%' }} />
}
