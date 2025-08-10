type SkeletonProps = {
  width?: number | string
  height?: number | string
  className?: string
  radius?: number | string
  'aria-label'?: string
}

export function Skeleton({ width = '100%', height = 14, className = '', radius = 6, ...rest }: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius: radius }}
      aria-hidden
      {...rest}
    />
  )
}

export function SkeletonLines({ count = 6, lineHeight = 14, gap = 8 }: { count?: number; lineHeight?: number; gap?: number }) {
  return (
    <div role="status" aria-live="polite" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ marginBottom: i === count - 1 ? 0 : gap }}>
          <Skeleton height={lineHeight} width={`${80 + Math.random() * 20}%`} />
        </div>
      ))}
    </div>
  )
}

export default Skeleton

