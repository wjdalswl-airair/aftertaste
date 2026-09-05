import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { getMyFavorites, type Favorite } from '../api/bookmarks'
import { BottomNav } from '../components/BottomNav'
import { FavoriteButton } from '../components/FavoriteButton'
import { Skeleton } from '../components/Skeleton'

export function BookmarksPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  // undefined: 로딩 중, []: 확인 끝났는데 즐겨찾기 없음
  const [favorites, setFavorites] = useState<Favorite[] | undefined>(undefined)

  useEffect(() => {
    getMyFavorites()
      .then(setFavorites)
      .catch(() => setFavorites([]))
  }, [])

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-6">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <p className="text-center text-lg font-bold text-ink">{t('bookmarksPage.title')}</p>
      </header>

      <section className="px-4">
        {favorites === undefined ? (
          <BookmarksSkeleton />
        ) : favorites.length > 0 ? (
          <div className="flex flex-col gap-4">
            {favorites.map((favorite) =>
              favorite.type === 'PLACE' && favorite.place ? (
                <Link key={favorite.id} to={`/spots/${favorite.place.id}`} className="flex items-center gap-3">
                  <img
                    src={favorite.place.photo_url}
                    alt=""
                    className="h-[74px] w-[75px] rounded-2xl object-cover"
                  />
                  <div className="flex-1">
                    <p className="text-sm text-ink">{favorite.place.name}</p>
                    <p className="text-[11px] text-ink-secondary">{favorite.place.address}</p>
                  </div>
                  <FavoriteButton
                    placeId={favorite.place.id}
                    initialFavorited
                    size={20}
                    className="rounded-full p-1"
                  />
                </Link>
              ) : favorite.course ? (
                <Link key={favorite.id} to={`/courses/${favorite.course.id}`} className="flex items-center gap-3">
                  <div className="h-[74px] w-[75px] shrink-0 rounded-2xl bg-accent/15" />
                  <div className="flex-1">
                    <p className="text-sm text-ink">{favorite.course.title}</p>
                    <p className="text-[11px] text-ink-secondary">{favorite.course.place_name}</p>
                  </div>
                  <FavoriteButton
                    placeId={favorite.course.id}
                    type="course"
                    initialFavorited
                    size={20}
                    className="rounded-full p-1"
                  />
                </Link>
              ) : null,
            )}
          </div>
        ) : (
          <p className="text-sm text-ink-tertiary">{t('bookmarksPage.empty')}</p>
        )}
      </section>

      <BottomNav />
    </main>
  )
}

function BookmarksSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-[74px] w-[75px] rounded-2xl" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-3 w-1/2 rounded-sm" />
            <Skeleton className="h-3 w-1/3 rounded-sm" />
          </div>
        </div>
      ))}
    </div>
  )
}
