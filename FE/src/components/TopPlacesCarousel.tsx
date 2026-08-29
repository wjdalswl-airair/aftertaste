import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getTopPlaces, type TopPlace } from '../api/main'

export function TopPlacesCarousel() {
  const { t } = useTranslation()
  const [places, setPlaces] = useState<TopPlace[]>([])

  useEffect(() => {
    getTopPlaces()
      .then(setPlaces)
      .catch(() => setPlaces([]))
  }, [])

  if (places.length === 0) {
    return null
  }

  return (
    <section>
      <h2 className="mb-3 px-4 text-lg font-bold text-ink">{t('mainPage.topPlaces.title')}</h2>
      <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto px-4">
        {places.map((place) => (
          <div key={place.id} className="w-32 flex-shrink-0 snap-center">
            <img
              src={place.photo_url}
              alt=""
              className="aspect-square w-full rounded-lg object-cover"
            />
            <p className="mt-1 truncate text-sm text-ink">{place.name}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
