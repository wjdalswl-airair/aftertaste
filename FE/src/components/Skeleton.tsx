type SkeletonProps = {
  className?: string
}

// 데이터 로딩 중에 보여주는 회색 깜빡임 블록.
// 크기·radius는 className으로 지정한다 (실제 콘텐츠와 모양이 달라지면 로딩 후 박스 크기가 튀어 보인다 — rounded-* 꼭 맞춰줄 것).
export function Skeleton({ className = '' }: SkeletonProps) {
  return <div className={`animate-pulse bg-divider ${className}`} />
}
