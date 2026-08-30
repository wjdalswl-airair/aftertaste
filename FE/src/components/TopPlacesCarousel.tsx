import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getTopPlaces, type TopPlace } from '../api/main'
import { FavoriteButton } from './FavoriteButton'
import { Skeleton } from './Skeleton'

export function TopPlacesCarousel() {
  const { t } = useTranslation()
  // undefined: 로딩 중, []: 확인 끝났는데 Top10 없음
  const [places, setPlaces] = useState<TopPlace[] | undefined>(undefined)

  useEffect(() => {
    getTopPlaces()
      .then(setPlaces)
      .catch(() => setPlaces([]))
  }, [])

  return (
    <section>
      <h2 className="mb-3 px-4 text-lg font-bold text-ink">{t('mainPage.topPlaces.title')}</h2>

      {places === undefined && (
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

      {places?.length === 0 && (
        <p className="px-4 text-sm text-ink-tertiary">{t('mainPage.topPlaces.empty')}</p>
      )}

      {places && places.length > 0 && (
        <div className="scrollbar-hide flex snap-x snap-mandatory gap-3 overflow-x-auto px-4">
          {places.map((place) => (
            <Link key={place.id} to={`/spots/${place.id}`} className="w-[110px] flex-shrink-0 snap-center">
              <div className="relative">
                <img src={place.photo_url} alt="" className="aspect-square w-full rounded-md object-cover" />
                <FavoriteButton placeId={place.id} />
              </div>
              <p className="mt-1 truncate text-xs text-ink">{place.name}</p>
              <p className="truncate text-[11px] text-ink-secondary">{place.address}</p>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
