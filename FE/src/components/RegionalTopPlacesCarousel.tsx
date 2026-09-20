import { ChevronDown } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getTopPlacesByRegion, type RegionTopPlaces } from '../api/main'
import spotPlaceholder from '../assets/placeholder/spot.png'
import { BottomSheet } from './BottomSheet'
import { FavoriteButton } from './FavoriteButton'
import { PlaceholderImage } from './PlaceholderImage'
import { Skeleton } from './Skeleton'

// 드롭다운엔 축약형을 보여주고, BE 응답(`places/regions.py`의 정식 명칭)과 매칭할 땐 official을 쓴다.
// 지역명은 번역하지 않고 한글 그대로 쓴다 — BE가 주는 명소 이름/주소도 이미 번역 없이
// 한글 그대로 쓰는 것과 같은 성격의 갭이다 (docs/DETAIL_SPEC.md 참고).
const REGIONS: { short: string; official: string }[] = [
  { short: '서울', official: '서울특별시' },
  { short: '부산', official: '부산광역시' },
  { short: '대구', official: '대구광역시' },
  { short: '인천', official: '인천광역시' },
  { short: '광주', official: '광주광역시' },
  { short: '대전', official: '대전광역시' },
  { short: '울산', official: '울산광역시' },
  { short: '세종', official: '세종특별자치시' },
  { short: '경기', official: '경기도' },
  { short: '강원', official: '강원특별자치도' },
  { short: '충북', official: '충청북도' },
  { short: '충남', official: '충청남도' },
  { short: '전북', official: '전북특별자치도' },
  { short: '전남', official: '전라남도' },
  { short: '경북', official: '경상북도' },
  { short: '경남', official: '경상남도' },
  { short: '제주', official: '제주특별자치도' },
]

export function RegionalTopPlacesCarousel() {
  const { t } = useTranslation()
  const [region, setRegion] = useState(REGIONS[0])
  const [open, setOpen] = useState(false)
  // undefined: 로딩 중, []: 확인 끝났는데 즐겨찾기 있는 지역이 하나도 없음
  const [regionsData, setRegionsData] = useState<RegionTopPlaces[] | undefined>(undefined)

  // 지역을 바꿀 때마다 다시 부르지 않는다 — 화면 진입 시 딱 한 번만 불러서 전체 지역
  // 데이터를 들고 있고, 드롭다운 선택은 그 안에서 골라 보여주기만 한다 (docs/troubleshooting.md 참고).
  useEffect(() => {
    getTopPlacesByRegion()
      .then(setRegionsData)
      .catch(() => setRegionsData([]))
  }, [])

  const places = regionsData?.find((entry) => entry.region === region.official)?.places ?? []

  return (
    <section>
      <div className="mb-3 flex items-center justify-between px-4">
        <h2 className="text-lg font-bold text-ink">{t('mainPage.regionalTop.title')}</h2>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex items-center gap-1 text-sm text-ink-secondary"
          aria-label={t('mainPage.regionalTop.selectRegion')}
        >
          {region.short}
          <ChevronDown size={16} />
        </button>
      </div>

      {regionsData === undefined && (
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

      {regionsData && places.length === 0 && (
        <p className="px-4 text-sm text-ink-tertiary">{t('mainPage.regionalTop.empty')}</p>
      )}

      {regionsData && places.length > 0 && (
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

      {open && (
        <BottomSheet onClose={() => setOpen(false)}>
          <div className="max-h-[60dvh] overflow-y-auto">
            {REGIONS.map((option) => (
              <button
                key={option.short}
                type="button"
                onClick={() => {
                  setRegion(option)
                  setOpen(false)
                }}
                className={`block w-full py-4 text-center text-[15px] font-medium ${
                  option.short === region.short ? 'text-primary' : 'text-ink'
                }`}
              >
                {option.short}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="mt-2 block w-full py-3 text-center text-sm text-ink-tertiary"
          >
            취소
          </button>
        </BottomSheet>
      )}
    </section>
  )
}
