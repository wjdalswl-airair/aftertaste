import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getBanners, getHallOfFame, type Banner, type HallOfFameReview } from '../api/main'
import { getPlaceDetail, getRecommendedSpots, type PlaceDetail, type RecommendedSpot } from '../api/spots'
import { Skeleton } from './Skeleton'

type Slide =
  | { type: 'hallOfFame'; review: HallOfFameReview; place: PlaceDetail | null }
  | { type: 'recommend'; spot: RecommendedSpot }

const AUTO_ADVANCE_MS = 4000

export function Hero() {
  const { t } = useTranslation()
  // undefined: 로딩 중, []: 명예의전당·추천 둘 다 없음(배너로 대체)
  const [slides, setSlides] = useState<Slide[] | undefined>(undefined)
  const [banners, setBanners] = useState<Banner[] | undefined>(undefined)
  const [activeIndex, setActiveIndex] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  const scrollEndTimer = useRef<number>(undefined)

  useEffect(() => {
    Promise.all([getHallOfFame().catch(() => null), getRecommendedSpots().catch(() => [])]).then(
      ([review, spots]) => {
        const built: Slide[] = []

        // 명소 이름·작품명은 GET /api/places/{id}/를 한 번 더 불러야 하는데, 이 API가 주변
        // 상권을 실시간으로 카카오에 물어봐서 유독 느리다(약 1.3초, 2026-09-08 측정). 이걸
        // 기다렸다가 슬라이드를 보여주면 사진·리뷰가 이미 있는데도 배너 전체가 그만큼 늦게
        // 뜬다 — 그래서 place는 일단 null로 먼저 보여주고, 도착하면 그때 채워 넣는다.
        if (review) {
          built.push({ type: 'hallOfFame', review, place: null })
        }
        if (spots[0]) {
          built.push({ type: 'recommend', spot: spots[0] })
        }

        setSlides(built)
        if (built.length === 0) {
          getBanners()
            .then(setBanners)
            .catch(() => setBanners([]))
        }

        if (review) {
          getPlaceDetail(review.place)
            .then((place) => {
              setSlides((prev) =>
                prev?.map((slide) => (slide.type === 'hallOfFame' ? { ...slide, place } : slide)),
              )
            })
            .catch(() => {})
        }
      },
    )
  }, [])

  // 몇 초마다 다음 슬라이드로 자동 전환한다 (슬라이드가 2개 이상일 때만).
  useEffect(() => {
    if (!slides || slides.length < 2) {
      return
    }
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % slides.length)
    }, AUTO_ADVANCE_MS)
    return () => clearInterval(timer)
  }, [slides])

  useEffect(() => {
    scrollRef.current?.scrollTo({ left: activeIndex * scrollRef.current.clientWidth, behavior: 'smooth' })
  }, [activeIndex])

  // 스크롤이 완전히 멈춘 뒤에만 활성 슬라이드를 확정한다.
  // (스크롤 도중에 매번 계산하면, 자동 전환으로 움직이는 중간에도 값이 튀어서 원래 자리로 되돌아가 버린다)
  function handleScroll() {
    window.clearTimeout(scrollEndTimer.current)
    scrollEndTimer.current = window.setTimeout(() => {
      if (!scrollRef.current) {
        return
      }
      const index = Math.round(scrollRef.current.scrollLeft / scrollRef.current.clientWidth)
      setActiveIndex(index)
    }, 100)
  }

  if (slides === undefined) {
    return <Skeleton className="mx-4 h-56 rounded-lg" />
  }

  if (slides.length === 0) {
    if (banners && banners.length > 0) {
      return (
        <div className="scrollbar-hide flex snap-x snap-mandatory gap-3 overflow-x-auto px-4">
          {banners.map((banner) => (
            <a
              key={banner.id}
              href={banner.link_url || undefined}
              className="aspect-[16/9] w-full flex-shrink-0 snap-center overflow-hidden rounded-lg"
            >
              <img src={banner.image_url} alt="" className="h-full w-full object-cover" />
            </a>
          ))}
        </div>
      )
    }
    // 명예의전당·추천·배너 전부 없어도 자리는 남겨둔다. 나중에 데이터가 생기면 이미지만 채워진다.
    return (
      <div className="mx-4 flex h-56 items-center justify-center rounded-lg bg-divider">
        <p className="text-sm text-ink-tertiary">{t('mainPage.hero.empty')}</p>
      </div>
    )
  }

  return (
    <div className="px-4">
      <div className="relative">
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="scrollbar-hide flex snap-x snap-mandatory overflow-x-auto rounded-lg"
        >
          {slides.map((slide, index) => (
            <Link
              key={index}
              to={`/spots/${slide.type === 'hallOfFame' ? slide.review.place : slide.spot.id}`}
              className="relative h-56 w-full flex-shrink-0 snap-center overflow-hidden"
            >
              {slide.type === 'hallOfFame' ? (
                <HallOfFameSlide slide={slide} title={t('mainPage.hero.title')} />
              ) : (
                <RecommendSlide slide={slide} title={t('mainPage.hero.recommendTitle')} />
              )}
            </Link>
          ))}
        </div>

        {slides.length > 1 && (
          <div className="absolute inset-x-4 top-3 z-10 flex gap-1">
            {slides.map((_, index) => (
              <div
                key={index}
                className={`h-[3px] flex-1 rounded-full ${index === activeIndex ? 'bg-white' : 'bg-white/30'}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function HallOfFameSlide({
  slide,
  title,
}: {
  slide: Extract<Slide, { type: 'hallOfFame' }>
  title: string
}) {
  const work = slide.place?.works?.[0]?.work
  const workPrefix = work?.category === 'MOVIE' ? '영화' : work?.category === 'DRAMA' ? '드라마' : null

  return (
    <>
      {slide.review.photos[0] && (
        <img src={slide.review.photos[0].photo_url} alt="" className="h-full w-full object-cover" />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
      <div className="absolute bottom-4 left-4 text-white">
        <p className="text-lg font-bold">{title}</p>
        {slide.place && (
          <p className="text-sm text-white/90">
            {workPrefix && work?.title ? `${workPrefix} <${work.title}> ` : ''}
            {slide.place.name}
          </p>
        )}
      </div>
    </>
  )
}

function RecommendSlide({ slide, title }: { slide: Extract<Slide, { type: 'recommend' }>; title: string }) {
  return (
    <>
      <img src={slide.spot.photo_url} alt="" className="h-full w-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
      <div className="absolute bottom-4 left-4 text-white">
        <p className="text-lg font-bold">{title}</p>
        <p className="text-sm text-white/90">{slide.spot.name}</p>
      </div>
    </>
  )
}
