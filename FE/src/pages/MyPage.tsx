import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { deleteAccount, getMe, logout, updateProfile, type Member } from '../api/auth'
import { getMyFavorites, type Favorite } from '../api/bookmarks'
import { getMyReviews, type ReviewItem } from '../api/reviews'
import { getPlaceDetail } from '../api/spots'
import { BottomNav } from '../components/BottomNav'
import { LanguageSheet } from '../components/LanguageSheet'
import { Skeleton } from '../components/Skeleton'
import { uploadProfilePhoto } from '../lib/profilePhotoUpload'

const NICKNAME_MAX_LENGTH = 20

export function MyPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [me, setMe] = useState<Member | undefined>(undefined)
  const [favorites, setFavorites] = useState<Favorite[] | undefined>(undefined)
  const [myReviews, setMyReviews] = useState<ReviewItem[] | undefined>(undefined)
  // 리뷰 API(GET /api/account/reviews/)엔 장소 이름이 없이 ID만 와서, 카드에 이름을 보여주려면
  // 리뷰에 쓰인 장소들만 따로(중복 제거) 조회해야 한다 (docs/DETAIL_SPEC.md S-10 참고).
  const [placeNames, setPlaceNames] = useState<Record<number, string>>({})

  const [editing, setEditing] = useState(false)
  const [nickname, setNickname] = useState('')
  const [photoUrl, setPhotoUrl] = useState<string | null>(null)
  const [uploadingPhoto, setUploadingPhoto] = useState(false)
  const [photoError, setPhotoError] = useState(false)
  const [saving, setSaving] = useState(false)

  const [confirmingWithdraw, setConfirmingWithdraw] = useState(false)

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

  const places = favorites?.filter(
    (favorite): favorite is Favorite & { place: NonNullable<Favorite['place']> } =>
      favorite.type === 'PLACE' && favorite.place !== null,
  )

  function startEditing() {
    if (!me) {
      return
    }
    setNickname(me.nickname)
    setPhotoUrl(me.profile_image_url)
    setPhotoError(false)
    setEditing(true)
  }

  async function handlePhotoSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) {
      return
    }
    setUploadingPhoto(true)
    setPhotoError(false)
    try {
      const url = await uploadProfilePhoto(file)
      setPhotoUrl(url)
    } catch (error) {
      console.error('프로필 사진 업로드 실패', error)
      setPhotoError(true)
    } finally {
      setUploadingPhoto(false)
    }
  }

  async function handleSaveProfile() {
    if (!me || saving) {
      return
    }
    setSaving(true)
    try {
      await updateProfile({ nickname: nickname.trim(), profile_image_url: photoUrl })
      const updated = await getMe()
      setMe(updated)
      setEditing(false)
    } catch (error) {
      console.error('프로필 저장 실패', error)
    } finally {
      setSaving(false)
    }
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
    <main className="flex min-h-dvh flex-col gap-8 pb-24">
      <header className="flex items-center justify-between px-4 pt-6">
        <p className="font-brand text-2xl font-bold text-primary">여운</p>
        <LanguageSheet />
      </header>

      {me === undefined ? (
        <div className="flex items-center gap-4 px-4">
          <Skeleton className="h-20 w-20 rounded-full" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-24 rounded-sm" />
            <Skeleton className="h-3 w-32 rounded-sm" />
          </div>
        </div>
      ) : (
        <section className="px-4">
          <div className="flex items-start gap-4">
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

              {editing && photoError && (
                <p className="mt-1 text-xs text-[#e0574a]">{t('reviewForm.photoUploadError')}</p>
              )}

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
          {places && places.length > 0 && (
            <Link to="/bookmarks" className="text-sm text-ink-tertiary">
              {t('myPage.favoritesMore')}
            </Link>
          )}
        </div>
        {places === undefined ? (
          <HorizontalCardSkeleton />
        ) : places.length > 0 ? (
          <div className="scrollbar-hide flex gap-3 overflow-x-auto">
            {places.map((favorite) => (
              <Link key={favorite.id} to={`/spots/${favorite.place.id}`} className="w-[110px] flex-shrink-0">
                <img
                  src={favorite.place.photo_url}
                  alt=""
                  className="h-[110px] w-full rounded-xl object-cover"
                />
                <p className="mt-2 truncate text-xs text-ink">{favorite.place.name}</p>
                <p className="truncate text-xs text-ink-secondary">{favorite.place.address}</p>
              </Link>
            ))}
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
        <h2 className="mb-3 text-lg font-bold text-ink">{t('myPage.myCoursesTitle')}</h2>
        <p className="text-sm text-ink-tertiary">{t('myPage.myCoursesEmpty')}</p>
      </section>

      <section className="px-4">
        <button
          type="button"
          onClick={handleLogout}
          className="w-full rounded-full border border-primary py-3 text-sm font-medium text-primary"
        >
          {t('myPage.logoutButton')}
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
        <div className="fixed inset-0 z-50 mx-auto w-full max-w-[480px]">
          <button
            type="button"
            aria-label="닫기"
            className="absolute inset-0 bg-black/40"
            onClick={() => setConfirmingWithdraw(false)}
          />
          <div className="absolute inset-x-0 bottom-0 flex flex-col">
            <div className="w-full animate-[sheet-up_0.2s_ease-out] rounded-t-2xl bg-white pb-8 pt-2">
              <div className="mx-auto mt-1.5 h-[3px] w-[46px] rounded-full bg-divider" />
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
                className="block w-full py-3 text-center text-ink-tertiary"
              >
                {t('myPage.withdrawCancelButton')}
              </button>
            </div>
          </div>
        </div>
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
