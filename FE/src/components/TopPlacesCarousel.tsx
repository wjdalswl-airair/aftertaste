import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getTopPlaces, type TopPlace } from '../api/main'
import spotPlaceholder from '../assets/placeholder/spot.png'
import { FavoriteButton } from './FavoriteButton'
import { PlaceholderImage } from './PlaceholderImage'
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

  // 제목에 줄바꿈(\n)이 있으면 두 줄로 나눠서 보여준다 (ko.json 참고).
  const [titleFirstLine, ...titleRestLines] = t('mainPage.topPlaces.title').split('\n')
  const titleSecondLine = titleRestLines.join('\n')

  return (
    <section>
      <h2 className="mb-3 px-4 text-ink">
        {titleSecondLine ? (
          <>
            <span className="block">
              <span className="inline-block rounded-full bg-accent mb-1.5 px-2 py-1 text-sm font-medium text-white">
                {titleFirstLine}
              </span>
            </span>
            <span className="block text-lg font-semibold text-ink">{titleSecondLine}</span>
          </>
        ) : (
          <span className="text-lg">{titleFirstLine}</span>
        )}
      </h2>

      {places === undefined && (
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

      {places?.length === 0 && (
        <p className="px-4 text-sm text-ink-tertiary">{t('mainPage.topPlaces.empty')}</p>
      )}

      {places && places.length > 0 && (
        <div className="scrollbar-hide flex snap-x snap-mandatory gap-3 overflow-x-auto px-4">
          {places.map((place) => (
            <Link key={place.id} to={`/spots/${place.id}`} className="w-[110px] flex-shrink-0 snap-center">
              <div className="relative">
                <PlaceholderImage
                  src={place.photo_url}
                  placeholder={spotPlaceholder}
                  alt=""
                  className="aspect-square w-full rounded-lg"
                />
                <FavoriteButton placeId={place.id} initialFavorited={place.is_favorited} />
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
