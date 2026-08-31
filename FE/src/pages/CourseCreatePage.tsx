import { ArrowLeft, Plus, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { createCourse, type CoursePlaceInput, type CoursePlaceRole } from '../api/courses'
import { getPlaceDetail, type NearbyPlace, type PlaceDetail } from '../api/spots'
import { BottomNav } from '../components/BottomNav'
import { Skeleton } from '../components/Skeleton'
import { loadKakaoMaps } from '../lib/kakaoMap'
import { classifyNearbyPlace, getCoursePlaceRole, type CourseCategoryTab } from '../utils/courseCategory'
import { getDistanceKm } from '../utils/distance'

const TABS: CourseCategoryTab[] = ['FOOD_CAFE', 'EXPERIENCE', 'NEARBY']
const ROLE_LABEL: Record<CoursePlaceRole, string> = {
  RESTAURANT: '맛집',
  CAFE: '카페',
  OTHER: '주변 명소',
}
const TITLE_MAX_LENGTH = 200

// 지도 위 명소(앙커)/후보 마커 색. index.css의 --color-primary, --color-ink-tertiary와 맞춘다.
const ANCHOR_PIN_COLOR = '#f47c5c'
const PICKED_PIN_COLOR = '#f47c5c'
const CANDIDATE_PIN_COLOR = '#c9bab0'

function pinIconDataUrl(color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36"><path d="M14 0C6.3 0 0 6.3 0 14c0 10.5 14 22 14 22s14-11.5 14-22C28 6.3 21.7 0 14 0z" fill="${color}"/><circle cx="14" cy="14" r="5" fill="white"/></svg>`
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}

type Pick = { role: CoursePlaceRole; candidate: NearbyPlace }

export function CourseCreatePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { placeId } = useParams<{ placeId: string }>()

  const [place, setPlace] = useState<PlaceDetail | undefined>(undefined)
  const [tab, setTab] = useState<CourseCategoryTab>('FOOD_CAFE')
  const [title, setTitle] = useState('')
  const [picks, setPicks] = useState<Pick[]>([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    getPlaceDetail(Number(placeId))
      .then(setPlace)
      .catch(() => setPlace(undefined))
  }, [placeId])

  const anchorLat = place?.latitude ? Number(place.latitude) : null
  const anchorLng = place?.longitude ? Number(place.longitude) : null

  const candidates = useMemo(
    () => (place?.nearby_places ?? []).filter((nearby) => classifyNearbyPlace(nearby.category_name) === tab),
    [place, tab],
  )

  function handleAdd(candidate: NearbyPlace) {
    const role = getCoursePlaceRole(candidate.category_name)
    setPicks((prev) => {
      const index = prev.findIndex((pick) => pick.role === role)
      const next: Pick = { role, candidate }
      if (index === -1) {
        return [...prev, next]
      }
      const copy = [...prev]
      copy[index] = next
      return copy
    })
  }

  function handleRemove(role: CoursePlaceRole) {
    setPicks((prev) => prev.filter((pick) => pick.role !== role))
  }

  const handleToggle = useCallback(
    (candidate: NearbyPlace) => {
      const role = getCoursePlaceRole(candidate.category_name)
      setPicks((prev) => {
        const isPicked = prev.some((pick) => pick.role === role && pick.candidate === candidate)
        if (isPicked) {
          return prev.filter((pick) => pick.role !== role)
        }
        const next: Pick = { role, candidate }
        const index = prev.findIndex((pick) => pick.role === role)
        if (index === -1) {
          return [...prev, next]
        }
        const copy = [...prev]
        copy[index] = next
        return copy
      })
    },
    [],
  )

  const canSubmit = title.trim().length > 0 && picks.length === 3 && !submitting

  async function handleSubmit() {
    if (!canSubmit || !placeId) {
      return
    }
    setSubmitting(true)
    const course_places: CoursePlaceInput[] = picks.map((pick) => ({
      role: pick.role,
      name: pick.candidate.place_name ?? '',
      address: pick.candidate.address_name ?? '',
      road_address_name: pick.candidate.road_address_name ?? '',
      latitude: pick.candidate.latitude,
      longitude: pick.candidate.longitude,
      category_name: pick.candidate.category_name ?? '',
      kakao_place_id: null,
    }))
    try {
      const course = await createCourse(Number(placeId), { title: title.trim(), description: '', course_places })
      navigate(`/courses/${course.id}`, { replace: true })
    } catch {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-dvh flex-col gap-4 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-6">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <p className="text-center text-lg font-bold text-ink">{t('courseCreate.title')}</p>
      </header>

      {place === undefined ? (
        <div className="flex flex-col gap-3 px-4">
          <Skeleton className="h-10 w-full rounded-lg" />
          <Skeleton className="h-8 w-full rounded-full" />
          <Skeleton className="h-40 w-full rounded-2xl" />
        </div>
      ) : (
        <>
          <div className="px-4">
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value.slice(0, TITLE_MAX_LENGTH))}
              placeholder={t('courseCreate.titlePlaceholder')}
              className="w-full rounded-lg border border-divider px-3 py-2 text-sm text-ink outline-none"
            />
          </div>

          {anchorLat !== null && anchorLng !== null && (
            <div className="px-4">
              <CourseCandidateMap
                anchor={{ name: place.name, latitude: anchorLat, longitude: anchorLng }}
                candidates={candidates}
                picks={picks}
                onToggle={handleToggle}
              />
            </div>
          )}

          <div className="flex gap-2 px-4">
            {TABS.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setTab(option)}
                className={`rounded-full border px-3 py-2 text-sm ${
                  tab === option ? 'border-primary bg-primary text-white' : 'border-divider text-ink-secondary'
                }`}
              >
                {t(`courseCreate.tabs.${option}`)}
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-3 px-4">
            {candidates.length === 0 ? (
              <p className="py-4 text-center text-sm text-ink-tertiary">{t('courseCreate.candidatesEmpty')}</p>
            ) : (
              candidates.map((candidate, index) => {
                const role = getCoursePlaceRole(candidate.category_name)
                const isPicked = picks.some((pick) => pick.role === role && pick.candidate === candidate)
                const distance =
                  anchorLat !== null && anchorLng !== null
                    ? getDistanceKm(anchorLat, anchorLng, candidate.latitude, candidate.longitude).toFixed(1)
                    : null
                return (
                  <div
                    key={`${candidate.place_name}-${index}`}
                    className="flex items-center justify-between rounded-xl border border-divider px-3 py-2.5"
                  >
                    <div>
                      <p className="text-sm text-ink">{candidate.place_name}</p>
                      <p className="text-xs text-ink-secondary">
                        {ROLE_LABEL[role]}
                        {distance && ` · ${distance}km`}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleAdd(candidate)}
                      aria-label="추가"
                      className={`flex h-7 w-7 items-center justify-center rounded-full ${
                        isPicked ? 'bg-divider' : 'bg-primary'
                      }`}
                    >
                      <Plus size={16} className="text-white" />
                    </button>
                  </div>
                )
              })
            )}
          </div>

          <div className="flex flex-col gap-3 px-4">
            <p className="text-sm font-bold text-ink">
              {picks.length + 1} / 4 · {t('courseCreate.selectedLabel')}
            </p>

            <div className="flex items-center gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
                1
              </span>
              <div>
                <p className="text-sm font-medium text-ink">{place.name}</p>
                {place.works[0] && <p className="text-xs text-ink-secondary">{place.works[0].work.title}</p>}
              </div>
            </div>

            {picks.map((pick, index) => (
              <div key={pick.role} className="flex items-center gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
                  {index + 2}
                </span>
                <div className="flex-1">
                  <p className="text-sm font-medium text-ink">{pick.candidate.place_name}</p>
                  <p className="text-xs text-ink-secondary">{ROLE_LABEL[pick.role]}</p>
                </div>
                <button type="button" onClick={() => handleRemove(pick.role)} aria-label="제거">
                  <X size={18} className="text-ink-tertiary" />
                </button>
              </div>
            ))}
          </div>

          <div className="px-4">
            <button
              type="button"
              disabled={!canSubmit}
              onClick={handleSubmit}
              className="w-full rounded-full bg-primary py-3 text-sm font-bold text-white disabled:opacity-40"
            >
              {t('courseCreate.submitButton')}
            </button>
          </div>
        </>
      )}

      <BottomNav />
    </main>
  )
}

