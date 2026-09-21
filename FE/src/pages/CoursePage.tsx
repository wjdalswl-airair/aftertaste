import { Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getCourseFeed, type CourseSummary } from '../api/courses'
import { BottomNav } from '../components/BottomNav'
import { Skeleton } from '../components/Skeleton'

// 코스 탭 — 등록된 모든 코스를 최신순으로 보여준다 (issue #74 API 기준).
// 명소별 좌표를 지도에 찍는 건 이후에 붙이고, 지금은 세로 목록만 우선 구현한다.
export function CoursePage() {
  const { t } = useTranslation()
  // undefined: 로딩 중, []: 확인 끝났는데 코스 없음
  const [courses, setCourses] = useState<CourseSummary[] | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    getCourseFeed(1)
      .then((result) => {
        setCourses(result.courses)
        setHasMore(result.next !== null)
        setPage(1)
      })
      .catch(() => {
        setCourses([])
        setHasMore(false)
      })
  }, [])

  function handleLoadMore() {
    setLoadingMore(true)
    const nextPage = page + 1
    getCourseFeed(nextPage)
      .then((result) => {
        setCourses((prev) => [...(prev ?? []), ...result.courses])
        setHasMore(result.next !== null)
        setPage(nextPage)
      })
      .catch(() => setHasMore(false))
      .finally(() => setLoadingMore(false))
  }

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="-mb-6 grid grid-cols-[1fr_auto_1fr] items-center px-4 py-4">
        <Link to="/" className="font-brand text-2xl font-bold text-primary">여운</Link>
        <h1 className="text-lg font-bold text-ink">{t('coursePage.title')}</h1>
        <div />
      </header>

      <section className="flex flex-col gap-5 px-4">
        {courses === undefined ? (
          <CourseListSkeleton />
        ) : courses.length > 0 ? (
          <>
            {courses.map((course) => (
              <Link key={course.id} to={`/courses/${course.id}`} className="flex flex-col gap-2">
                <div className="h-[140px] w-full rounded-2xl bg-accent/15" />
                <div>
                  <p className="text-sm font-bold text-ink">{course.title}</p>
                  <div className="flex items-center gap-1 text-xs text-ink-secondary">
                    <span>{course.place_name}</span>
                    {course.favorite_count > 0 && (
                      <>
                        <span className="text-ink-tertiary">·</span>
                        <span className="flex items-center gap-0.5 text-ink-tertiary">
                          <Star size={11} className="fill-primary text-primary" />
                          {course.favorite_count}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </Link>
            ))}

            {hasMore && (
              <button
                type="button"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="mx-auto my-2 block rounded-full border border-divider px-6 py-2 text-sm text-ink-secondary disabled:opacity-50"
              >
                {loadingMore ? t('coursePage.loadingMore') : t('coursePage.loadMore')}
              </button>
            )}
          </>
        ) : (
          <p className="py-20 text-center text-sm text-ink-tertiary">{t('coursePage.empty')}</p>
        )}
      </section>

      <BottomNav />
    </main>
  )
}

function CourseListSkeleton() {
  return (
    <>
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex flex-col gap-2">
          <Skeleton className="h-[140px] w-full rounded-2xl" />
          <Skeleton className="h-3 w-1/2 rounded-sm" />
          <Skeleton className="h-3 w-1/3 rounded-sm" />
        </div>
      ))}
    </>
  )
}
