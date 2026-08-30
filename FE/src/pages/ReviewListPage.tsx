import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getPlaceReviews, type ReviewItem } from '../api/reviews'
import { getPlaceDetail, type PlaceDetail } from '../api/spots'
import { BottomNav } from '../components/BottomNav'
import { Skeleton } from '../components/Skeleton'

type SortOrder = 'latest' | 'popular'

export function ReviewListPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { placeId } = useParams<{ placeId: string }>()

  const [place, setPlace] = useState<PlaceDetail | undefined>(undefined)
  const [reviews, setReviews] = useState<ReviewItem[] | undefined>(undefined)
  const [sort, setSort] = useState<SortOrder>('latest')

  useEffect(() => {
    getPlaceDetail(Number(placeId))
      .then(setPlace)
      .catch(() => setPlace(undefined))
    getPlaceReviews(Number(placeId))
      .then(setReviews)
      .catch(() => setReviews([]))
  }, [placeId])

  const sorted = reviews
    ? [...reviews].sort((a, b) =>
        sort === 'popular'
          ? b.like_count - a.like_count
          : new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      )
    : undefined

  return (
    <main className="flex min-h-dvh flex-col gap-4 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-6">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <p className="truncate text-center text-lg font-medium text-ink">
          {place?.name ?? ''}
          {reviews && <span className="ml-1.5 text-xs font-normal text-ink-tertiary">{reviews.length}개</span>}
        </p>
      </header>

      <div className="flex gap-6 border-b border-divider px-4">
        {(['latest', 'popular'] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setSort(option)}
            className={`pb-2 text-base ${
              sort === option ? 'border-b-2 border-primary font-bold text-ink' : 'text-ink-tertiary'
            }`}
          >
            {option === 'latest' ? t('reviewList.sortLatest') : t('reviewList.sortPopular')}
          </button>
        ))}
      </div>

      <div className="px-4">
        {sorted === undefined ? (
          <div className="grid grid-cols-3 gap-2">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="aspect-square rounded-none" />
            ))}
          </div>
        ) : sorted.length > 0 ? (
          <div className="grid grid-cols-3 gap-2">
            {sorted.map((review) => (
              <Link
                key={review.id}
                to={`/spots/${placeId}/reviews/${review.id}`}
                className="relative aspect-square overflow-hidden rounded-none bg-divider"
              >
                {review.photos[0] && (
                  <img src={review.photos[0].photo_url} alt="" className="h-full w-full object-cover" />
                )}
              </Link>
            ))}
          </div>
        ) : (
          <p className="py-10 text-center text-sm text-ink-tertiary">{t('reviewList.empty')}</p>
        )}
      </div>

      <BottomNav />
    </main>
  )
}
