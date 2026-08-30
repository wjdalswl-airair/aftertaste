import { Star, X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

type RatingModalProps = {
  place: { name: string; photo_url: string }
  onClose: () => void
  // 별점만 고르고 넘어간다 — 서버 호출은 여기서 안 하고, 리뷰 작성 화면에서 텍스트까지
  // 채운 뒤 한 번에 등록한다 (BE가 content 없는 리뷰를 안 받아줌).
  onNext: (rating: number) => void
}

// 명소 상세의 "별점 남기기" 버튼을 누르면 뜨는 첫 단계 모달 (Figma node-id 102:687).
export function RatingModal({ place, onClose, onNext }: RatingModalProps) {
  const { t } = useTranslation()
  const [rating, setRating] = useState(0)

  return (
    <div className="fixed inset-0 z-50 mx-auto w-full max-w-[480px]">
      <button type="button" aria-label="닫기" className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="absolute inset-0 flex items-center justify-center px-6">
        <div className="relative w-full rounded-3xl bg-white px-6 pb-8 pt-6 text-center">
          <button type="button" onClick={onClose} aria-label="닫기" className="absolute right-5 top-5">
            <X size={24} className="text-ink" />
          </button>

          <img
            src={place.photo_url}
            alt=""
            className="mx-auto h-[74px] w-[75px] rounded-2xl bg-divider object-cover"
          />
          <p className="mt-4 text-base font-bold text-ink">{place.name}</p>
          <p className="mt-1 text-xs text-ink-tertiary">{t('ratingModal.question')}</p>

          <div className="mt-5 flex items-center justify-center gap-1.5">
            {[1, 2, 3, 4, 5].map((value) => (
              <button key={value} type="button" onClick={() => setRating(value)} aria-label={`${value}점`}>
                <Star
                  size={32}
                  className={value <= rating ? 'fill-primary text-primary' : 'text-ink-tertiary'}
                />
              </button>
            ))}
          </div>

          <button
            type="button"
            disabled={rating === 0}
            onClick={() => onNext(rating)}
            className="mt-6 w-full rounded-full bg-primary py-3 text-sm font-bold text-white disabled:opacity-40"
          >
            {t('ratingModal.submitButton')}
          </button>
          <p className="mt-3 text-[11px] text-ink-tertiary">{t('ratingModal.hint')}</p>
        </div>
      </div>
    </div>
  )
}
