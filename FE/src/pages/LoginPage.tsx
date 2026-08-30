import { signInWithPopup } from 'firebase/auth'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { appleProvider, auth, googleProvider } from '../lib/firebase'
import { useAuthStore } from '../store/useAuthStore'

type LocationState = { from?: string; message?: string } | null

export function LoginPage() {
  const member = useAuthStore((state) => state.member)
  const isLoading = useAuthStore((state) => state.isLoading)
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)

  const state = location.state as LocationState
  const from = state?.from ?? '/'

  // 로그인이 완료되면(useInitAuth가 member를 채우면) 원래 가려던 곳으로 이동한다.
  useEffect(() => {
    if (!isLoading && member) {
      navigate(from, { replace: true })
    }
  }, [isLoading, member, navigate, from])

  async function handleLogin(provider: typeof googleProvider | typeof appleProvider) {
    setError(null)
    try {
      await signInWithPopup(auth, provider)
      // 로그인 성공 후 회원 조회/가입 처리는 useInitAuth의 onAuthStateChanged가 담당한다.
    } catch {
      setError('로그인에 실패했어요. 다시 시도해주세요.')
    }
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="font-brand text-3xl font-bold text-primary">여운</h1>
      <p className="text-ink-secondary">당신의 여운을 위해 지금 바로 로그인 해보세요!</p>

      {state?.message && <p className="text-sm text-primary">{state.message}</p>}

      <div className="flex w-full max-w-xs flex-col gap-3">
        <button
          type="button"
          onClick={() => handleLogin(googleProvider)}
          className="rounded-lg border border-divider bg-white px-4 py-3 text-ink"
        >
          Google 계정으로 로그인
        </button>
        <button
          type="button"
          onClick={() => handleLogin(appleProvider)}
          className="rounded-lg border border-divider bg-white px-4 py-3 text-ink"
        >
          Apple 계정으로 로그인
        </button>
      </div>

      {error && <p className="text-sm text-primary">{error}</p>}

      <p className="text-xs text-ink-tertiary">
        로그인 시
        <br />
        이용약관 및 개인정보처리방침에 동의합니다.
      </p>
    </main>
  )
}
