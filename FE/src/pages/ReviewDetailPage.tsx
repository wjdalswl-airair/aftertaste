import { ArrowLeft, Heart, MoreHorizontal } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { deleteReview, getPlaceReviews, likeReview, reportReview, unlikeReview, type ReviewItem } from '../api/reviews'
import { getPlaceDetail, type PlaceDetail } from '../api/spots'
import { BottomNav } from '../components/BottomNav'
import { Skeleton } from '../components/Skeleton'
import { useAuthStore } from '../store/useAuthStore'

export function ReviewDetailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { placeId, reviewId } = useParams<{ placeId: string; reviewId: string }>()
  const member = useAuthStore((state) => state.member)

  // undefined: 로딩 중, null: 못 찾음
  const [review, setReview] = useState<ReviewItem | null | undefined>(undefined)
  const [place, setPlace] = useState<PlaceDetail | undefined>(undefined)
  const [reviewCount, setReviewCount] = useState<number | undefined>(undefined)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    getPlaceDetail(Number(placeId))
      .then(setPlace)
      .catch(() => setPlace(undefined))
    getPlaceReviews(Number(placeId))
      .then((reviews) => {
        setReviewCount(reviews.length)
        setReview(reviews.find((item) => item.id === Number(reviewId)) ?? null)
      })
      .catch(() => setReview(null))
  }, [placeId, reviewId])

  function handleToggleLike() {
    if (!review) {
      return
    }
    if (!member) {
      navigate('/login', { state: { message: '로그인이 필요한 기능입니다' } })
      return
    }
    const next = !review.is_liked_by_me
    setReview({ ...review, is_liked_by_me: next, like_count: review.like_count + (next ? 1 : -1) })
    const request = next ? likeReview(review.id) : unlikeReview(review.id)
    request.catch(() => {
      setReview((current) =>
        current ? { ...current, is_liked_by_me: !next, like_count: current.like_count + (next ? -1 : 1) } : current,
      )
    })
  }

  async function handleDelete() {
    if (!review) {
      return
    }
    await deleteReview(review.id).catch(() => {})
    navigate(`/spots/${placeId}/reviews`, { replace: true })
  }

  function handleReport() {
    if (!review) {
      return
    }
    setMenuOpen(false)
    reportReview(review.id).catch(() => {})
  }

  function handleOpenMenu() {
    if (!member) {
      navigate('/login', { state: { message: '로그인이 필요한 기능입니다' } })
      return
    }
    setMenuOpen(true)
  }

  // BE 응답에 "내가 쓴 글인지" 여부가 없어서(is_mine 같은 필드 없음), 닉네임 비교로 임시 판단한다.
  // 닉네임이 겹치면 오작동할 수 있어 정확한 방법은 아니다 (docs/DETAIL_SPEC.md S-07 참고).
  const isMine = Boolean(member && review && member.nickname === review.author_nickname)

  return (
    <main className="flex min-h-dvh flex-col pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-6">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <p className="truncate text-center text-lg font-medium text-ink">
          {place?.name}
          {reviewCount !== undefined && (
            <span className="ml-1.5 text-xs font-normal text-ink-tertiary">{reviewCount}개</span>
          )}
        </p>
      </header>

      {review === undefined && (
        <div className="mt-6 flex flex-col gap-4">
          <div className="flex items-center gap-3 px-4 py-3">
            <Skeleton className="h-[38px] w-[38px] rounded-full" />
            <Skeleton className="h-3 w-20 rounded-sm" />
          </div>

          <Skeleton className="h-[280px] w-full rounded-none" />

          <div className="flex items-center justify-between px-4">
            <div className="flex items-center gap-2">
              <Skeleton className="h-[18px] w-[18px] rounded-sm" />
              <Skeleton className="h-4 w-6 rounded-sm" />
            </div>
            <Skeleton className="h-3 w-24 rounded-sm" />
          </div>

          <div className="flex flex-col gap-2 px-4">
            <Skeleton className="h-4 w-full rounded-sm" />
            <Skeleton className="h-4 w-2/3 rounded-sm" />
          </div>
        </div>
      )}

      {review === null && (
        <p className="px-4 py-20 text-center text-ink-tertiary">{t('reviewDetail.notFound')}</p>
      )}

      {review && (
        <div className="mt-6 flex flex-col gap-4">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="h-[40px] w-[40px] rounded-full bg-divider" />
              <p className="font-medium text-ink">{review.author_nickname}</p>
            </div>
            <button type="button" onClick={handleOpenMenu} aria-label="더보기">
              <MoreHorizontal size={22} className="text-ink" />
            </button>
          </div>

          {review.photos[0] ? (
            <img src={review.photos[0].photo_url} alt="" className="h-[280px] w-full object-cover" />
          ) : (
            // 사진이 없을 때 보여줄 기본 샘플 이미지 — 파일 정해지면 여기에 넣는다. 지금은 빈 박스.
            <div className="h-[280px] w-full bg-divider" />
          )}

          <div className="flex items-end justify-between px-4">
            <div className="flex items-end gap-2">
              <button type="button" onClick={handleToggleLike} aria-label="좋아요">
                <Heart size={24} className={`block text-primary ${review.is_liked_by_me ? 'fill-primary' : ''}`} />
              </button>
              <p className="text-sm font-medium text-ink">{review.like_count}</p>
            </div>
            <div className="flex gap-3 text-sm text-ink-tertiary">
              <span>{formatReviewDate(review.created_at)}</span>
              <span>{formatReviewTime(review.created_at)}</span>
            </div>
          </div>

          <p className="px-4 text-base font-medium leading-[1.5] text-ink">{review.content}</p>
       </div>
      )}

      {menuOpen && review && (
        <div className="fixed inset-0 z-50 mx-auto w-full max-w-[480px]">
          <button
            type="button"
            aria-label="닫기"
            className="absolute inset-0 bg-black/40"
            onClick={() => setMenuOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 flex flex-col">
            <div className="w-full animate-[sheet-up_0.2s_ease-out] rounded-t-2xl bg-white pb-8 pt-2">
              <div className="mx-auto mt-1.5 h-[3px] w-[46px] rounded-full bg-divider" />
              {isMine ? (
                <>
                  <Link
                    to={`/spots/${placeId}/reviews/${review.id}/edit`}
                    className="block w-full py-4 text-center text-[15px] font-medium text-ink"
                  >
                    {t('reviewDetail.edit')}
                  </Link>
                  <button
                    type="button"
                    onClick={handleDelete}
                    className="block w-full py-4 text-center text-[15px] font-medium text-[#e0574a]"
                  >
                    {t('reviewDetail.delete')}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={handleReport}
                  className="block w-full py-4 text-center text-[15px] font-medium text-[#e0574a]"
                >
                  {t('reviewDetail.report')}
                </button>
              )}
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                className="mt-2 block w-full py-3 text-center text-ink-tertiary"
              >
                {t('reviewDetail.cancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </main>
  )
}

function formatReviewDate(isoString: string) {
  const date = new Date(isoString)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}.${pad(date.getMonth() + 1)}.${pad(date.getDate())}`
}

function formatReviewTime(isoString: string) {
  const date = new Date(isoString)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`
}
