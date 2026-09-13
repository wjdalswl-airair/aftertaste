import { Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { searchPlaces, type WorkSearchResult } from '../api/search'
import { getMapPlaces, type MapPlace } from '../api/spots'
import { getWorkDetail } from '../api/works'
import { BottomNav } from '../components/BottomNav'
import { LocationPermissionModal } from '../components/LocationPermissionModal'
import { useGeolocation } from '../hooks/useGeolocation'
import { loadKakaoMaps, pinIconDataUrl } from '../lib/kakaoMap'

// index.css의 --color-primary와 맞춘 값 (다른 지도 화면과 동일 톤, SpotDetailPage.tsx 참고).
const MAP_PIN_COLOR = '#f47c5c'

// 위치 권한이 아직 없거나 거부됐을 때 쓰는 기본 중심 — 서울시청 (2026-09-13 사용자 결정).
const DEFAULT_CENTER = { lat: 37.5665, lng: 126.978 }

// 전체 명소를 카카오맵에 클러스터링해서 보여주는 화면. 축소하면 개수 뱃지로 묶이고,
// 확대하면 개별 마커로 흩어진다(카카오 MarkerClusterer 기본 동작, 커스텀 로직 없음).
// 지도 위 검색창에서 작품을 고르면 그 작품이 촬영된 명소만 걸러서 보여준다.
export function MapPage() {
  const { t } = useTranslation()
  const { coords, showConsentModal, handleAllow, handleDeny } = useGeolocation()
  // undefined: 로딩 중, []: 응답은 왔는데 명소 없음(또는 API 실패)
  const [places, setPlaces] = useState<MapPlace[] | undefined>(undefined)

  const [workQuery, setWorkQuery] = useState('')
  const [workSuggestions, setWorkSuggestions] = useState<WorkSearchResult[]>([])
  const [selectedWork, setSelectedWork] = useState<WorkSearchResult | null>(null)
  // null: 필터 없음(전체 명소), 배열: 선택된 작품이 촬영된 명소 id만
  const [filteredPlaceIds, setFilteredPlaceIds] = useState<number[] | null>(null)
  // 값이 바뀔 때만 지도를 필터된 명소들에 맞춰 재중심/재확대한다 (매 렌더마다 하면 사용자가
  // 지도를 움직인 것까지 계속 덮어써버린다).
  const [fitTrigger, setFitTrigger] = useState(0)

  useEffect(() => {
    getMapPlaces()
      .then(setPlaces)
      .catch(() => setPlaces([]))
  }, [])

  // 작품 제목 자동완성 — 통합검색(WORK)을 그대로 재사용한다(SearchPage.tsx와 동일 패턴).
  useEffect(() => {
    const trimmed = workQuery.trim()
    if (!trimmed || selectedWork) {
      setWorkSuggestions([])
      return
    }
    const timer = setTimeout(() => {
      searchPlaces(trimmed, 'WORK')
        .then((result) => setWorkSuggestions(result.works))
        .catch(() => setWorkSuggestions([]))
    }, 300)
    return () => clearTimeout(timer)
  }, [workQuery, selectedWork])

  function handleSelectWork(work: WorkSearchResult) {
    setSelectedWork(work)
    setWorkQuery(work.title)
    setWorkSuggestions([])
    // 작품에 연결된 명소는 id·이름 정도만 온다(주소·사진뿐, 좌표 없음) — 이미 받아둔
    // 전체 명소 목록(좌표 포함)과 id로 대조해서 걸러 쓴다. BE 호출을 늘리지 않는다.
    getWorkDetail(work.id)
      .then((detail) => {
        setFilteredPlaceIds(detail.places.map((place) => place.id))
        setFitTrigger((prev) => prev + 1)
      })
      .catch(() => setFilteredPlaceIds([]))
  }

  function handleClearWork() {
    setSelectedWork(null)
    setWorkQuery('')
    setWorkSuggestions([])
    setFilteredPlaceIds(null)
  }

  const visiblePlaces =
    filteredPlaceIds === null ? places : places?.filter((place) => filteredPlaceIds.includes(place.id))

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="grid grid-cols-[1fr_auto_1fr] items-center px-4 pt-4">
        <Link to="/" className="font-brand text-2xl font-bold text-primary">여운</Link>
        <h1 className="text-lg font-bold text-ink">{t('mapPage.title')}</h1>
        <div />
      </header>

      <div className="px-4">
        <div className="relative">
          <div className="absolute inset-x-3 top-3 z-10">
            <div className="flex items-center gap-2 rounded-lg bg-white p-4 shadow-md">
              <Search size={16} className="text-ink-tertiary" />
              <input
                type="text"
                value={workQuery}
                onChange={(event) => {
                  setWorkQuery(event.target.value)
                  if (selectedWork) {
                    setSelectedWork(null)
                    setFilteredPlaceIds(null)
                  }
                }}
                placeholder={t('mapPage.workSearchPlaceholder')}
                className="flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-tertiary"
              />
              {selectedWork && (
                <button type="button" onClick={handleClearWork} aria-label="필터 해제">
                  <X size={16} className="text-ink-tertiary" />
                </button>
              )}
            </div>

            {workSuggestions.length > 0 && (
              <div className="mt-1 flex flex-col rounded-2xl bg-white p-1 shadow-md">
                {workSuggestions.map((work) => (
                  <button
                    key={work.id}
                    type="button"
                    onClick={() => handleSelectWork(work)}
                    className="rounded-xl px-3 py-2 text-left text-sm text-ink"
                  >
                    {work.title}
                  </button>
                ))}
              </div>
            )}

            {filteredPlaceIds?.length === 0 && (
              <p className="mt-2 rounded-2xl bg-white px-3 py-2 text-center text-xs text-ink-tertiary shadow-md">
                {t('mapPage.workEmpty')}
              </p>
            )}
          </div>

          <SpotsMap places={visiblePlaces} coords={coords} fitTrigger={fitTrigger} />
        </div>
      </div>

      {showConsentModal && <LocationPermissionModal onAllow={handleAllow} onDeny={handleDeny} />}

      <BottomNav />
    </main>
  )
}

