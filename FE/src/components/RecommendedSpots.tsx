import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getRecommendedSpots, type RecommendedSpot } from '../api/spots'
import spotPlaceholder from '../assets/placeholder/spot.png'
import { FavoriteButton } from './FavoriteButton'
import { PlaceholderImage } from './PlaceholderImage'
import { Skeleton } from './Skeleton'
import { getDongName } from '../lib/kakaoMap'

type Props = {
  status: 'pending' | 'granted' | 'denied'
  coords: { lat: number; lng: number } | null
}

// 위치 권한 요청(useGeolocation)은 MainPage가 하나만 소유한다 — WeatherWidget도 같은 위치
// 정보를 쓰는데, 컴포넌트마다 훅을 따로 부르면 동의 모달이 중복으로 뜰 수 있어서
// status/coords를 props로 받는 방식으로 바꿨다 (2026-09-20, 날씨 위젯 추가하며 리팩터).
export function RecommendedSpots({ status, coords }: Props) {
  const { t } = useTranslation()
  // undefined: 로딩 중, []: 확인 끝났는데 추천 없음
  const [spots, setSpots] = useState<RecommendedSpot[] | undefined>(undefined)
  // 좌표를 "역삼동" 같은 동 이름으로 바꾼 값. 못 가져오면 null(기존 "내 주변 명소" 문구로 대체).
  const [dongName, setDongName] = useState<string | null>(null)

  useEffect(() => {
    // 위치 거부 시엔 이 섹션 자체를 안 보여주므로(아래 return 참고) 굳이 호출할 필요 없다.
    if (status === 'pending' || status === 'denied') {
      return
    }
    getRecommendedSpots(coords ?? undefined)
      .then(setSpots)
      .catch(() => setSpots([]))
  }, [status, coords])

  useEffect(() => {
    if (status !== 'granted' || !coords) {
      setDongName(null)
      return
    }
    getDongName(coords.lat, coords.lng).then(setDongName)
  }, [status, coords])

  // 위치 거부 시엔 "내 주변 명소"를 안 보여준다 — 아래에 이미 있는 "전국 Top10" 섹션이
  // 그 역할을 대신한다 (2026-09-06 사용자 결정).
  if (status === 'denied') {
    return null
  }

  return (
    <section>
      <h2 className="mb-3 px-4 text-lg font-bold text-ink">
        {dongName ? t('mainPage.recommend.titleNearby', { dong: dongName }) : t('mainPage.recommend.title')}
      </h2>

      {(spots === undefined || status === 'pending') && (
        <div className="flex gap-3 px-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-[110px] flex-shrink-0">
              <Skeleton className="aspect-square w-full rounded-lg" />
              <Skeleton className="mt-1 h-3 w-full rounded-sm" />
              <Skeleton className="mt-1 h-3 w-2/3 rounded-sm" />
            </div>
          ))}
        </div>
      )}

      {spots?.length === 0 && status !== 'pending' && (
        <p className="px-4 text-sm text-ink-tertiary">{t('mainPage.recommend.empty')}</p>
      )}

      {spots && spots.length > 0 && (
        <div className="scrollbar-hide flex snap-x snap-mandatory gap-3 overflow-x-auto px-4">
          {spots.map((spot) => (
            <Link key={spot.id} to={`/spots/${spot.id}`} className="w-[110px] flex-shrink-0 snap-center">
              <div className="relative">
                <PlaceholderImage
                  src={spot.photo_url}
                  placeholder={spotPlaceholder}
                  alt=""
                  className="aspect-square w-full rounded-lg"
                />
                <FavoriteButton placeId={spot.id} initialFavorited={spot.is_favorited} />
              </div>
              <p className="mt-1 truncate text-xs text-ink">{spot.name}</p>
              <p className="truncate text-[11px] text-ink-secondary">{spot.address}</p>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
