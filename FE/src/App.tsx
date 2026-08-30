import { Navigate, Route, Routes } from 'react-router-dom'
import { BottomNav } from './components/BottomNav'
import { LanguageSheet } from './components/LanguageSheet'
import { RequireAuth } from './components/RequireAuth'
import { useInitAuth } from './hooks/useInitAuth'
import { BookmarksPage } from './pages/BookmarksPage'
import { LoginPage } from './pages/LoginPage'
import { MainPage } from './pages/MainPage'
import { ReviewDetailPage } from './pages/ReviewDetailPage'
import { ReviewFormPage } from './pages/ReviewFormPage'
import { ReviewListPage } from './pages/ReviewListPage'
import { SearchPage } from './pages/SearchPage'
import { SpotDetailPage } from './pages/SpotDetailPage'
import { WorkDetailPage } from './pages/WorkDetailPage'
import { useAuthStore } from './store/useAuthStore'

// Phase 1에서 로그인 가드가 실제로 동작하는지 확인하기 위한 임시 화면.
// 진짜 마이페이지는 Phase 7에서 만든다.
function TempMyPage() {
  const member = useAuthStore((state) => state.member)
  return (
    <main className="flex min-h-dvh flex-col pb-24">
      <header className="flex items-center justify-end px-4 pt-6">
        <LanguageSheet />
      </header>
      <div className="flex flex-1 items-center justify-center">
        <p className="text-ink">로그인됨: {member?.nickname}</p>
      </div>
      <BottomNav />
    </main>
  )
}

function App() {
  useInitAuth()

  return (
    <Routes>
      <Route path="/" element={<MainPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/spots/:placeId" element={<SpotDetailPage />} />
      <Route path="/spots/:placeId/reviews" element={<ReviewListPage />} />
      <Route path="/spots/:placeId/reviews/:reviewId" element={<ReviewDetailPage />} />
      <Route path="/works/:workId" element={<WorkDetailPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/mypage" element={<TempMyPage />} />
        <Route path="/bookmarks" element={<BookmarksPage />} />
        <Route path="/spots/:placeId/reviews/new" element={<ReviewFormPage />} />
        <Route path="/spots/:placeId/reviews/:reviewId/edit" element={<ReviewFormPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
