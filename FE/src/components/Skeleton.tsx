type SkeletonProps = {
  className?: string
}

// 데이터 로딩 중에 보여주는 회색 깜빡임 블록. 크기는 className으로 지정한다.
export function Skeleton({ className = '' }: SkeletonProps) {
  return <div className={`animate-pulse rounded-md bg-divider ${className}`} />
}