function SpotsMap({
  places,
  coords,
  fitTrigger,
}: {
  places: MapPlace[] | undefined
  coords: { lat: number; lng: number } | null
  fitTrigger: number
}) {
  const { t } = useTranslation()
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<kakao.maps.Map | null>(null)
  const clustererRef = useRef<kakao.maps.MarkerClusterer | null>(null)
  const infoWindowRef = useRef<kakao.maps.InfoWindow | null>(null)
  // 위치 권한이 허용된 순간 딱 한 번만 사용자 위치로 재중심한다 — 안 그러면 GPS 좌표가
  // 미세하게 갱신될 때마다, 혹은 사용자가 지도를 직접 움직인 뒤에도 자꾸 되돌아간다.
  const recenteredRef = useRef(false)
  // 마지막으로 처리한 fitTrigger 값 — 바뀐 경우에만 지도를 명소들에 맞춰 재조정한다.
  const lastFitTriggerRef = useRef(0)
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
        const center = new kakaoSdk.maps.LatLng(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng)
        mapInstanceRef.current = new kakaoSdk.maps.Map(mapRef.current, { center, level: 8 })
        setStatus('ready')
      })
      .catch(() => setStatus('unavailable'))

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (status !== 'ready' || !coords || recenteredRef.current || !map) {
      return
    }
    recenteredRef.current = true
    map.setCenter(new window.kakao.maps.LatLng(coords.lat, coords.lng))
  }, [status, coords])

  useEffect(() => {
    const kakaoSdk = window.kakao
    const map = mapInstanceRef.current
    if (status !== 'ready' || !kakaoSdk?.maps || !map || !places) {
      return
    }

    clustererRef.current?.clear()
    const clusterer = new kakaoSdk.maps.MarkerClusterer({
      map,
      gridSize: 60,
      averageCenter: true,
      minLevel: 6,
    })
    clustererRef.current = clusterer

    const positions: kakao.maps.LatLng[] = []
    const markers = places.map((place) => {
      const position = new kakaoSdk.maps.LatLng(place.latitude, place.longitude)
      positions.push(position)
      const marker = new kakaoSdk.maps.Marker({
        position,
        title: place.name,
        image: new kakaoSdk.maps.MarkerImage(pinIconDataUrl(MAP_PIN_COLOR), new kakaoSdk.maps.Size(28, 36)),
      })
      kakaoSdk.maps.event.addListener(marker, 'click', () => {
        infoWindowRef.current?.close()
        const infoWindow = new kakaoSdk.maps.InfoWindow({
          content: `
            <a href="/spots/${place.id}" class="block px-3 py-2 text-center text-xs font-medium text-ink no-underline">
              ${place.name}
            </a>
          `,
        })
        infoWindow.open(map, marker)
        infoWindowRef.current = infoWindow
      })
      return marker
    })
    clusterer.addMarkers(markers)

    // 작품 필터가 새로 선택된 경우에만(fitTrigger 변경) 그 명소들이 다 보이게 지도 범위를
    // 맞춘다 — 전체 명소를 처음 불러왔을 때는 기본 중심(서울/내 위치)을 그대로 유지한다.
    if (fitTrigger !== lastFitTriggerRef.current) {
      lastFitTriggerRef.current = fitTrigger
      if (positions.length > 0) {
        const bounds = new kakaoSdk.maps.LatLngBounds()
        positions.forEach((position) => bounds.extend(position))
        map.setBounds(bounds)
      }
    }
  }, [places, status, fitTrigger])

  return (
    <div className="relative h-[80dvh] w-full overflow-hidden bg-accent/15">
      <div ref={mapRef} className="h-full w-full" />
      {status !== 'ready' && (
        <div className="absolute inset-0 flex items-center justify-center bg-accent/15 text-sm text-ink-tertiary">
          {status === 'loading' ? '' : t('mapPage.unavailable')}
        </div>
      )}
    </div>
  )
}
