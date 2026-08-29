import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getHallOfFame, type HallOfFameReview } from '../api/main'

export function HallOfFameCard() {
  const { t } = useTranslation()
  // undefined: 아직 로딩 중, null: 로딩 끝났지만 데이터 없음(정상)
  const [review, setReview] = useState<HallOfFameReview | null | undefined>(undefined)

  useEffect(() => {
    getHallOfFame()
      .then(setReview)
      .catch(() => setReview(null))
  }, [])

  return (
    <section className="px-4">
      <h2 className="mb-3 text-lg font-bold text-ink">{t('mainPage.hallOfFame.title')}</h2>
      {review ? (
        <div className="overflow-hidden rounded-lg border border-divider">
          {review.photos[0] && (
            <img src={review.photos[0].photo_url} alt="" className="aspect-video w-full object-cover" />
          )}
          <div className="p-3">
            <p className="text-ink">{review.content}</p>
            <p className="mt-1 text-sm text-ink-secondary">{review.author_nickname}</p>
          </div>
        </div>
      ) : (
        review === null && (
          <p className="rounded-lg border border-divider p-6 text-center text-sm text-ink-tertiary">
            {t('mainPage.hallOfFame.empty')}
          </p>
        )
      )}
    </section>
  )
}
