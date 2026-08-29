import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getRecommendedSpots, type RecommendedSpot } from '../api/spots'
import { useGeolocation } from '../hooks/useGeolocation'

export function RecommendedSpots() {
  const { t } = useTranslation()
  const { status, coords } = useGeolocation()
  const [spots, setSpots] = useState<RecommendedSpot[]>([])

  useEffect(() => {
    if (status === 'pending') {
      return
    }
    getRecommendedSpots(coords ?? undefined)
      .then(setSpots)
      .catch(() => setSpots([]))
  }, [status, coords])

  if (spots.length === 0) {
    return null
  }

  return (
    <section className="px-4">
      <h2 className="mb-3 text-lg font-bold text-ink">{t('mainPage.recommend.title')}</h2>
      <div className="flex flex-col gap-3">
        {spots.map((spot) => (
          <div key={spot.id} className="flex items-center gap-3 rounded-lg border border-divider p-3">
            <img
              src={spot.photo_url}
              alt=""
              className="h-16 w-16 flex-shrink-0 rounded-md object-cover"
            />
            <div>
              <p className="text-ink">{spot.name}</p>
              <p className="text-sm text-ink-secondary">{spot.address}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
