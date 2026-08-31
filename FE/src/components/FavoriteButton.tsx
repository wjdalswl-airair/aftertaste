import { Star } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { addCourseFavorite, addFavorite, removeCourseFavorite, removeFavorite } from '../api/bookmarks'
import { useAuthStore } from '../store/useAuthStore'

type FavoriteButtonProps = {
  placeId: number
  // 'course'면 placeId를 코스 id로 넘긴다 (명소/코스 즐겨찾기 API가 서로 달라서 여기서 갈라준다).
  type?: 'place' | 'course'
  // 목록 API(추천/Top10)는 즐겨찾기 여부를 안 줘서 기본값은 항상 빈 별이다.
  // 명소 상세처럼 실제 값(is_favorited)을 아는 화면에서만 넘겨준다.
  initialFavorited?: boolean
  size?: number
  className?: string
}

// 명소·코스 카드/상세 화면에 얹는 즐겨찾기 별 버튼.
export function FavoriteButton({
  placeId,
  type = 'place',
  initialFavorited = false,
  size = 16,
  className = 'absolute right-1 top-1 rounded-full p-1',
}: FavoriteButtonProps) {
  const navigate = useNavigate()
  const member = useAuthStore((state) => state.member)
  const [isFavorited, setIsFavorited] = useState(initialFavorited)
  const [pending, setPending] = useState(false)

  function handleClick(event: React.MouseEvent) {
    event.preventDefault()
    event.stopPropagation()

    if (!member) {
      navigate('/login', { state: { message: '로그인이 필요한 기능입니다' } })
      return
    }
    if (pending) {
      return
    }

    setPending(true)
    const next = !isFavorited
    setIsFavorited(next)
    const add = type === 'course' ? addCourseFavorite : addFavorite
    const remove = type === 'course' ? removeCourseFavorite : removeFavorite
    const request = next ? add(placeId) : remove(placeId)
    request
      .catch(() => setIsFavorited(!next))
      .finally(() => setPending(false))
  }

  return (
    <button type="button" onClick={handleClick} aria-label="즐겨찾기" className={className}>
      <Star size={size} className={isFavorited ? 'fill-primary text-primary' : 'text-primary'} />
    </button>
  )
}
