import { ArrowLeft, CalendarDays, Clapperboard, Clock, ExternalLink, Share2, Star, Tag, Users } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getWorkDetail, type WorkDetail } from '../api/works'
import spotPlaceholder from '../assets/placeholder/spot.png'
import workPlaceholder from '../assets/placeholder/work.png'
import { BottomNav } from '../components/BottomNav'
import { FavoriteButton } from '../components/FavoriteButton'
import { PlaceholderImage } from '../components/PlaceholderImage'
import { Skeleton } from '../components/Skeleton'

export function WorkDetailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { workId } = useParams<{ workId: string }>()

  // undefined: 로딩 중, null: 존재하지 않거나 실패
  const [work, setWork] = useState<WorkDetail | null | undefined>(undefined)

  useEffect(() => {
    setWork(undefined)
    getWorkDetail(Number(workId))
      .then(setWork)
      .catch(() => setWork(null))
  }, [workId])

  function handleShare() {
    navigator.clipboard.writeText(window.location.href).catch(() => {})
  }

  return (
    <main className="flex min-h-dvh flex-col gap-4 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-4">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <div />
        <button type="button" onClick={handleShare} aria-label="공유" className="justify-self-end">
          <Share2 size={22} className="text-ink" />
        </button>
      </header>

      {work === undefined && <WorkDetailSkeleton />}

      {work === null && (
        <p className="px-4 py-20 text-center text-ink-tertiary">{t('workDetail.notFound')}</p>
      )}

      {work && (
        <>
          <div className="flex flex-col gap-1 px-4">
            <p className="text-sm text-primary">
              {work.category === 'DRAMA' ? t('searchPage.filters.drama') : t('searchPage.filters.movie')}
            </p>
            <p className="text-xl font-bold text-ink">{work.title}</p>
          </div>

          <div className="flex items-stretch gap-3 px-4">
            <PlaceholderImage
              src={work.poster_url}
              placeholder={workPlaceholder}
              alt=""
              className="w-[42%] shrink-0 rounded-2xl"
            />
            <div className="flex flex-1 flex-col justify-center gap-3 rounded-2xl bg-accent/15 p-4">
              <InfoRow icon={<Users size={14} />} label={t('workDetail.mainCast')} value={work.main_cast} />
              <InfoRow icon={<Clapperboard size={14} />} label={t('workDetail.director')} value={work.director} />
              <InfoRow icon={<Tag size={14} />} label={t('workDetail.genre')} value={work.genre} />
              <InfoRow icon={<Star size={14} />} label={t('workDetail.rating')} value={work.rating ?? ''} />
              <InfoRow
                icon={<Clock size={14} />}
                label={t('workDetail.runtime')}
                value={work.runtime != null ? t('workDetail.runtimeValue', { minutes: work.runtime }) : ''}
              />
              <InfoRow
                icon={<CalendarDays size={14} />}
                label={t('workDetail.releaseDate')}
                value={work.release_date ?? ''}
              />
            </div>
          </div>

          <section className="px-4">
            <h2 className="mb-3 text-lg font-bold text-ink">{t('workDetail.storyTitle')}</h2>
            <WorkDescription description={work.description} />
            <a
              href={`https://www.google.com/search?q=${encodeURIComponent(work.title)}`}
              target="_blank"
              rel="noreferrer"
              className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-full bg-primary py-3 text-center text-sm font-medium text-white"
            >
              <ExternalLink size={16} />
              {t('workDetail.detailButton')}
            </a>
          </section>

          <section className="px-4">
            <h2 className="mb-3 text-lg font-bold text-ink">
              {t('workDetail.placesTitle', { title: work.title })}
            </h2>
            {work.places.length === 0 ? (
              <p className="text-sm text-ink-tertiary">{t('workDetail.placesEmpty')}</p>
            ) : (
              <div className="grid grid-cols-3 gap-x-3 gap-y-4">
                {work.places.map((place) => (
                  <Link key={place.id} to={`/spots/${place.id}`}>
                    <div className="relative">
                      <PlaceholderImage
                        src={place.photo_url}
                        placeholder={spotPlaceholder}
                        alt=""
                        className="aspect-square w-full rounded-xl"
                      />
                      <FavoriteButton placeId={place.id} />
                    </div>
                    <p className="mt-1 truncate text-xs text-ink">{place.name}</p>
                    <p className="truncate text-[11px] text-ink-secondary">{place.address}</p>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}

      <BottomNav />
    </main>
  )
}

// "이 작품의 이야기" 설명이 4줄 넘게 넘치면 더보기/접기 토글을 보여준다.
// 실제로 4줄을 넘는지는 line-clamp 적용 상태에서 scrollHeight/clientHeight를 비교해서 판단한다.
function WorkDescription({ description }: { description: string }) {
  const { t } = useTranslation()
  const textRef = useRef<HTMLParagraphElement>(null)
  const [expanded, setExpanded] = useState(false)
  const [overflowing, setOverflowing] = useState(false)

  useEffect(() => {
    if (textRef.current) {
      setOverflowing(textRef.current.scrollHeight > textRef.current.clientHeight)
    }
  }, [description])

  // 설명이 아직 안 채워진 작품은 "정보를 준비중입니다" 같은 임시 문구로 대신 보여준다
  // (2026-09-13 사용자 결정, 실제 데이터가 채워지면 자연히 안 뜬다).
  if (!description) {
    return (
      <div className="rounded-xl bg-accent/15 p-5">
        <p className="text-sm text-ink-tertiary">{t('workDetail.storyEmpty')}</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl bg-accent/15 p-5">
      <p
        ref={textRef}
        className={`text-sm leading-[1.7] text-ink-secondary ${expanded ? '' : 'line-clamp-3'}`}
      >
        {description}
      </p>
      {(overflowing || expanded) && (
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          className="mt-2 text-xs font-medium text-primary"
        >
          {expanded ? t('workDetail.storyLess') : t('workDetail.storyMore')}
        </button>
      )}
    </div>
  )
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  if (!value) {
    return null
  }
  return (
    <div className="flex gap-2.5 text-[13px]">
      <span className="mt-0.5 shrink-0 text-primary">{icon}</span>
      <span className="w-[70px] shrink-0 text-ink">{label}</span>
      <span className="flex-1 text-ink-secondary">{value}</span>
    </div>
  )
}

function WorkDetailSkeleton() {
  return (
    <div className="flex flex-col gap-4 px-4">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-3 w-1/4 rounded-sm" />
        <Skeleton className="h-6 w-2/3 rounded-sm" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-[230px] w-[42%] shrink-0 rounded-2xl" />
        <Skeleton className="h-[230px] flex-1 rounded-2xl" />
      </div>
    </div>
  )
}
