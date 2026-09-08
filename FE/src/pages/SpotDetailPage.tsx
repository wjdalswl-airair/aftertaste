import {
  AlertTriangle,
  ArrowLeft,
  Camera,
  CalendarDays,
  Clock,
  Film,
  MapPin,
  Share2,
  Sparkles,
  Star,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { aiRecommendCourse, getPlaceCourses } from '../api/courses'
import { getPlaceDetail, type PlaceDetail, type PlaceWork } from '../api/spots'
import { BottomNav } from '../components/BottomNav'
import { FavoriteButton } from '../components/FavoriteButton'
import { RatingModal } from '../components/RatingModal'
import { Skeleton } from '../components/Skeleton'
import { loadKakaoMaps, pinIconDataUrl } from '../lib/kakaoMap'
import { useAuthStore } from '../store/useAuthStore'
import { shortRegion } from '../utils/address'

// index.css의 --color-primary와 맞춘 값 (코스 생성 화면 마커와 동일, CourseCreatePage.tsx 참고).
const SPOT_PIN_COLOR = '#f47c5c'

export function SpotDetailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { placeId } = useParams<{ placeId: string }>()
  const member = useAuthStore((state) => state.member)

  // undefined: 로딩 중, null: 존재하지 않거나 실패
  const [place, setPlace] = useState<PlaceDetail | null | undefined>(undefined)
  const [showRatingModal, setShowRatingModal] = useState(false)
  const [courseAiLoading, setCourseAiLoading] = useState(false)
  const [courseAiError, setCourseAiError] = useState<string | null>(null)

  useEffect(() => {
    setPlace(undefined)
    getPlaceDetail(Number(placeId))
      .then(setPlace)
      .catch(() => setPlace(null))
  }, [placeId])

  function handleShare() {
    navigator.clipboard.writeText(window.location.href).catch(() => {})
  }

  function requireLogin() {
    if (!member) {
      navigate('/login', { state: { message: '로그인이 필요한 기능입니다' } })
      return false
    }
    return true
  }

  // "별점 남기기" 버튼은 없앴다(2026-09-06) — BE Review 모델의 content가 필수라 별점만
  // 저장하는 API 자체가 없어서, 별점만 남기는 흐름을 따로 만들 수 없었다.
  // 이 명소에 내가 쓴 리뷰가 하나라도 있으면(닉네임 비교 — 리뷰 API에 작성자 본인 여부
  // 플래그가 없어서 임시로 이렇게 판단, 다른 화면과 동일한 방식) 별점 모달 없이 바로
  // 작성 화면으로 보내고, 없으면 먼저 별점 모달에서 고른 뒤 작성 화면으로 넘어간다.
  function handleReviewClick() {
    if (!requireLogin()) {
      return
    }
    const alreadyReviewed = place?.reviews.some((review) => review.author_nickname === member?.nickname) ?? false
    if (alreadyReviewed) {
      navigate(`/spots/${placeId}/reviews/new`)
      return
    }
    setShowRatingModal(true)
  }

  // 이 명소를 기준으로 한 코스가 이미 있으면(로그인 불필요) 그중 첫 번째로 보내고,
  // 없으면 로그인 확인 후 AI(Claude)가 주변 상권으로 코스를 자동으로 만들어준다
  // (GitHub 이슈 #38 — 기존엔 수동 생성 화면으로 보냈으나, BE에 AI 추천 엔드포인트가 생겨서 교체).
  async function handleCourseClick() {
    if (courseAiLoading) {
      return
    }
    const courses = await getPlaceCourses(Number(placeId)).catch(() => [])
    if (courses.length > 0) {
      navigate(`/courses/${courses[0].id}`)
      return
    }
    if (!requireLogin()) {
      return
    }

    setCourseAiError(null)
    setCourseAiLoading(true)
    try {
      const course = await aiRecommendCourse(Number(placeId))
      navigate(`/courses/${course.id}`)
    } catch (error) {
      setCourseAiError(error instanceof Error ? error.message : t('spotDetail.courseAiError'))
    } finally {
      setCourseAiLoading(false)
    }
  }

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-6">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <div />
        <button type="button" onClick={handleShare} aria-label="공유" className="justify-self-end">
          <Share2 size={22} className="text-ink" />
        </button>
      </header>

      {place === undefined && <SpotDetailSkeleton />}

      {place === null && (
        <p className="px-4 py-20 text-center text-ink-tertiary">{t('spotDetail.notFound')}</p>
      )}

      {place && (
        <>
          <div className="relative px-4">
            <img
              src={place.photo_url}
              alt=""
              className="h-[230px] w-full rounded-2xl object-cover"
            />
            <FavoriteButton
              placeId={place.id}
              initialFavorited={place.is_favorited}
              size={18}
              className="absolute right-8 top-3 rounded-full bg-white/85 p-2"
            />
          </div>

          <div className="flex flex-col gap-6 px-4">
            <div className="flex items-start justify-between">
              <div className="flex flex-col gap-1">
                <p className="text-sm text-ink-tertiary">{shortRegion(place.address)}</p>
                <p className="text-xl font-bold text-ink">{place.name}</p>
              </div>
              {place.review_count > 0 && (
                <div className="flex shrink-0 items-center gap-1 pt-1">
                  <Star size={14} className="fill-primary text-primary" />
                  <p className="text-sm text-ink-secondary">
                    {place.review_average_rating} ({place.review_count.toLocaleString()})
                  </p>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-4 rounded-2xl bg-accent/15 p-5">
              <InfoRow icon={<MapPin size={14} />} label={t('spotDetail.location')} value={place.address} />
              <MainWorksRow works={place.works} />
              <InfoRow icon={<Camera size={14} />} label={t('spotDetail.photoTips')} value={place.photo_tips} />
              <InfoRow icon={<Clock size={14} />} label={t('spotDetail.businessHours')} value={place.business_hours} />
              <InfoRow
                icon={<CalendarDays size={14} />}
                label={t('spotDetail.recommendedTime')}
                value={place.recommended_time}
              />
              <InfoRow
                icon={<AlertTriangle size={14} />}
                label={t('spotDetail.etiquette')}
                value={place.etiquette}
              />
            </div>

            <button
              type="button"
              onClick={handleReviewClick}
              className="w-full rounded-full bg-primary py-3 text-sm font-medium text-white"
            >
              {t('spotDetail.reviewButton')}
            </button>
          </div>

          <section className="px-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-ink">{t('spotDetail.reviewsTitle')}</h2>
              {place.reviews.length > 0 && (
                <Link to={`/spots/${placeId}/reviews`} className="text-sm text-ink-tertiary">
                  {t('spotDetail.reviewsMore')}
                </Link>
              )}
            </div>
            {place.reviews.length === 0 ? (
              <p className="text-sm text-ink-tertiary">{t('spotDetail.reviewsEmpty')}</p>
            ) : (
              <div className="scrollbar-hide flex gap-3 overflow-x-auto">
                {place.reviews.map((review) => (
                  <Link
                    key={review.id}
                    to={`/spots/${placeId}/reviews/${review.id}`}
                    className="w-[110px] flex-shrink-0"
                  >
                    {review.photos[0] ? (
                      <img
                        src={review.photos[0].photo_url}
                        alt=""
                        className="h-[110px] w-full rounded-xl object-cover"
                      />
                    ) : (
                      <div className="h-[110px] w-full rounded-xl bg-divider" />
                    )}
                    <p className="mt-2 truncate pl-3 text-xs text-ink">{review.author_nickname}</p>
                    <p className="truncate pl-3 text-xs text-ink-secondary">{review.content}</p>
                  </Link>
                ))}
              </div>
            )}
          </section>

          <div className="px-4">
            <button
              type="button"
              onClick={handleCourseClick}
              disabled={courseAiLoading}
              className="flex w-full items-center justify-center gap-1.5 rounded-2xl bg-primary py-3 text-sm font-medium text-white disabled:opacity-60"
            >
              <Sparkles size={16} />
              {courseAiLoading ? t('spotDetail.courseCtaLoading') : t('spotDetail.courseCta')}
            </button>
            {courseAiError && <p className="mt-2 text-center text-xs text-primary">{courseAiError}</p>}
          </div>

          <section className="px-4">
            <h2 className="mb-3 text-lg font-bold text-ink">{t('spotDetail.mapTitle')}</h2>
            <SpotMap place={place} />
          </section>
        </>
      )}

      {showRatingModal && place && (
        <RatingModal
          place={{ name: place.name, photo_url: place.photo_url }}
          onClose={() => setShowRatingModal(false)}
          onNext={(rating) => {
            setShowRatingModal(false)
            navigate(`/spots/${placeId}/reviews/new`, { state: { rating } })
          }}
        />
      )}

      <BottomNav />
    </main>
  )
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  if (!value) {
    return null
  }
  return (
    <div className="flex gap-2.5 text-[13px]">
      <span className="mt-0.5 shrink-0 text-primary">{icon}</span>
      <span className="w-[90px] shrink-0 text-ink">{label}</span>
      <span className="flex-1 text-ink-secondary">{value}</span>
    </div>
  )
}

const MAIN_WORKS_COLLAPSED_COUNT = 7

// "주요 촬영작"은 작품이 8개 이상이면 처음 7개만 보여주고 더보기/접기로 나머지를 토글한다.
function MainWorksRow({ works }: { works: PlaceWork[] }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  if (works.length === 0) {
    return null
  }

  const hasMore = works.length > MAIN_WORKS_COLLAPSED_COUNT
  const visibleWorks = expanded ? works : works.slice(0, MAIN_WORKS_COLLAPSED_COUNT)

  return (
    <div className="flex gap-2.5 text-[13px]">
      <span className="mt-0.5 shrink-0 text-primary">
        <Film size={14} />
      </span>
      <span className="w-[90px] shrink-0 text-ink">{t('spotDetail.mainWorks')}</span>
      <span className="flex-1 text-ink-secondary">
        {visibleWorks.map((placeWork, index) => (
          <span key={placeWork.work.id}>
            <Link to={`/works/${placeWork.work.id}`} className="text-ink-secondary no-underline">
              {placeWork.work.title}
            </Link>
            {index < visibleWorks.length - 1 && ', '}
          </span>
        ))}
        {hasMore && (
          <button type="button" onClick={() => setExpanded((prev) => !prev)} className="ml-1 font-medium text-primary">
            {expanded ? t('spotDetail.mainWorksLess') : t('spotDetail.mainWorksMore')}
          </button>
        )}
      </span>
    </div>
  )
}

function SpotMap({ place }: { place: PlaceDetail }) {
  const { t } = useTranslation()
  const mapRef = useRef<HTMLDivElement>(null)
  // 지도 인스턴스와 마커를 기억해뒀다가, 명소가 바뀌어도 지도는 재사용(중심만 이동)하고
  // 마커는 지우고 새로 찍는다 — 안 그러면(예: 다른 명소로 이동) 이전 마커가 안 지워지고
  // 계속 쌓여서 여러 개로 보인다.
  const mapInstanceRef = useRef<kakao.maps.Map | null>(null)
  const markersRef = useRef<kakao.maps.Marker[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'unavailable'>('loading')

  // latitude/longitude는 DecimalField라 API가 문자열로 내려준다 ("37.579617").
  const lat = place.latitude === null ? null : Number(place.latitude)
  const lng = place.longitude === null ? null : Number(place.longitude)
  const hasCoords = lat !== null && lng !== null && !Number.isNaN(lat) && !Number.isNaN(lng)

  useEffect(() => {
    if (!hasCoords) {
      setStatus('unavailable')
      return
    }

    const promise = loadKakaoMaps()
    if (!promise) {
      setStatus('unavailable')
      return
    }

    let cancelled = false
    promise
      .then((kakaoSdk) => {
        if (cancelled || !mapRef.current) {
          return
        }
        const center = new kakaoSdk.maps.LatLng(lat, lng)

        if (!mapInstanceRef.current) {
          mapInstanceRef.current = new kakaoSdk.maps.Map(mapRef.current, { center, level: 4 })
        } else {
          mapInstanceRef.current.setCenter(center)
        }
        const map = mapInstanceRef.current

        // 이 지도는 명소 자체 위치만 보여준다 — 주변 상권(nearby_places)은 코스 화면
        // 지도에서만 후보로 마커 표시하고, 명소 상세에선 마커로 안 찍는다(사용자 결정).
        markersRef.current.forEach((marker) => marker.setMap(null))
        markersRef.current = [
          new kakaoSdk.maps.Marker({
            position: center,
            map,
            title: place.name,
            image: new kakaoSdk.maps.MarkerImage(pinIconDataUrl(SPOT_PIN_COLOR), new kakaoSdk.maps.Size(28, 36)),
          }),
        ]

        setStatus('ready')
      })
      .catch(() => setStatus('unavailable'))

    return () => {
      cancelled = true
    }
  }, [place, hasCoords, lat, lng])

  const directionsUrl = hasCoords
    ? `https://map.kakao.com/link/to/${encodeURIComponent(place.name)},${lat},${lng}`
    : null

  // 길찾기를 누른 시점에 사용자 현재 위치를 물어봐서 출발지로 같이 넣어준다.
  // 위치를 못 가져오면(거부·미지원 등) 목적지만 있는 기존 링크로 대신 연다.
  function handleDirectionsClick(event: React.MouseEvent) {
    event.preventDefault()
    if (!directionsUrl) {
      return
    }
    if (!navigator.geolocation) {
      window.open(directionsUrl, '_blank', 'noopener,noreferrer')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const from = `${encodeURIComponent(t('spotDetail.currentLocation'))},${position.coords.latitude},${position.coords.longitude}`
        const to = `${encodeURIComponent(place.name)},${lat},${lng}`
        window.open(`https://map.kakao.com/link/from/${from}/to/${to}`, '_blank', 'noopener,noreferrer')
      },
      () => {
        window.open(directionsUrl, '_blank', 'noopener,noreferrer')
      },
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="relative h-[240px] w-full overflow-hidden rounded-2xl bg-accent/15">
        <div ref={mapRef} className="h-full w-full" />
        {status !== 'ready' && (
          <div className="absolute inset-0 flex items-center justify-center bg-accent/15 text-sm text-ink-tertiary">
            {status === 'loading' ? '' : t(directionsUrl ? 'spotDetail.mapUnavailable' : 'spotDetail.noCoordinates')}
          </div>
        )}
      </div>

      {directionsUrl && (
        <a
          href={directionsUrl}
          onClick={handleDirectionsClick}
          target="_blank"
          rel="noreferrer"
          className="rounded-full border border-primary py-3 text-center text-sm font-medium text-primary"
        >
          {t('spotDetail.directions')}
        </a>
      )}
    </div>
  )
}

function SpotDetailSkeleton() {
  return (
    <div className="flex flex-col gap-8">
      <Skeleton className="mx-4 h-[230px] rounded-2xl" />

      <div className="flex flex-col gap-6 px-4">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-3 w-1/3 rounded-sm" />
          <Skeleton className="h-6 w-2/3 rounded-sm" />
        </div>
        <Skeleton className="h-56 w-full rounded-2xl" />
        <div className="flex gap-2.5">
          <Skeleton className="h-11 flex-1 rounded-full" />
          <Skeleton className="h-11 flex-1 rounded-full" />
        </div>
      </div>

      <div className="flex flex-col gap-3 px-4">
        <Skeleton className="h-5 w-1/3 rounded-sm" />
        <div className="flex gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-[110px] w-[110px] shrink-0 rounded-xl" />
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3 px-4">
        <Skeleton className="h-5 w-1/3 rounded-sm" />
        <Skeleton className="h-[280px] w-full rounded-2xl" />
      </div>
    </div>
  )
}
