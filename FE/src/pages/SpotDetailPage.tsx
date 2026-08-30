import {
  AlertTriangle,
  ArrowLeft,
  Camera,
  CalendarDays,
  Clock,
  Film,
  MapPin,
  Share2,
  Star,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getPlaceDetail, type PlaceDetail } from '../api/spots'
import { BottomNav } from '../components/BottomNav'
import { FavoriteButton } from '../components/FavoriteButton'
import { RatingModal } from '../components/RatingModal'
import { Skeleton } from '../components/Skeleton'
import { loadKakaoMaps } from '../lib/kakaoMap'
import { useAuthStore } from '../store/useAuthStore'

export function SpotDetailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { placeId } = useParams<{ placeId: string }>()
  const member = useAuthStore((state) => state.member)

  // undefined: 로딩 중, null: 존재하지 않거나 실패
  const [place, setPlace] = useState<PlaceDetail | null | undefined>(undefined)
  const [showRatingModal, setShowRatingModal] = useState(false)

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

  // 리뷰 작성 화면엔 별점 UI가 없어서(Figma 목업과 동일하게), "별점 남기기"/"리뷰 남기기"
  // 둘 다 먼저 이 모달에서 별점을 고른 뒤에 작성 화면으로 넘어간다.
  function handleReviewClick() {
    if (requireLogin()) {
      setShowRatingModal(true)
    }
  }

  return (
    <main className="flex min-h-dvh flex-col gap-8 pb-24">
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
                {place.works[0] && (
                  <Link to={`/works/${place.works[0].work.id}`} className="text-sm text-primary">
                    {place.works[0].work.category === 'DRAMA' ? t('searchPage.filters.drama') : t('searchPage.filters.movie')}{' '}
                    &lt;{place.works[0].work.title}&gt;
                  </Link>
                )}
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
              <InfoRow
                icon={<Film size={14} />}
                label={t('spotDetail.mainWorks')}
                value={place.works.map((w) => w.work.title).join(', ')}
              />
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

            <div className="flex gap-2.5">
              <button
                type="button"
                onClick={handleReviewClick}
                className="flex-1 rounded-full border border-primary py-3 text-sm font-medium text-primary"
              >
                {t('spotDetail.rateButton')}
              </button>
              <button
                type="button"
                onClick={handleReviewClick}
                className="flex-1 rounded-full bg-primary py-3 text-sm font-medium text-white"
              >
                {t('spotDetail.reviewButton')}
              </button>
            </div>
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
              disabled
              className="w-full rounded-2xl bg-primary py-4 text-sm font-medium text-white"
            >
              {t('spotDetail.courseCta')}
            </button>
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

function SpotMap({ place }: { place: PlaceDetail }) {
  const { t } = useTranslation()
  const mapRef = useRef<HTMLDivElement>(null)
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
        const map = new kakaoSdk.maps.Map(mapRef.current, { center, level: 4 })
        new kakaoSdk.maps.Marker({ position: center, map, title: place.name })

        place.nearby_places.forEach((nearby) => {
          new kakaoSdk.maps.Marker({
            position: new kakaoSdk.maps.LatLng(nearby.latitude, nearby.longitude),
            map,
            title: nearby.place_name ?? undefined,
          })
        })

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
