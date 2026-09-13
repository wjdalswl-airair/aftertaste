import { Plus } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { deleteAccount, getMe, logout, updateProfile, type Member } from '../api/auth'
import { getMyFavorites, type Favorite } from '../api/bookmarks'
import { getMyCourses, type Course } from '../api/courses'
import { getMyReviews, type ReviewItem } from '../api/reviews'
import { getPlaceDetail } from '../api/spots'
import spotPlaceholder from '../assets/placeholder/spot.png'
import { BottomNav } from '../components/BottomNav'
import { BottomSheet } from '../components/BottomSheet'
import { LanguageSheet } from '../components/LanguageSheet'
import { PlaceholderImage } from '../components/PlaceholderImage'
import { Skeleton } from '../components/Skeleton'
import { resetLocationConsent } from '../hooks/useGeolocation'
import { PhotoTooLargeError, UnsupportedImageError } from '../lib/compressImage'
import { deleteProfilePhoto, uploadProfilePhoto } from '../lib/profilePhotoUpload'
import { useAuthStore } from '../store/useAuthStore'

const NICKNAME_MAX_LENGTH = 20

export function MyPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  // 프로필 저장 시 이 화면의 로컬 상태(me)뿐 아니라 전역 스토어도 같이 갱신해야,
  // 메인 화면 인사말처럼 다른 화면에서 쓰는 닉네임도 새로고침 없이 바로 반영된다.
  const setMember = useAuthStore((state) => state.setMember)

  const [me, setMe] = useState<Member | undefined>(undefined)
  const [favorites, setFavorites] = useState<Favorite[] | undefined>(undefined)
  const [myReviews, setMyReviews] = useState<ReviewItem[] | undefined>(undefined)
  const [myCourses, setMyCourses] = useState<Course[] | undefined>(undefined)
  // 리뷰 API(GET /api/account/reviews/)엔 장소 이름이 없이 ID만 와서, 카드에 이름을 보여주려면
  // 리뷰에 쓰인 장소들만 따로(중복 제거) 조회해야 한다 (docs/DETAIL_SPEC.md S-10 참고).
  const [placeNames, setPlaceNames] = useState<Record<number, string>>({})

  const [editing, setEditing] = useState(false)
  const [nickname, setNickname] = useState('')
  const [photoUrl, setPhotoUrl] = useState<string | null>(null)
  const [uploadingPhoto, setUploadingPhoto] = useState(false)
  const [photoError, setPhotoError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [confirmingWithdraw, setConfirmingWithdraw] = useState(false)

  // 편집 중 새로 올린 프로필 사진 중, 저장 전에 다시 다른 사진으로 바꿔서 버려진 것만 추적한다.
  // 편집 시작 시 baseline으로 깔아둔 me.profile_image_url(기존 저장된 사진)은 여기 안 들어간다 —
  // 저장 전까지는 실제 프로필이 그 사진을 그대로 쓰고 있어서 지우면 안 된다.
  const previousDraftPhotoUrl = useRef<string | null>(null)

  // 프로필 사진을 새로 골라놓고 저장(handleSaveProfile)까진 안 한 채로 이 화면을 벗어나면,
  // 그 임시 업로드본을 정리한다. previousDraftPhotoUrl은 저장에 성공하면 null로 비워지므로
  // (handleSaveProfile 참고), 여기 남아있다는 건 저장 안 된 채로 나간다는 뜻이다.
  useEffect(() => {
    return () => {
      if (previousDraftPhotoUrl.current) {
        deleteProfilePhoto(previousDraftPhotoUrl.current)
      }
    }
  }, [])

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch(() => setMe(undefined))
    getMyFavorites()
      .then(setFavorites)
      .catch(() => setFavorites([]))
    getMyReviews()
      .then(setMyReviews)
      .catch(() => setMyReviews([]))
    getMyCourses()
      .then(setMyCourses)
      .catch(() => setMyCourses([]))
  }, [])

  useEffect(() => {
    if (!myReviews || myReviews.length === 0) {
      return
    }
    const uniquePlaceIds = [...new Set(myReviews.map((review) => review.place))]
    uniquePlaceIds.forEach((placeId) => {
      getPlaceDetail(placeId)
        .then((place) => setPlaceNames((prev) => ({ ...prev, [placeId]: place.name })))
        .catch(() => {})
    })
  }, [myReviews])

  function startEditing() {
    if (!me) {
      return
    }
    setNickname(me.nickname)
    setPhotoUrl(me.profile_image_url)
    setPhotoError(null)
    previousDraftPhotoUrl.current = null
    setEditing(true)
  }

  async function handlePhotoSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) {
      return
    }
    setUploadingPhoto(true)
    setPhotoError(null)
    try {
      const url = await uploadProfilePhoto(file)
      // 저장 전에 또 다른 사진으로 바꾸는 경우 — 직전 임시 업로드본은 이제 어디서도 안 쓰이니 지운다.
      if (previousDraftPhotoUrl.current) {
        deleteProfilePhoto(previousDraftPhotoUrl.current)
      }
      previousDraftPhotoUrl.current = url
      setPhotoUrl(url)
    } catch (error) {
      console.error('프로필 사진 업로드 실패', error)
      if (error instanceof UnsupportedImageError) {
        setPhotoError(t('reviewForm.photoUnsupportedFormat'))
      } else if (error instanceof PhotoTooLargeError) {
        setPhotoError(t('reviewForm.photoTooLarge'))
      } else {
        setPhotoError(t('reviewForm.photoUploadError'))
      }
    } finally {
      setUploadingPhoto(false)
    }
  }

  async function handleSaveProfile() {
    if (!me || saving) {
      return
    }
    const oldPhotoUrl = me.profile_image_url
    setSaving(true)
    try {
      await updateProfile({ nickname: nickname.trim(), profile_image_url: photoUrl })
      const updated = await getMe()
      setMe(updated)
      setMember(updated)
      setEditing(false)
      // 저장이 실제로 끝난 뒤에만 예전 프로필 사진을 지운다 — 저장 전에 지우면 저장이 실패했을 때
      // 프로필 사진이 사라진 채로 남는다.
      if (oldPhotoUrl && oldPhotoUrl !== photoUrl) {
        deleteProfilePhoto(oldPhotoUrl)
      }
      previousDraftPhotoUrl.current = null
    } catch (error) {
      console.error('프로필 저장 실패', error)
    } finally {
      setSaving(false)
    }
  }

  function handleResetLocationConsent() {
    resetLocationConsent()
    navigate('/')
  }

  async function handleLogout() {
    await logout().catch(() => {})
    navigate('/')
  }

  async function handleWithdraw() {
    await deleteAccount().catch(() => {})
    await logout().catch(() => {})
    navigate('/', { replace: true })
  }

  return (
    <main className="flex min-h-dvh flex-col gap-4 pb-24">
      <header className="flex items-center justify-between px-4 pt-4">
        <Link to="/" className="font-brand text-2xl font-bold text-primary">여운</Link>
        <LanguageSheet />
      </header>

      {me === undefined ? (
        <div className="mx-4 flex items-center gap-8 rounded-2xl bg-white px-6 py-4 shadow-[0_4px_12px_rgba(0,0,0,0.08)]">
          <Skeleton className="h-20 w-20 rounded-full" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-24 rounded-sm" />
            <Skeleton className="h-3 w-32 rounded-sm" />
          </div>
        </div>
      ) : (
        <section className="px-4">
          <div className="flex items-center gap-8 rounded-2xl bg-white px-6 py-4 shadow-[0_4px_12px_rgba(0,0,0,0.08)]">
            <div className="relative shrink-0">
              {(editing ? photoUrl : me.profile_image_url) ? (
                <img
                  src={(editing ? photoUrl : me.profile_image_url) ?? undefined}
                  alt=""
                  className="h-20 w-20 rounded-full object-cover"
                />
              ) : (
                <div className="h-20 w-20 rounded-full bg-accent/20" />
              )}
              {editing && (
                <label className="absolute bottom-0 right-0 flex h-6 w-6 items-center justify-center rounded-full bg-primary">
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handlePhotoSelect}
                    disabled={uploadingPhoto}
                  />
                  {uploadingPhoto ? (
                    <div className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <Plus size={14} className="text-white" />
                  )}
                </label>
              )}
            </div>

            <div className="flex-1">
              {editing ? (
                <div className="flex items-center gap-2">
                  <input
                    value={nickname}
                    onChange={(event) => setNickname(event.target.value.slice(0, NICKNAME_MAX_LENGTH))}
                    className="w-full rounded-lg border border-divider px-2 py-1 text-base font-bold text-ink outline-none"
                  />
                  <span className="shrink-0 text-xs text-ink-tertiary">
                    {nickname.length}/{NICKNAME_MAX_LENGTH}
                  </span>
                </div>
              ) : (
                <p className="text-base font-bold text-ink">{me.nickname}</p>
              )}
              <p className="mt-1 text-sm text-ink-tertiary">{me.email}</p>
              <p className="mt-2 text-xs text-ink-secondary">
                {t('myPage.reviewedPlacesLabel', { count: me.reviewed_places_count })}
              </p>
              <p className="text-xs text-ink-secondary">
                {t('myPage.createdCoursesLabel', { count: me.created_courses_count })}
              </p>

              {editing && photoError && <p className="mt-1 text-xs text-[#e0574a]">{photoError}</p>}

              <button
                type="button"
                onClick={editing ? handleSaveProfile : startEditing}
                disabled={editing && saving}
                className="mt-3 rounded-full border border-primary px-4 py-1.5 text-xs font-medium text-primary disabled:opacity-40"
              >
                {editing ? t('myPage.profileSaveButton') : t('myPage.profileEditButton')}
              </button>
            </div>
          </div>
        </section>
      )}

      <section className="px-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-bold text-ink">{t('myPage.favoritesTitle')}</h2>
          {favorites && favorites.length > 0 && (
            <Link to="/bookmarks" className="text-sm text-ink-tertiary">
              {t('myPage.favoritesMore')}
            </Link>
          )}
        </div>
        {favorites === undefined ? (
          <HorizontalCardSkeleton />
        ) : favorites.length > 0 ? (
          <div className="scrollbar-hide flex gap-3 overflow-x-auto">
            {favorites.map((favorite) =>
              favorite.type === 'PLACE' && favorite.place ? (
                <Link key={favorite.id} to={`/spots/${favorite.place.id}`} className="w-[110px] flex-shrink-0">
                  <PlaceholderImage
                    src={favorite.place.photo_url}
                    placeholder={spotPlaceholder}
                    alt=""
                    className="h-[110px] w-full rounded-xl"
                  />
                  <p className="mt-2 truncate text-xs text-ink">{favorite.place.name}</p>
                  <p className="truncate text-xs text-ink-secondary">{favorite.place.address}</p>
                </Link>
              ) : favorite.course ? (
                <Link key={favorite.id} to={`/courses/${favorite.course.id}`} className="w-[110px] flex-shrink-0">
                  <div className="h-[110px] w-full rounded-xl bg-accent/15" />
                  <p className="mt-2 truncate text-xs text-ink">{favorite.course.title}</p>
                  <p className="truncate text-xs text-ink-secondary">{favorite.course.place_name}</p>
                </Link>
              ) : null,
            )}
          </div>
        ) : (
          <p className="text-sm text-ink-tertiary">{t('myPage.favoritesEmpty')}</p>
        )}
      </section>

      <section className="px-4">
        <h2 className="mb-3 text-lg font-bold text-ink">{t('myPage.myReviewsTitle')}</h2>
        {myReviews === undefined ? (
          <HorizontalCardSkeleton />
        ) : myReviews.length > 0 ? (
          <div className="scrollbar-hide flex gap-3 overflow-x-auto">
            {myReviews.map((review) => (
              <Link
                key={review.id}
                to={`/spots/${review.place}/reviews/${review.id}`}
                className="w-[110px] flex-shrink-0"
              >
                {review.photos[0] ? (
                  <img
                    src={review.photos[0].photo_url}
                    alt=""
                    loading="lazy"
                    className="h-[110px] w-full rounded-xl object-cover"
                  />
                ) : (
                  <div className="h-[110px] w-full rounded-xl bg-divider" />
                )}
                <p className="mt-2 truncate text-xs font-medium text-ink">{placeNames[review.place] ?? ''}</p>
                <p className="line-clamp-2 text-xs text-ink-secondary">{review.content}</p>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-ink-tertiary">{t('myPage.myReviewsEmpty')}</p>
        )}
      </section>

      <section className="px-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-bold text-ink">{t('myPage.myCoursesTitle')}</h2>
          {myCourses && myCourses.length > 0 && (
            <Link to="/mycourses" className="text-sm text-ink-tertiary">
              {t('myPage.favoritesMore')}
            </Link>
          )}
        </div>
        {myCourses === undefined ? (
          <HorizontalCardSkeleton />
        ) : myCourses.length > 0 ? (
          <div className="scrollbar-hide flex gap-3 overflow-x-auto">
            {myCourses.map((course) => (
              <Link key={course.id} to={`/courses/${course.id}`} className="w-[110px] flex-shrink-0">
                <div className="h-[110px] w-full rounded-xl bg-accent/15" />
                <p className="mt-2 truncate text-xs text-ink">{course.title}</p>
                <p className="truncate text-xs text-ink-secondary">{course.place_name}</p>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-ink-tertiary">{t('myPage.myCoursesEmpty')}</p>
        )}
      </section>

      <section className="mt-auto px-4">
        <button
          type="button"
          onClick={handleLogout}
          className="w-full rounded-full border border-primary py-3 text-sm font-medium text-primary"
        >
          {t('myPage.logoutButton')}
        </button>
        <button
          type="button"
          onClick={handleResetLocationConsent}
          className="mt-3 block w-full text-center text-xs text-ink-tertiary"
        >
          {t('myPage.resetLocationLink')}
        </button>
        <button
          type="button"
          onClick={() => setConfirmingWithdraw(true)}
          className="mt-3 block w-full text-center text-xs text-ink-tertiary"
        >
          {t('myPage.withdrawLink')}
        </button>
      </section>

      {confirmingWithdraw && (
        <BottomSheet onClose={() => setConfirmingWithdraw(false)}>
          <p className="px-4 pt-4 text-center text-[15px] font-bold text-ink">
            {t('myPage.withdrawConfirmTitle')}
          </p>
          <button
            type="button"
            onClick={handleWithdraw}
            className="mt-2 block w-full py-4 text-center text-[15px] font-medium text-[#e0574a]"
          >
            {t('myPage.withdrawConfirmButton')}
          </button>
          <button
            type="button"
            onClick={() => setConfirmingWithdraw(false)}
            className="block w-full py-3 text-center text-sm text-ink-tertiary"
          >
            {t('myPage.withdrawCancelButton')}
          </button>
        </BottomSheet>
      )}

      <BottomNav />
    </main>
  )
}

function HorizontalCardSkeleton() {
  return (
    <div className="flex gap-3">
      {[0, 1, 2].map((i) => (
        <div key={i} className="w-[110px] flex-shrink-0">
          <Skeleton className="h-[110px] w-full rounded-xl" />
          <Skeleton className="mt-2 h-3 w-3/4 rounded-sm" />
        </div>
      ))}
    </div>
  )
}
