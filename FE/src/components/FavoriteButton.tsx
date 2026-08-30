import { Star } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { addFavorite, removeFavorite } from '../api/bookmarks'
import { useAuthStore } from '../store/useAuthStore'

// 명소 카드 썸네일 위에 얹는 즐겨찾기 별 버튼.
// 목록 API(추천/Top10)가 즐겨찾기 여부를 안 줘서, 처음엔 항상 빈 별로 시작한다
// (실제로 이미 즐겨찾기한 명소여도 목록에선 그렇게 보일 수 있음 — BE 응답에 필드 추가되면 고칠 것).
export function FavoriteButton({ placeId }: { placeId: number }) {
  const navigate = useNavigate()
  const member = useAuthStore((state) => state.member)
  const [isFavorited, setIsFavorited] = useState(false)
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
    const request = next ? addFavorite(placeId) : removeFavorite(placeId)
    request
      .catch(() => setIsFavorited(!next))
      .finally(() => setPending(false))
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label="즐겨찾기"
      className="absolute right-1 top-1 rounded-full p-1"
    >
      <Star size={16} className={isFavorited ? 'fill-primary text-primary' : 'text-primary'} />
    </button>
  )
}
