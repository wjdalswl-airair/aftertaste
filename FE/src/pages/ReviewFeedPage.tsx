import { Heart, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { getReviewFeed, type ReviewFeedOrdering, type ReviewItem } from '../api/reviews'
import { BottomNav } from '../components/BottomNav'
import { Skeleton } from '../components/Skeleton'

export function ReviewFeedPage() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  // 리뷰 상세의 작품 해시태그를 눌러 들어오면 work_id로 "이 작품 리뷰만 보기" 필터가 걸린다
  // (issue #60 서버 필터, DETAIL_SPEC.md S-07 참고). work_title은 필터 칩에 보여줄 이름표일 뿐,
  // 실제 필터링은 work_id로 한다.
  const workIdParam = searchParams.get('work_id')
  const workId = workIdParam ? Number(workIdParam) : undefined
  const workTitle = searchParams.get('work_title') ?? ''

  const [ordering, setOrdering] = useState<ReviewFeedOrdering>('latest')
  // 촬영지(place_name)와 태그된 작품(works[].title) 둘 다로 검색한다(작품 태그는 issue #60로
  // ReviewSerializer에 추가됨). BE 파라미터 없이 이미 불러온 리뷰를 FE에서 걸러 보여준다 —
  // 그래서 아직 안 불러온 뒷 페이지의 리뷰는 "더보기"로 더 불러와야 검색 대상에 들어온다.
  const [searchQuery, setSearchQuery] = useState('')
  // undefined: 로딩 중, []: 확인 끝났는데 리뷰 없음
  const [reviews, setReviews] = useState<ReviewItem[] | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    setReviews(undefined)
    getReviewFeed({ ordering, page: 1, workId })
      .then((result) => {
        setReviews(result.reviews)
        setHasMore(result.next !== null)
        setPage(1)
      })
      .catch(() => {
        setReviews([])
        setHasMore(false)
      })
  }, [ordering, workId])

  function handleLoadMore() {
    setLoadingMore(true)
    const nextPage = page + 1
    getReviewFeed({ ordering, page: nextPage, workId })
      .then((result) => {
        setReviews((prev) => [...(prev ?? []), ...result.reviews])
        setHasMore(result.next !== null)
        setPage(nextPage)
      })
      .catch(() => setHasMore(false))
      .finally(() => setLoadingMore(false))
  }

  function handleClearWorkFilter() {
    setSearchParams({})
  }

  const normalizedQuery = searchQuery.trim().toLowerCase()
  const visibleReviews = reviews?.filter(
    (review) =>
      normalizedQuery === '' ||
      review.place_name.toLowerCase().includes(normalizedQuery) ||
      review.works.some((work) => work.title.toLowerCase().includes(normalizedQuery)),
  )

  return (
    <main className="flex min-h-dvh flex-col gap-4 pb-24">
      <header className="grid grid-cols-[1fr_auto_1fr] items-center px-4 pt-4">
        <Link to="/" className="font-brand text-2xl font-bold text-primary">여운</Link>
        <h1 className="text-lg font-bold text-ink">{t('reviewFeedPage.title')}</h1>
        <div />
      </header>

      <div className="px-4 pb-2">
        {workId ? (
          <div className="flex items-center gap-2 rounded-lg bg-accent/15 p-4">
            <span className="flex-1 truncate text-sm font-bold text-ink">
              {t('reviewFeedPage.workFilterLabel', { title: workTitle })}
            </span>
            <button type="button" onClick={handleClearWorkFilter} aria-label={t('reviewFeedPage.workFilterClear')}>
              <X size={16} className="text-ink-tertiary" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 rounded-lg bg-accent/15 p-4">
            <Search size={16} className="text-ink-tertiary" />
            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder={t('reviewFeedPage.searchPlaceholder')}
              className="flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-tertiary"
            />
          </div>
        )}
      </div>

      <div className="flex gap-6 px-4">
        {(['latest', 'popular'] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setOrdering(option)}
            className={`pb-2 text-sm ${
              ordering === option ? 'border-b-2 border-primary font-bold text-ink' : 'text-ink-tertiary'
            }`}
          >
            {option === 'latest' ? t('reviewFeedPage.sortLatest') : t('reviewFeedPage.sortPopular')}
          </button>
        ))}
      </div>

      {visibleReviews === undefined ? (
        <ReviewFeedSkeleton />
      ) : visibleReviews.length > 0 ? (
        <div className="px-4">
          {/* 핀터레스트식 매스너리: 짝/홀 인덱스로 리뷰를 두 칸에 미리 나눠서 각자 세로로 쌓는다.
              CSS columns-2(다단 레이아웃)로도 같은 모양을 만들 수 있지만, 그건 전체 높이를 다시
              계산해 재배치하는 방식이라 "더보기"로 리뷰가 늘어날 때마다 이미 보이던 카드까지
              흔들린다. 인덱스로 칸을 고정하면 새 리뷰는 항상 두 칸 중 하나의 끝에만 추가돼서
              기존 카드는 절대 안 움직인다 — 사진이 계속 늘어날 예정이라 이 안정성이 중요하다. */}
          <div className="flex gap-4">
            {[0, 1].map((columnIndex) => (
              <div key={columnIndex} className="flex flex-1 flex-col gap-4">
                {visibleReviews
                  .filter((_, index) => index % 2 === columnIndex)
                  .map((review) => (
                    <ReviewFeedCard key={review.id} review={review} />
                  ))}
              </div>
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
        <p className="px-4 py-20 text-center text-sm text-ink-tertiary">
          {normalizedQuery === '' ? t('reviewFeedPage.empty') : t('reviewFeedPage.searchEmpty')}
        </p>
      )}

      <BottomNav />
    </main>
  )
}

function ReviewFeedCard({ review }: { review: ReviewItem }) {
  return (
    <Link
      to={`/spots/${review.place}/reviews/${review.id}`}
      className="relative block overflow-hidden rounded-md bg-divider"
    >
      <img
        src={review.photos[0]?.photo_url ?? review.place_photo_url}
        alt=""
        loading="lazy"
        className="block h-auto w-full object-cover"
      />
      <div className="absolute bottom-2 right-2 flex items-center gap-1 rounded-full bg-black/40 px-1.5 py-0.5">
        <Heart size={12} className={`text-white ${review.is_liked_by_me ? 'fill-white' : ''}`} />
        <span className="text-[10px] font-medium text-white">{review.like_count}</span>
      </div>
    </Link>
  )
}

const SKELETON_COLUMN_HEIGHTS = [
  ['h-40', 'h-56', 'h-32'],
  ['h-48', 'h-32', 'h-52'],
]

function ReviewFeedSkeleton() {
  return (
    <div className="flex gap-4 px-4">
      {SKELETON_COLUMN_HEIGHTS.map((heights, columnIndex) => (
        <div key={columnIndex} className="flex flex-1 flex-col gap-4">
          {heights.map((height, i) => (
            <Skeleton key={i} className={`block w-full rounded-md ${height}`} />
          ))}
        </div>
      ))}
    </div>
  )
}
