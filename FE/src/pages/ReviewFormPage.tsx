import { ArrowLeft, Plus, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { createReview, getPlaceReviews, updateReview, type ReviewWorkTag } from '../api/reviews'
import { getPlaceDetail, type PlaceDetail, type WorkInfo } from '../api/spots'
import spotPlaceholder from '../assets/placeholder/spot.png'
import { BottomNav } from '../components/BottomNav'
import { PlaceholderImage } from '../components/PlaceholderImage'
import { Skeleton } from '../components/Skeleton'
import { PhotoTooLargeError, UnsupportedImageError } from '../lib/compressImage'
import { deleteReviewPhoto, uploadReviewPhoto } from '../lib/reviewPhotoUpload'
import { useLocaleStore } from '../store/useLocaleStore'
import { shortRegion } from '../utils/address'

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
  const [photoError, setPhotoError] = useState<string | null>(null)
  // 작품 태그: DB 전체가 아니라 "이 명소(place.works)에서 촬영한 작품"으로만 후보를 제한한다.
  // 제출 시 work_ids로 서버에 저장된다(issue #60, BE reviews/serializers.py:ReviewWriteSerializer).
  const [workQuery, setWorkQuery] = useState('')
  const [selectedWorks, setSelectedWorks] = useState<ReviewWorkTag[]>([])

  // 이 화면에서 새로 업로드한 사진의 URL만 담아둔다. 수정 화면에 처음부터 있던 기존 리뷰 사진은
  // 여기 안 들어간다 — 아직 저장(제출) 전이라 실제 리뷰가 그 사진을 그대로 쓰고 있어서, 지우기를
  // 눌러도 Storage에서 바로 지우면 안 된다(저장 안 해도 리뷰 사진이 깨짐).
  const newlyUploadedPhotoUrls = useRef<Set<string>>(new Set())

  // 나가기 확인 모달: 헤더 뒤로가기·브라우저 뒤로가기·BottomNav 탭 이동을 전부 이 모달로 가로챈다.
  // 확인을 누르면 pendingLeaveAction에 담아둔 실제 이동을 실행한다.
  const [leaveModalOpen, setLeaveModalOpen] = useState(false)
  const pendingLeaveAction = useRef<(() => void) | null>(null)
  // 제출 성공으로 화면을 뜨는 중이면 true — 아래 popstate 가드가 "나가시겠어요?" 모달을
  // 띄우지 않고 그냥 지나가게 한다 (leaveAfterSubmit 참고).
  const isLeavingAfterSubmitRef = useRef(false)

  function requestLeave(action: () => void) {
    pendingLeaveAction.current = action
    setLeaveModalOpen(true)
  }

  function handleCancelLeave() {
    setLeaveModalOpen(false)
    pendingLeaveAction.current = null
  }

  function handleConfirmLeave() {
    setLeaveModalOpen(false)
    const action = pendingLeaveAction.current
    pendingLeaveAction.current = null
    // 제출 안 하고 나가는 거라, 이번 화면에서 새로 올렸지만 끝내 저장 안 된 사진을 정리한다.
    newlyUploadedPhotoUrls.current.forEach((url) => deleteReviewPhoto(url))
    newlyUploadedPhotoUrls.current.clear()
    action?.()
  }

  useEffect(() => {
    getPlaceDetail(Number(placeId))
      .then(setPlace)
      .catch(() => setPlace(undefined))
  }, [placeId])

  // 브라우저 자체 뒤로가기 버튼도 가로챈다: 진입 시 같은 주소를 한 번 더 쌓아두고(더미),
  // 뒤로가기를 누르면 더미가 사라진 자리를 popstate로 감지해 즉시 다시 채워 넣어(자리 유지)
  // 실제로는 화면이 안 바뀐 것처럼 만든 뒤 모달을 띄운다. 확인을 누르면 더미+원본 두 칸을
  // 한 번에 건너뛰어(go(-2)) 진짜 이전 화면으로 이동한다.
  useEffect(() => {
    window.history.pushState(null, '', window.location.href)
    function handlePopState() {
      if (isLeavingAfterSubmitRef.current) {
        return
      }
      window.history.pushState(null, '', window.location.href)
      requestLeave(() => window.history.go(-2))
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // 제출 성공 후 이동할 때 쓴다. 마운트 시 쌓아둔 더미 history 항목 하나만 지우면(예: replace)
  // 그 아래 있던 "원래 폼 진입 항목"이 그대로 남아서, 상세 화면에서 뒤로가기를 누르면 폼 화면이
  // 다시 나오는 문제가 있었다. go(-1)로 더미 항목까지 마저 되돌아간 뒤 그 자리를 replace해서
  // 더미+원본 두 항목을 사실상 하나로 합친다.
  function leaveAfterSubmit(url: string) {
    isLeavingAfterSubmitRef.current = true
    function handleReplace() {
      window.removeEventListener('popstate', handleReplace)
      navigate(url, { replace: true })
    }
    window.addEventListener('popstate', handleReplace)
    window.history.go(-1)
  }

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
          setSelectedWorks(existing.works)
        }
      })
      .catch(() => {})
  }, [placeId, reviewId])

  function handleSelectWork(work: WorkInfo) {
    setSelectedWorks((prev) => (prev.some((item) => item.id === work.id) ? prev : [...prev, work]))
    setWorkQuery('')
  }

  function handleRemoveWork(workId: number) {
    setSelectedWorks((prev) => prev.filter((item) => item.id !== workId))
  }

  async function handlePhotoSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || photoUrls.length >= PHOTO_MAX_COUNT) {
      return
    }
    setUploading(true)
    setPhotoError(null)
    try {
      const url = await uploadReviewPhoto(file)
      newlyUploadedPhotoUrls.current.add(url)
      setPhotoUrls((prev) => [...prev, url])
    } catch (error) {
      // 업로드 실패해도 나머지 흐름은 그대로 진행 — 사용자가 다시 시도할 수 있게 안내만 띄운다.
      console.error('리뷰 사진 업로드 실패', error)
      if (error instanceof UnsupportedImageError) {
        setPhotoError(t('reviewForm.photoUnsupportedFormat'))
      } else if (error instanceof PhotoTooLargeError) {
        setPhotoError(t('reviewForm.photoTooLarge'))
      } else {
        setPhotoError(t('reviewForm.photoUploadError'))
      }
    } finally {
      setUploading(false)
    }
  }

  function handleRemovePhoto(url: string) {
    setPhotoUrls((prev) => prev.filter((item) => item !== url))
    if (newlyUploadedPhotoUrls.current.has(url)) {
      newlyUploadedPhotoUrls.current.delete(url)
      deleteReviewPhoto(url)
    }
  }

  async function handleSubmit() {
    if (rating === 0 || !content.trim() || submitting) {
      return
    }
    setSubmitting(true)
    const input = {
      rating,
      content: content.trim(),
      language,
      photo_urls: photoUrls,
      work_ids: selectedWorks.map((work) => work.id),
    }
    try {
      if (isEdit) {
        await updateReview(Number(reviewId), input)
        leaveAfterSubmit(`/spots/${placeId}/reviews/${reviewId}`)
      } else {
        const { reviewId: newId } = await createReview(Number(placeId), input)
        leaveAfterSubmit(`/spots/${placeId}/reviews/${newId}`)
      }
    } catch {
      setSubmitting(false)
    }
  }

  const canSubmit = rating > 0 && content.trim().length > 0 && !submitting

  const trimmedWorkQuery = workQuery.trim().toLowerCase()
  const workSuggestions =
    trimmedWorkQuery === ''
      ? []
      : (place?.works.map((placeWork) => placeWork.work) ?? []).filter(
          (work) => !selectedWorks.some((item) => item.id === work.id) && work.title.toLowerCase().includes(trimmedWorkQuery),
        )

  function handleBack() {
    requestLeave(() => navigate(-1))
  }

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-2">
        <button type="button" onClick={handleBack} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <p className="text-center text-lg font-bold text-ink">
          {isEdit ? t('reviewForm.editTitle') : t('reviewForm.title')}
        </p>
      </header>

      {place ? (
        <div className="flex items-center gap-3 border-b border-divider px-4 pb-4">
          <PlaceholderImage
            src={place.photo_url}
            placeholder={spotPlaceholder}
            alt=""
            className="h-[74px] w-[75px] rounded-2xl"
          />
          <div>
            <p className="text-[15px] font-bold text-ink">{place.name}</p>
            <p className="text-xs text-ink-secondary">{shortRegion(place.address)}</p>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 border-b border-divider px-4 pb-4">
          <Skeleton className="h-[74px] w-[75px] rounded-2xl" />
          <Skeleton className="h-4 w-32 rounded-sm" />
        </div>
      )}

      <div className="px-4">
        <p className="mb-2 text-lg font-bold text-ink">{t('reviewForm.workLabel')}</p>
        <input
          type="text"
          value={workQuery}
          onChange={(event) => setWorkQuery(event.target.value)}
          placeholder={t('reviewForm.workPlaceholder')}
          className="w-full rounded-lg bg-accent/15 p-4 text-sm text-ink outline-none placeholder:text-ink-tertiary"
        />
        {workQuery.trim() && workSuggestions.length > 0 && (
          <div className="mt-1 flex flex-col">
            {workSuggestions.map((work) => (
              <button
                key={work.id}
                type="button"
                onClick={() => handleSelectWork(work)}
                className="py-2 text-left text-sm text-ink"
              >
                {work.title}
              </button>
            ))}
          </div>
        )}
        {selectedWorks.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {selectedWorks.map((work) => (
              <span
                key={work.id}
                className="flex items-center gap-1 rounded-full border border-ink-secondary px-3 py-1.5 text-xs font-bold text-ink-secondary"
              >
                #{work.title}
                <button type="button" onClick={() => handleRemoveWork(work.id)} aria-label={`${work.title} 삭제`}>
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="px-4">
        <div className="mb-2 flex items-baseline gap-2">
          <p className="text-lg font-bold text-ink">{t('reviewForm.photoLabel')}</p>
          <p className="text-xs text-ink-tertiary">
            {photoUrls.length} / {PHOTO_MAX_COUNT}
          </p>
        </div>
        <div className="flex gap-2 overflow-x-auto pt-2">
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
        </div>
        {photoError && <p className="mt-2 text-xs text-[#e0574a]">{photoError}</p>}
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

      <BottomNav
        guardNavigation={(to) => {
          requestLeave(() => navigate(to))
          return false
        }}
      />

      {leaveModalOpen && <LeaveConfirmModal onCancel={handleCancelLeave} onConfirm={handleConfirmLeave} />}
    </main>
  )
}

function LeaveConfirmModal({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) {
  const { t } = useTranslation()
  return (
    <div className="fixed inset-0 z-50 mx-auto w-full max-w-[480px]">
      <button type="button" aria-label="닫기" className="absolute inset-0 bg-black/40" onClick={onCancel} />
      <div className="absolute inset-0 flex items-center justify-center px-6" onClick={onCancel}>
        <div className="w-full rounded-3xl bg-white px-6 py-8 text-center" onClick={(event) => event.stopPropagation()}>
          <p className="text-sm text-ink">{t('reviewForm.leaveConfirm')}</p>
          <div className="mt-6 flex gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 rounded-full border border-divider py-3 text-sm font-bold text-ink-secondary"
            >
              {t('reviewForm.leaveConfirmStay')}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className="flex-1 rounded-full bg-primary py-3 text-sm font-bold text-white"
            >
              {t('reviewForm.leaveConfirmLeave')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
