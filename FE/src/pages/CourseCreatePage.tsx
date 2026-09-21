import { DndContext, PointerSensor, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import { arrayMove, SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { ArrowLeft, GripVertical, Plus, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { createCourse, getCourseDetail, updateCourse, type CoursePlaceInput, type CoursePlaceRole } from '../api/courses'
import { getPlaceDetail, type NearbyPlace, type PlaceDetail } from '../api/spots'
import { BottomNav } from '../components/BottomNav'
import { Skeleton } from '../components/Skeleton'
import { loadKakaoMaps, pinIconDataUrl } from '../lib/kakaoMap'
import { useAuthStore } from '../store/useAuthStore'
import { classifyNearbyPlace, getCoursePlaceRole, type CourseCategoryTab } from '../utils/courseCategory'
import { getDistanceKm } from '../utils/distance'

const TABS: CourseCategoryTab[] = ['FOOD_CAFE', 'EXPERIENCE', 'NEARBY']
const ROLE_LABEL: Record<CoursePlaceRole, string> = {
  RESTAURANT: '맛집',
  CAFE: '카페',
  OTHER: '주변 명소',
}
const TITLE_MAX_LENGTH = 200
// 탭 하나당 후보 목록 개수 제한. BE가 명소 상세(GET /api/places/{id}/)에서 카카오 카테고리
// 검색으로 음식점·카페·관광명소 각각 최대 15개씩(최대 45개) 받아온 걸 그대로 넘겨주는데,
// 한 탭(예: 맛집·카페)에 두 카테고리가 합쳐져 최대 30개까지 뜰 수 있어서 화면에서 다시 자른다.
const MAX_CANDIDATES_PER_TAB = 15

// 지도 위 명소(앙커)/후보 마커 색. index.css의 --color-primary, --color-ink-tertiary와 맞춘다.
const ANCHOR_PIN_COLOR = '#f47c5c'
const PICKED_PIN_COLOR = '#f47c5c'
const CANDIDATE_PIN_COLOR = '#c9bab0'

type Pick = { role: CoursePlaceRole; candidate: NearbyPlace }

// 후보 객체에 고유 id가 없어서(NearbyPlace 참고) 좌표로 같은 장소인지 판단한다. 수정 화면은
// picks를 course_places에서 새로 만들어서(candidates 배열과 다른 객체 참조) === 비교로는
// "이미 담긴 후보"를 못 찾는다 — 좌표 비교로 바꿔서 생성/수정 화면 둘 다 정확히 맞게 한다.
function isSameCandidate(a: NearbyPlace, b: NearbyPlace) {
  return a.latitude === b.latitude && a.longitude === b.longitude
}

export function CourseCreatePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { placeId, courseId } = useParams<{ placeId?: string; courseId?: string }>()
  const isEdit = Boolean(courseId)
  const member = useAuthStore((state) => state.member)

  const [place, setPlace] = useState<PlaceDetail | undefined>(undefined)
  const [tab, setTab] = useState<CourseCategoryTab>('FOOD_CAFE')
  const [title, setTitle] = useState('')
  const [picks, setPicks] = useState<Pick[]>([])
  const [submitting, setSubmitting] = useState(false)
  // 수정 모드에서만 쓴다 — description은 화면에 입력 UI가 없어서, 기존 값을 그대로 들고 있다가
  // 제출할 때 같이 보낸다(PATCH가 title/description/course_places를 통째로 받기 때문).
  const [existingDescription, setExistingDescription] = useState('')

  useEffect(() => {
    if (!isEdit) {
      getPlaceDetail(Number(placeId))
        .then(setPlace)
        .catch(() => setPlace(undefined))
      return
    }
    getCourseDetail(Number(courseId))
      .then((course) => {
        // 작성자 본인이 아니면 수정 화면에 들어올 수 없다 — 상세 화면으로 돌려보낸다.
        if (!member || course.creator_nickname !== member.nickname) {
          navigate(`/courses/${courseId}`, { replace: true })
          return
        }
        setTitle(course.title)
        setExistingDescription(course.description)
        setPicks(
          course.course_places.map((coursePlace) => ({
            role: coursePlace.role,
            candidate: {
              place_name: coursePlace.name,
              address_name: coursePlace.address,
              road_address_name: coursePlace.road_address_name,
              latitude: coursePlace.latitude,
              longitude: coursePlace.longitude,
              category_name: coursePlace.category_name,
            },
          })),
        )
        getPlaceDetail(course.place_id)
          .then(setPlace)
          .catch(() => setPlace(undefined))
      })
      .catch(() => navigate('/mycourses', { replace: true }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [placeId, courseId, isEdit])

  const anchorLat = place?.latitude ? Number(place.latitude) : null
  const anchorLng = place?.longitude ? Number(place.longitude) : null

  const candidates = useMemo(
    () =>
      (place?.nearby_places ?? [])
        .filter((nearby) => classifyNearbyPlace(nearby.category_name) === tab)
        .slice(0, MAX_CANDIDATES_PER_TAB),
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
        const isPicked = prev.some((pick) => pick.role === role && isSameCandidate(pick.candidate, candidate))
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

  // 순서 변경 드래그는 그립 아이콘(핸들)에서만 시작한다 — 목록 자체를 스와이프해서 스크롤하는
  // 동작과 겹치지 않게 하려는 것.
  const dragSensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }))

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) {
      return
    }
    setPicks((prev) => {
      const oldIndex = prev.findIndex((pick) => pick.role === active.id)
      const newIndex = prev.findIndex((pick) => pick.role === over.id)
      if (oldIndex === -1 || newIndex === -1) {
        return prev
      }
      return arrayMove(prev, oldIndex, newIndex)
    })
  }

  const canSubmit = title.trim().length > 0 && picks.length === 3 && !submitting

  async function handleSubmit() {
    if (!canSubmit) {
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
      if (isEdit && courseId) {
        await updateCourse(Number(courseId), {
          title: title.trim(),
          description: existingDescription,
          course_places,
        })
        navigate(`/courses/${courseId}`, { replace: true })
      } else if (placeId) {
        const course = await createCourse(Number(placeId), { title: title.trim(), description: '', course_places })
        navigate(`/courses/${course.id}`, { replace: true })
      }
    } catch {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="-mb-6 grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-2">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <p className="text-center text-lg font-bold text-ink">
          {t(isEdit ? 'courseCreate.editTitle' : 'courseCreate.title')}
        </p>
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
              className="w-full rounded-sm border border-divider p-4 text-base text-ink outline-none"
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

          <div className="mx-4 flex flex-col gap-3 rounded-xl border border-divider bg-white p-4">
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

            <DndContext sensors={dragSensors} onDragEnd={handleDragEnd}>
              <SortableContext items={picks.map((pick) => pick.role)} strategy={verticalListSortingStrategy}>
                {picks.map((pick, index) => (
                  <SortablePickItem key={pick.role} pick={pick} index={index} onRemove={handleRemove} />
                ))}
              </SortableContext>
            </DndContext>
          </div>

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
                const isPicked = picks.some((pick) => pick.role === role && isSameCandidate(pick.candidate, candidate))
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

function SortablePickItem({
  pick,
  index,
  onRemove,
}: {
  pick: Pick
  index: number
  onRemove: (role: CoursePlaceRole) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: pick.role })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-3 bg-background ${isDragging ? 'z-10 opacity-90' : ''}`}
    >
      <button
        type="button"
        {...attributes}
        {...listeners}
        aria-label="순서 변경"
        className="touch-none text-ink-tertiary"
      >
        <GripVertical size={16} />
      </button>
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
        {index + 2}
      </span>
      <div className="flex-1">
        <p className="text-sm font-medium text-ink">{pick.candidate.place_name}</p>
        <p className="text-xs text-ink-secondary">{ROLE_LABEL[pick.role]}</p>
      </div>
      <button type="button" onClick={() => onRemove(pick.role)} aria-label="제거">
        <X size={18} className="text-ink-tertiary" />
      </button>
    </div>
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
  // 마커 클릭 시 뜨는 말풍선. 지도 화면(MapPage.tsx)의 말풍선과 모양·스타일을 통일한다.
  const infoOverlayRef = useRef<kakao.maps.CustomOverlay | null>(null)
  // 처음 지도가 뜰 때 딱 한 번만, 이미 골라둔 코스 구성(수정 화면 진입 시 미리 채워진 picks)이
  // 전부 보이게 범위를 맞춘다 — 그 뒤로 후보를 추가/제거할 때마다 지도가 움직이면 산만해서
  // 한 번만 하고 끝낸다.
  const hasFitBoundsRef = useRef(false)
  const [status, setStatus] = useState<'loading' | 'ready' | 'unavailable'>('loading')

  function showBubble(position: kakao.maps.LatLng, name: string) {
    const kakaoSdk = window.kakao
    const map = mapInstanceRef.current
    if (!kakaoSdk?.maps || !map) {
      return
    }
    infoOverlayRef.current?.setMap(null)
    const overlay = new kakaoSdk.maps.CustomOverlay({
      position,
      xAnchor: 0.5,
      yAnchor: 1.1,
      content: `
        <div class="relative">
          <div class="block whitespace-nowrap rounded-lg bg-white px-3 py-2 text-center text-xs font-medium text-ink shadow-md">
            ${name}
          </div>
          <span class="absolute left-1/2 top-full -translate-x-1/2 border-x-[6px] border-x-transparent border-t-[6px] border-t-white"></span>
        </div>
      `,
    })
    overlay.setMap(map)
    infoOverlayRef.current = overlay
  }

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
        const anchorMarker = new kakaoSdk.maps.Marker({
          position: center,
          map,
          title: anchor.name,
          image: new kakaoSdk.maps.MarkerImage(pinIconDataUrl(ANCHOR_PIN_COLOR, 1), new kakaoSdk.maps.Size(28, 36)),
        })
        kakaoSdk.maps.event.addListener(anchorMarker, 'click', () => showBubble(center, anchor.name))
        setStatus('ready')
      })
      .catch(() => setStatus('unavailable'))

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anchor.latitude, anchor.longitude, anchor.name])

  useEffect(() => {
    const kakaoSdk = window.kakao
    const map = mapInstanceRef.current
    if (status !== 'ready' || !kakaoSdk?.maps || !map) {
      return
    }

    markersRef.current.forEach((marker) => marker.setMap(null))
    markersRef.current = candidates.map((candidate) => {
      // pickIndex + 2가 "코스 구성" 목록의 순번(앙커=1, picks[0]=2, picks[1]=3...)과 같은 숫자다.
      const pickIndex = picks.findIndex((pick) => isSameCandidate(pick.candidate, candidate))
      const isPicked = pickIndex !== -1
      const position = new kakaoSdk.maps.LatLng(candidate.latitude, candidate.longitude)
      const marker = new kakaoSdk.maps.Marker({
        position,
        map,
        title: candidate.place_name ?? undefined,
        image: new kakaoSdk.maps.MarkerImage(
          pinIconDataUrl(isPicked ? PICKED_PIN_COLOR : CANDIDATE_PIN_COLOR, isPicked ? pickIndex + 2 : undefined),
          new kakaoSdk.maps.Size(28, 36),
        ),
      })
      kakaoSdk.maps.event.addListener(marker, 'click', () => {
        onToggle(candidate)
        showBubble(position, candidate.place_name ?? '')
      })
      return marker
    })

    if (!hasFitBoundsRef.current && picks.length > 0) {
      hasFitBoundsRef.current = true
      const bounds = new kakaoSdk.maps.LatLngBounds()
      bounds.extend(new kakaoSdk.maps.LatLng(anchor.latitude, anchor.longitude))
      picks.forEach((pick) => bounds.extend(new kakaoSdk.maps.LatLng(pick.candidate.latitude, pick.candidate.longitude)))
      map.setBounds(bounds)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidates, picks, onToggle, status])

  return (
    <div className="relative h-[280px] w-full overflow-hidden rounded-2xl bg-accent/15">
      <div ref={mapRef} className="h-full w-full" />
      {status !== 'ready' && (
        <div className="absolute inset-0 flex items-center justify-center bg-accent/15 text-sm text-ink-tertiary">
          {status === 'loading' ? '' : t('courseCreate.mapUnavailable')}
        </div>
      )}
    </div>
  )
}
