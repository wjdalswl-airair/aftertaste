import { Heart } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getReviewFeed, type ReviewFeedOrdering, type ReviewItem } from '../api/reviews'
import { BottomNav } from '../components/BottomNav'
import { LanguageSheet } from '../components/LanguageSheet'
import { Skeleton } from '../components/Skeleton'

export function ReviewFeedPage() {
  const { t } = useTranslation()
  const [ordering, setOrdering] = useState<ReviewFeedOrdering>('latest')
  // undefined: 로딩 중, []: 확인 끝났는데 리뷰 없음
  const [reviews, setReviews] = useState<ReviewItem[] | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    setReviews(undefined)
    getReviewFeed({ ordering, page: 1 })
      .then((result) => {
        setReviews(result.reviews)
        setHasMore(result.next !== null)
        setPage(1)
      })
      .catch(() => {
        setReviews([])
        setHasMore(false)
      })
  }, [ordering])

  function handleLoadMore() {
    setLoadingMore(true)
    const nextPage = page + 1
    getReviewFeed({ ordering, page: nextPage })
      .then((result) => {
        setReviews((prev) => [...(prev ?? []), ...result.reviews])
        setHasMore(result.next !== null)
        setPage(nextPage)
      })
      .catch(() => setHasMore(false))
      .finally(() => setLoadingMore(false))
  }

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="flex items-center justify-between px-4 pt-4">
        <Link to="/" className="font-brand text-2xl font-bold text-primary">여운</Link>
        <h1 className="text-lg font-bold text-ink">{t('reviewFeedPage.title')}</h1>
        <LanguageSheet />
      </header>

      <div className="flex gap-6 px-4">
        {(['latest', 'popular'] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setOrdering(option)}
            className={`pb-2 text-base ${
              ordering === option ? 'border-b-2 border-primary font-bold text-ink' : 'text-ink-tertiary'
            }`}
          >
            {option === 'latest' ? t('reviewFeedPage.sortLatest') : t('reviewFeedPage.sortPopular')}
          </button>
        ))}
      </div>

      {reviews === undefined ? (
        <ReviewFeedSkeleton />
      ) : reviews.length > 0 ? (
        <div className="px-4">
          <div className="grid grid-cols-3 gap-2">
            {reviews.map((review) => (
              <Link
                key={review.id}
                to={`/spots/${review.place}/reviews/${review.id}`}
                className="relative aspect-square overflow-hidden rounded-none bg-divider"
              >
                <img
                  src={review.photos[0]?.photo_url ?? review.place_photo_url}
                  alt=""
                  className="h-full w-full object-cover"
                />
                <div className="absolute right-1 top-1 flex items-center gap-0.5 rounded-full bg-accent px-1.5 py-0.5">
                  <Heart size={12} className={`text-white ${review.is_liked_by_me ? 'fill-white' : ''}`} />
                  <span className="text-[10px] font-medium text-white">{review.like_count}</span>
                </div>
              </Link>
            ))}
          </div>

          {hasMore && (
            <button
              type="button"
              onClick={handleLoadMore}
              disabled={loadingMore}
              className="mx-auto my-4 block rounded-full border border-divider px-6 py-2 text-sm text-ink-secondary disabled:opacity-50"
            >
              {loadingMore ? t('reviewFeedPage.loadingMore') : t('reviewFeedPage.loadMore')}
            </button>
          )}
        </div>
      ) : (
        <p className="px-4 py-20 text-center text-sm text-ink-tertiary">{t('reviewFeedPage.empty')}</p>
      )}

      <BottomNav />
    </main>
  )
}

function ReviewFeedSkeleton() {
  return (
    <div className="grid grid-cols-3 gap-2 px-4">
      {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <Skeleton key={i} className="aspect-square rounded-none" />
      ))}
    </div>
  )
}
