import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from './components/RequireAuth'
import { useInitAuth } from './hooks/useInitAuth'
import { LoginPage } from './pages/LoginPage'
import { MainPage } from './pages/MainPage'
import { useAuthStore } from './store/useAuthStore'

// Phase 1에서 로그인 가드가 실제로 동작하는지 확인하기 위한 임시 화면.
// 진짜 마이페이지는 Phase 7에서 만든다.
function TempMyPage() {
  const member = useAuthStore((state) => state.member)
  return (
    <main className="flex min-h-dvh items-center justify-center">
      <p className="text-ink">로그인됨: {member?.nickname}</p>
    </main>
  )
}

function App() {
  useInitAuth()

  return (
    <Routes>
      <Route path="/" element={<MainPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/mypage" element={<TempMyPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
