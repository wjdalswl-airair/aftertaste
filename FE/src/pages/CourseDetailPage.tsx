import { ArrowLeft, MoreHorizontal, Share2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { deleteCourse, getCourseDetail, type Course, type CoursePlaceRole } from '../api/courses'
import { getPlaceDetail, type PlaceDetail } from '../api/spots'
import { BottomNav } from '../components/BottomNav'
import { FavoriteButton } from '../components/FavoriteButton'
import { Skeleton } from '../components/Skeleton'
import { loadKakaoMaps } from '../lib/kakaoMap'
import { useAuthStore } from '../store/useAuthStore'
import { getDistanceKm } from '../utils/distance'

const ROLE_LABEL: Record<CoursePlaceRole, string> = {
  RESTAURANT: '맛집',
  CAFE: '카페',
  OTHER: '주변 명소',
}

// anchor place의 address 앞 두 토큰을 짧은 지역명으로 쓴다 (예: "경기도 수원시..." → "경기 수원").
// BE 응답엔 지역명 필드가 따로 없어서 임시로 이렇게 잘라 쓴다.
function shortRegion(address: string): string {
  return address.split(' ').slice(0, 2).join(' ')
}

function formatDate(isoString: string) {
  const date = new Date(isoString)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}.${pad(date.getMonth() + 1)}.${pad(date.getDate())}`
}

export function CourseDetailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { courseId } = useParams<{ courseId: string }>()
  const member = useAuthStore((state) => state.member)

  // undefined: 로딩 중, null: 존재하지 않음
  const [course, setCourse] = useState<Course | null | undefined>(undefined)
  const [place, setPlace] = useState<PlaceDetail | undefined>(undefined)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    setCourse(undefined)
    setPlace(undefined)
    getCourseDetail(Number(courseId))
      .then((data) => {
        setCourse(data)
        getPlaceDetail(data.place_id)
          .then(setPlace)
          .catch(() => setPlace(undefined))
      })
      .catch(() => setCourse(null))
  }, [courseId])

  function handleShare() {
    navigator.clipboard.writeText(window.location.href).catch(() => {})
  }

  async function handleDelete() {
    if (!course) {
      return
    }
    await deleteCourse(course.id).catch(() => {})
    navigate('/mycourses', { replace: true })
  }

  // BE 응답에 "내가 만든 코스인지" 여부 필드가 없어서, 리뷰와 같은 방식으로 닉네임 비교로 임시 판단한다.
  const isMine = Boolean(member && course && course.creator_nickname === member.nickname)

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_auto] items-center px-4 pt-6">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <p className="truncate text-center text-lg font-bold text-ink">{course?.title}</p>
        <div className="flex items-center gap-3 justify-self-end">
          {course && (
            <FavoriteButton
              placeId={course.id}
              type="course"
              size={20}
              className="relative rounded-full p-0.5"
            />
          )}
          <button type="button" onClick={handleShare} aria-label="공유">
            <Share2 size={20} className="text-ink" />
          </button>
          {isMine && (
            <button type="button" onClick={() => setMenuOpen(true)} aria-label="더보기">
              <MoreHorizontal size={20} className="text-ink" />
            </button>
          )}
        </div>
      </header>

      {course === undefined && <CourseDetailSkeleton />}

      {course === null && <p className="px-4 py-20 text-center text-ink-tertiary">{t('courseDetail.notFound')}</p>}

      {course && (
        <>
          <p className="px-4 text-sm text-ink-tertiary">
            {place && `${shortRegion(place.address)} · `}
            {course.course_places.length + 1}
            {t('courseDetail.placesCountSuffix')} · {formatDate(course.created_at)}
          </p>

          <div className="px-4">
            <CourseMap course={course} place={place} />
          </div>

          <section className="flex flex-col gap-4 px-4">
            {place && (
              <div className="flex items-center gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
                  1
                </span>
                <div>
                  <p className="text-sm font-medium text-ink">{place.name}</p>
                  {place.works[0] && <p className="text-xs text-ink-secondary">{place.works[0].work.title}</p>}
                </div>
              </div>
            )}
            {course.course_places.map((coursePlace, index) => (
              <div key={coursePlace.id} className="flex items-center gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
                  {index + 2}
                </span>
                <div>
                  <p className="text-sm font-medium text-ink">{coursePlace.name}</p>
                  <p className="text-xs text-ink-secondary">
                    {ROLE_LABEL[coursePlace.role]}
                    {place &&
                      place.latitude &&
                      place.longitude &&
                      ` · ${getDistanceKm(
                        Number(place.latitude),
                        Number(place.longitude),
                        coursePlace.latitude,
                        coursePlace.longitude,
                      ).toFixed(1)}km`}
                  </p>
                </div>
              </div>
            ))}
          </section>
        </>
      )}

      {menuOpen && course && (
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
              <button
                type="button"
                onClick={handleDelete}
                className="block w-full py-4 text-center text-[15px] font-medium text-[#e0574a]"
              >
                {t('courseDetail.delete')}
              </button>
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                className="mt-2 block w-full py-3 text-center text-ink-tertiary"
              >
                {t('courseDetail.cancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </main>
  )
}

function CourseMap({ course, place }: { course: Course; place: PlaceDetail | undefined }) {
  const mapRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'unavailable'>('loading')

  const lat = place?.latitude ? Number(place.latitude) : null
  const lng = place?.longitude ? Number(place.longitude) : null
  const hasCoords = lat !== null && lng !== null && !Number.isNaN(lat) && !Number.isNaN(lng)

  useEffect(() => {
    if (!hasCoords || !place) {
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
        const map = new kakaoSdk.maps.Map(mapRef.current, { center, level: 5 })
        new kakaoSdk.maps.Marker({ position: center, map, title: place.name })

        course.course_places.forEach((coursePlace) => {
          new kakaoSdk.maps.Marker({
            position: new kakaoSdk.maps.LatLng(coursePlace.latitude, coursePlace.longitude),
            map,
            title: coursePlace.name,
          })
        })

        setStatus('ready')
      })
      .catch(() => setStatus('unavailable'))

    return () => {
      cancelled = true
    }
  }, [course, hasCoords, lat, lng, place])

  return (
    <div className="relative h-[200px] w-full overflow-hidden rounded-2xl bg-accent/15">
      <div ref={mapRef} className="h-full w-full" />
      {status !== 'ready' && (
        <div className="absolute inset-0 flex items-center justify-center bg-accent/15 text-sm text-ink-tertiary" />
      )}
    </div>
  )
}

function CourseDetailSkeleton() {
  return (
    <div className="flex flex-col gap-4 px-4">
      <Skeleton className="h-4 w-40 rounded-sm" />
      <Skeleton className="h-[200px] w-full rounded-2xl" />
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-6 w-6 rounded-full" />
          <div className="flex flex-1 flex-col gap-1.5">
            <Skeleton className="h-3 w-1/2 rounded-sm" />
            <Skeleton className="h-3 w-1/3 rounded-sm" />
          </div>
        </div>
      ))}
    </div>
  )
}
