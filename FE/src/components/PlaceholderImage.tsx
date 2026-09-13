type PlaceholderImageProps = {
  // 실제 사진 URL. 빈 문자열/undefined/null이면 placeholder를 대신 보여준다.
  src: string | null | undefined
  placeholder: string
  alt: string
  // 박스 크기(h-/w-/aspect-/rounded- 등)만 넣는다 — object-fit은 이 컴포넌트가 정한다.
  className: string
  loading?: 'lazy' | 'eager'
}

// 명소·작품 썸네일 공용 컴포넌트. 실제 사진은 object-cover로 박스를 꽉 채우고, 사진이 없어서
// placeholder로 대신 보여줄 때는 object-contain으로 바꾼다 — placeholder 일러스트(work.png 2:3,
// spot.png 3:2)의 원본 비율이 실제 쓰이는 박스마다 다 달라서, object-cover를 그대로 쓰면
// 위치마다 좌우·상하가 잘려 보이기 때문이다(2026-09-13, 명소 상세에서 발견).
export function PlaceholderImage({ src, placeholder, alt, className, loading }: PlaceholderImageProps) {
  const hasPhoto = Boolean(src)
  return (
    <img
      src={hasPhoto ? (src as string) : placeholder}
      alt={alt}
      loading={loading}
      className={`${className} ${hasPhoto ? 'object-cover' : 'bg-accent/15 object-contain'}`}
    />
  )
}