function CourseCandidateMap({
  anchor,
  candidates,
  picks,
  onToggle,
}: {
  anchor: { name: string; latitude: number; longitude: number }
  candidates: NearbyPlace[]
  picks: Pick[]
  onToggle: (candidate: NearbyPlace) => void
}) {
  const { t } = useTranslation()
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<kakao.maps.Map | null>(null)
  const markersRef = useRef<kakao.maps.Marker[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'unavailable'>('loading')

  useEffect(() => {
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
        const center = new kakaoSdk.maps.LatLng(anchor.latitude, anchor.longitude)
        const map = new kakaoSdk.maps.Map(mapRef.current, { center, level: 5 })
        mapInstanceRef.current = map
        new kakaoSdk.maps.Marker({
          position: center,
          map,
          title: anchor.name,
          image: new kakaoSdk.maps.MarkerImage(pinIconDataUrl(ANCHOR_PIN_COLOR), new kakaoSdk.maps.Size(28, 36)),
        })
        setStatus('ready')
      })
      .catch(() => setStatus('unavailable'))

    return () => {
      cancelled = true
    }
  }, [anchor.latitude, anchor.longitude, anchor.name])

  useEffect(() => {
    const kakaoSdk = window.kakao
    const map = mapInstanceRef.current
    if (status !== 'ready' || !kakaoSdk?.maps || !map) {
      return
    }

    markersRef.current.forEach((marker) => marker.setMap(null))
    markersRef.current = candidates.map((candidate) => {
      const isPicked = picks.some((pick) => pick.candidate === candidate)
      const marker = new kakaoSdk.maps.Marker({
        position: new kakaoSdk.maps.LatLng(candidate.latitude, candidate.longitude),
        map,
        title: candidate.place_name ?? undefined,
        image: new kakaoSdk.maps.MarkerImage(
          pinIconDataUrl(isPicked ? PICKED_PIN_COLOR : CANDIDATE_PIN_COLOR),
          new kakaoSdk.maps.Size(28, 36),
        ),
      })
      kakaoSdk.maps.event.addListener(marker, 'click', () => onToggle(candidate))
      return marker
    })
  }, [candidates, picks, onToggle, status])

  return (
    <div className="relative h-[180px] w-full overflow-hidden rounded-2xl bg-accent/15">
      <div ref={mapRef} className="h-full w-full" />
      {status !== 'ready' && (
        <div className="absolute inset-0 flex items-center justify-center bg-accent/15 text-sm text-ink-tertiary">
          {status === 'loading' ? '' : t('courseCreate.mapUnavailable')}
        </div>
      )}
    </div>
  )
}
