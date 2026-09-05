import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getRecommendedSpots, type RecommendedSpot } from '../api/spots'
import { useGeolocation } from '../hooks/useGeolocation'
import { FavoriteButton } from './FavoriteButton'
import { LocationPermissionModal } from './LocationPermissionModal'
import { Skeleton } from './Skeleton'
import { getDongName } from '../lib/kakaoMap'

export function RecommendedSpots() {
  const { t } = useTranslation()
  const { status, coords, showConsentModal, handleAllow, handleDeny } = useGeolocation()
  // undefined: 로딩 중, []: 확인 끝났는데 추천 없음
  const [spots, setSpots] = useState<RecommendedSpot[] | undefined>(undefined)
  // 좌표를 "역삼동" 같은 동 이름으로 바꾼 값. 못 가져오면 null(기존 "내 주변 명소" 문구로 대체).
  const [dongName, setDongName] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'pending') {
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

  return (
    <section>
      <h2 className="mb-3 px-4 text-lg font-bold text-ink">
        {dongName ? t('mainPage.recommend.titleNearby', { dong: dongName }) : t('mainPage.recommend.title')}
      </h2>

      {(spots === undefined || status === 'pending') && (
        <div className="flex gap-3 px-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-[110px] flex-shrink-0">
              <Skeleton className="aspect-square w-full rounded-md" />
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
                <img src={spot.photo_url} alt="" className="aspect-square w-full rounded-md object-cover" />
                <FavoriteButton placeId={spot.id} />
              </div>
              <p className="mt-1 truncate text-xs text-ink">{spot.name}</p>
              <p className="truncate text-[11px] text-ink-secondary">{spot.address}</p>
            </Link>
          ))}
        </div>
      )}

      {showConsentModal && <LocationPermissionModal onAllow={handleAllow} onDeny={handleDeny} />}
    </section>
  )
}
