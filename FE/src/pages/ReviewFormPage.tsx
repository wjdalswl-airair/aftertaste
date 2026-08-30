import { ArrowLeft, Plus, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { createReview, getPlaceReviews, updateReview } from '../api/reviews'
import { getPlaceDetail, type PlaceDetail } from '../api/spots'
import { BottomNav } from '../components/BottomNav'
import { Skeleton } from '../components/Skeleton'
import { uploadReviewPhoto } from '../lib/reviewPhotoUpload'
import { useLocaleStore } from '../store/useLocaleStore'

const CONTENT_MAX_LENGTH = 500
const PHOTO_MAX_COUNT = 5

export function ReviewFormPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { placeId, reviewId } = useParams<{ placeId: string; reviewId?: string }>()
  const language = useLocaleStore((state) => state.language)
  const isEdit = Boolean(reviewId)

  const initialRating = (location.state as { rating?: number } | null)?.rating ?? 0

  const [place, setPlace] = useState<PlaceDetail | undefined>(undefined)
  const [rating, setRating] = useState(initialRating)
  const [content, setContent] = useState('')
  const [photoUrls, setPhotoUrls] = useState<string[]>([])
  const [uploading, setUploading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [photoError, setPhotoError] = useState(false)

  useEffect(() => {
    getPlaceDetail(Number(placeId))
      .then(setPlace)
      .catch(() => setPlace(undefined))
  }, [placeId])

  useEffect(() => {
    if (!reviewId) {
      return
    }
    getPlaceReviews(Number(placeId))
      .then((reviews) => {
        const existing = reviews.find((review) => review.id === Number(reviewId))
        if (existing) {
          setRating(existing.rating)
          setContent(existing.content)
          setPhotoUrls(existing.photos.map((photo) => photo.photo_url))
        }
      })
      .catch(() => {})
  }, [placeId, reviewId])

  async function handlePhotoSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || photoUrls.length >= PHOTO_MAX_COUNT) {
      return
    }
    setUploading(true)
    setPhotoError(false)
    try {
      const url = await uploadReviewPhoto(file)
      setPhotoUrls((prev) => [...prev, url])
    } catch (error) {
      // 업로드 실패해도 나머지 흐름은 그대로 진행 — 사용자가 다시 시도할 수 있게 안내만 띄운다.
      console.error('리뷰 사진 업로드 실패', error)
      setPhotoError(true)
    } finally {
      setUploading(false)
    }
  }

  function handleRemovePhoto(url: string) {
    setPhotoUrls((prev) => prev.filter((item) => item !== url))
  }

  async function handleSubmit() {
    if (rating === 0 || !content.trim() || submitting) {
      return
    }
    setSubmitting(true)
    const input = { rating, content: content.trim(), language, photo_urls: photoUrls }
    try {
      if (isEdit) {
        await updateReview(Number(reviewId), input)
        navigate(`/spots/${placeId}/reviews/${reviewId}`, { replace: true })
      } else {
        const { reviewId: newId } = await createReview(Number(placeId), input)
        navigate(`/spots/${placeId}/reviews/${newId}`, { replace: true })
      }
    } catch {
      setSubmitting(false)
    }
  }

  const canSubmit = rating > 0 && content.trim().length > 0 && !submitting

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-6">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <p className="text-center text-lg font-bold text-ink">
          {isEdit ? t('reviewForm.editTitle') : t('reviewForm.title')}
        </p>
      </header>

      {place ? (
        <div className="flex items-center gap-3 border-b border-divider px-4 pb-4">
          <img src={place.photo_url} alt="" className="h-[74px] w-[75px] rounded-2xl object-cover" />
          <div>
            <p className="text-[15px] font-bold text-ink">{place.name}</p>
            {place.works[0] && <p className="text-xs text-ink-secondary">{place.works[0].work.title}</p>}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 border-b border-divider px-4 pb-4">
          <Skeleton className="h-[74px] w-[75px] rounded-2xl" />
          <Skeleton className="h-4 w-32 rounded-sm" />
        </div>
      )}

      <div className="px-4">
        <div className="mb-2 flex items-baseline gap-2">
          <p className="text-lg font-bold text-ink">{t('reviewForm.photoLabel')}</p>
          <p className="text-xs text-ink-tertiary">
            {photoUrls.length} / {PHOTO_MAX_COUNT}
          </p>
        </div>
        <div className="flex gap-2 overflow-x-auto">
          {photoUrls.map((url) => (
            <div key={url} className="relative h-[74px] w-[75px] shrink-0">
              <img src={url} alt="" className="h-full w-full rounded-lg object-cover" />
              <button
                type="button"
                onClick={() => handleRemovePhoto(url)}
                aria-label="사진 삭제"
                className="absolute -right-1 -top-1 rounded-full bg-ink p-0.5"
              >
                <X size={12} className="text-white" />
              </button>
            </div>
          ))}
          {photoUrls.length < PHOTO_MAX_COUNT && (
            <label className="flex h-[74px] w-[75px] shrink-0 items-center justify-center rounded-lg bg-accent/15">
              <input type="file" accept="image/*" className="hidden" onChange={handlePhotoSelect} disabled={uploading} />
              {uploading ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              ) : (
                <Plus size={22} className="text-primary" />
              )}
            </label>
          )}
        </div>
        {photoError && <p className="mt-2 text-xs text-[#e0574a]">{t('reviewForm.photoUploadError')}</p>}
      </div>

      <div className="px-4">
        <p className="mb-2 text-lg font-bold text-ink">{t('reviewForm.contentLabel')}</p>
        <div className="rounded-lg bg-accent/15 p-6">
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value.slice(0, CONTENT_MAX_LENGTH))}
            placeholder={t('reviewForm.contentPlaceholder')}
            rows={8}
            className="w-full resize-none bg-transparent text-base text-ink outline-none placeholder:text-ink-tertiary"
          />
          <p className="text-right text-[11px] text-ink-tertiary">
            {content.length} / {CONTENT_MAX_LENGTH}
          </p>
        </div>
      </div>

      <div className="px-4">
        <button
          type="button"
          disabled={!canSubmit}
          onClick={handleSubmit}
          className="w-full rounded-full bg-primary py-3 text-sm font-bold text-white disabled:opacity-40"
        >
          {t('reviewForm.submitButton')}
        </button>
      </div>

      <BottomNav />
    </main>
  )
}
