import { ArrowLeft, CalendarDays, Clapperboard, Share2, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getWorkDetail, type WorkDetail } from '../api/works'
import { BottomNav } from '../components/BottomNav'
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
    <main className="flex min-h-dvh flex-col gap-8 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-6">
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
          <div className="px-4">
            <img
              src={work.poster_url}
              alt=""
              className="h-[230px] w-full rounded-2xl object-cover"
            />
          </div>

          <div className="flex flex-col gap-6 px-4">
            <div className="flex flex-col gap-1">
              <p className="text-sm text-primary">
                {work.category === 'DRAMA' ? t('searchPage.filters.drama') : t('searchPage.filters.movie')}
              </p>
              <p className="text-xl font-bold text-ink">{work.title}</p>
            </div>

            <div className="flex flex-col gap-4 rounded-2xl bg-accent/15 p-5">
              <InfoRow icon={<Users size={14} />} label={t('workDetail.mainCast')} value={work.main_cast} />
              <InfoRow icon={<Clapperboard size={14} />} label={t('workDetail.director')} value={work.director} />
              <InfoRow
                icon={<CalendarDays size={14} />}
                label={t('workDetail.releaseDate')}
                value={work.release_date ?? ''}
              />
            </div>
          </div>

          <section className="px-4">
            <h2 className="mb-3 text-lg font-bold text-ink">{t('workDetail.storyTitle')}</h2>
            <p className="rounded-2xl bg-accent/15 p-5 text-sm leading-[1.7] text-ink-secondary">
              {work.description}
            </p>
            <a
              href={`https://www.google.com/search?q=${encodeURIComponent(work.title)}`}
              target="_blank"
              rel="noreferrer"
              className="mt-4 block w-full rounded-full bg-primary py-3 text-center text-sm font-medium text-white"
            >
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
                    <img
                      src={place.photo_url}
                      alt=""
                      className="aspect-square w-full rounded-xl object-cover"
                    />
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
    <div className="flex flex-col gap-8 px-4">
      <Skeleton className="h-[230px] w-full rounded-2xl" />
      <div className="flex flex-col gap-2">
        <Skeleton className="h-3 w-1/4 rounded-sm" />
        <Skeleton className="h-6 w-2/3 rounded-sm" />
      </div>
      <Skeleton className="h-32 w-full rounded-2xl" />
    </div>
  )
}
