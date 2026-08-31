import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from './components/RequireAuth'
import { useInitAuth } from './hooks/useInitAuth'
import { BookmarksPage } from './pages/BookmarksPage'
import { LoginPage } from './pages/LoginPage'
import { MainPage } from './pages/MainPage'
import { MyPage } from './pages/MyPage'
import { ReviewDetailPage } from './pages/ReviewDetailPage'
import { ReviewFormPage } from './pages/ReviewFormPage'
import { ReviewListPage } from './pages/ReviewListPage'
import { SearchPage } from './pages/SearchPage'
import { SpotDetailPage } from './pages/SpotDetailPage'
import { WorkDetailPage } from './pages/WorkDetailPage'

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
        <Route path="/mypage" element={<MyPage />} />
        <Route path="/bookmarks" element={<BookmarksPage />} />
        <Route path="/spots/:placeId/reviews/new" element={<ReviewFormPage />} />
        <Route path="/spots/:placeId/reviews/:reviewId/edit" element={<ReviewFormPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
