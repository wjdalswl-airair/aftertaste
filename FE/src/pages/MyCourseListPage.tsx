import { ArrowLeft, MoreHorizontal } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { deleteCourse, getMyCourses, type Course } from '../api/courses'
import { BottomNav } from '../components/BottomNav'
import { Skeleton } from '../components/Skeleton'

function formatDate(isoString: string) {
  const date = new Date(isoString)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}.${pad(date.getMonth() + 1)}.${pad(date.getDate())}`
}

export function MyCourseListPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [courses, setCourses] = useState<Course[] | undefined>(undefined)
  const [menuTarget, setMenuTarget] = useState<Course | null>(null)

  useEffect(() => {
    getMyCourses()
      .then(setCourses)
      .catch(() => setCourses([]))
  }, [])

  async function handleDelete() {
    if (!menuTarget) {
      return
    }
    await deleteCourse(menuTarget.id).catch(() => {})
    setCourses((prev) => prev?.filter((course) => course.id !== menuTarget.id))
    setMenuTarget(null)
  }

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-6">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <p className="text-center text-lg font-bold text-ink">
          {t('myCourseList.title')}
          {courses && <span className="ml-1.5 text-xs font-normal text-ink-tertiary">{courses.length}개</span>}
        </p>
      </header>

      <section className="flex flex-col gap-5 px-4">
        {courses === undefined ? (
          <MyCourseListSkeleton />
        ) : courses.length > 0 ? (
          courses.map((course) => (
            <div key={course.id} className="flex items-start gap-3">
              <Link to={`/courses/${course.id}`} className="flex flex-1 flex-col gap-2">
                <div className="h-[140px] w-full rounded-2xl bg-accent/15" />
                <div>
                  <p className="text-sm font-bold text-ink">{course.title}</p>
                  <p className="text-xs text-ink-secondary">
                    {course.place_name} · {course.course_places.length + 1}
                    {t('myCourseList.placesCountSuffix')} · {formatDate(course.created_at)}
                  </p>
                </div>
              </Link>
              <button type="button" onClick={() => setMenuTarget(course)} aria-label="더보기" className="pt-2">
                <MoreHorizontal size={18} className="text-ink-tertiary" />
              </button>
            </div>
          ))
        ) : (
          <p className="text-sm text-ink-tertiary">{t('myCourseList.empty')}</p>
        )}
      </section>

      {menuTarget && (
        <div className="fixed inset-0 z-50 mx-auto w-full max-w-[480px]">
          <button
            type="button"
            aria-label="닫기"
            className="absolute inset-0 bg-black/40"
            onClick={() => setMenuTarget(null)}
          />
          <div className="absolute inset-x-0 bottom-0 flex flex-col">
            <div className="w-full animate-[sheet-up_0.2s_ease-out] rounded-t-2xl bg-white pb-8 pt-2">
              <div className="mx-auto mt-1.5 h-[3px] w-[46px] rounded-full bg-divider" />
              <button
                type="button"
                onClick={handleDelete}
                className="block w-full py-4 text-center text-[15px] font-medium text-[#e0574a]"
              >
                {t('myCourseList.delete')}
              </button>
              <button
                type="button"
                onClick={() => setMenuTarget(null)}
                className="mt-2 block w-full py-3 text-center text-ink-tertiary"
              >
                {t('myCourseList.cancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </main>
  )
}

function MyCourseListSkeleton() {
  return (
    <>
      {[0, 1].map((i) => (
        <div key={i} className="flex flex-col gap-2">
          <Skeleton className="h-[140px] w-full rounded-2xl" />
          <Skeleton className="h-3 w-1/2 rounded-sm" />
          <Skeleton className="h-3 w-1/3 rounded-sm" />
        </div>
      ))}
    </>
  )
}
