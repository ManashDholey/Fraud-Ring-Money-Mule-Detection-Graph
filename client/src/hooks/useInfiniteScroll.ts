import { useEffect, useRef, useCallback } from 'react'

interface UseInfiniteScrollOptions {
  enabled: boolean
  threshold?: number
}

export function useInfiniteScroll(
  onIntersect: () => void,
  options: UseInfiniteScrollOptions = { enabled: true, threshold: 0.1 }
) {
  const sentinelRef = useRef<HTMLDivElement>(null)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const hasCalledRef = useRef(false)

  const onIntersectStable = useCallback(onIntersect, [onIntersect])

  useEffect(() => {
    if (!options.enabled) return

    const sentinel = sentinelRef.current
    if (!sentinel) return

    const handleIntersection = (entries: IntersectionObserverEntry[]) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && !hasCalledRef.current) {
          hasCalledRef.current = true
          onIntersectStable()
          // Reset after a frame to allow for the callback to update state and fetch more
          requestAnimationFrame(() => {
            hasCalledRef.current = false
          })
        }
      })
    }

    observerRef.current = new IntersectionObserver(handleIntersection, {
      threshold: options.threshold,
    })

    observerRef.current.observe(sentinel)

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [options.enabled, options.threshold, onIntersectStable])

  return { sentinelRef }
}
