import { signInWithCustomToken, signInWithPopup } from 'firebase/auth'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { kakaoLogin } from '../api/auth'
import googleIcon from '../assets/icons/google.svg'
import kakaoIcon from '../assets/icons/kakao.svg'
import { BottomNav } from '../components/BottomNav'
import { Modal } from '../components/Modal'
import { auth, googleProvider } from '../lib/firebase'
import { loadKakaoAuth } from '../lib/kakaoAuth'
import { useAuthStore } from '../store/useAuthStore'

type LocationState = { from?: string; message?: string } | null

// 카카오는 리다이렉트 방식(Kakao.Auth.authorize())이라, 로그인 화면 자기 자신을 돌아올 주소로 쓴다.
const KAKAO_REDIRECT_URI = `${window.location.origin}/login`

export function LoginPage() {
  const member = useAuthStore((state) => state.member)
  const isLoading = useAuthStore((state) => state.isLoading)
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  const [openModal, setOpenModal] = useState<'terms' | 'privacy' | null>(null)

  const state = location.state as LocationState
  const from = state?.from ?? '/'

  // 로그인이 완료되면(useInitAuth가 member를 채우면) 원래 가려던 곳으로 이동한다.
  useEffect(() => {
    if (!isLoading && member) {
      navigate(from, { replace: true })
    }
  }, [isLoading, member, navigate, from])

  // 카카오 로그인 2단계: authorize()가 이 화면으로 ?code=...를 붙여 돌려보내면 여기서 이어받는다.
  useEffect(() => {
    const code = new URLSearchParams(location.search).get('code')
    if (!code) {
      return
    }
    // 같은 code로 다시 시도하지 않도록(새로고침 등) 주소에서 code를 바로 지운다.
    navigate('/login', { replace: true, state })

    kakaoLogin(code, KAKAO_REDIRECT_URI)
      .then(({ firebase_custom_token }) => signInWithCustomToken(auth, firebase_custom_token))
      // 로그인 성공 후 회원 조회/가입 처리는 useInitAuth의 onAuthStateChanged가 담당한다.
      .catch(() => setError('로그인에 실패했어요. 다시 시도해주세요.'))
    // 페이지 진입 시(주소에 code가 있을 때) 딱 한 번만 처리한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleGoogleLogin() {
    setError(null)
    try {
      await signInWithPopup(auth, googleProvider)
      // 로그인 성공 후 회원 조회/가입 처리는 useInitAuth의 onAuthStateChanged가 담당한다.
    } catch {
      setError('로그인에 실패했어요. 다시 시도해주세요.')
    }
  }

  async function handleKakaoLogin() {
    setError(null)
    const kakao = await loadKakaoAuth()
    if (!kakao) {
      setError('로그인에 실패했어요. 다시 시도해주세요.')
      return
    }
    kakao.Auth.authorize({ redirectUri: KAKAO_REDIRECT_URI })
  }

  return (
    <main className="flex min-h-dvh flex-col pb-24">
      <header className="flex items-center px-4 pt-6">
        <p className="font-brand text-2xl font-bold text-primary">여운</p>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center gap-12 px-6 text-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-20 w-20 rounded-full bg-ink-tertiary" />
          <p className='text-ink'>당신의 여운을 위해 <br /> 지금 바로 로그인 해보세요!</p>
        </div>
        {/* {state?.message && <p className="text-sm text-primary">{state.message}</p>} */}

        <div className="flex w-full max-w-xs flex-col gap-4">
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="flex h-14 items-center justify-center gap-2 rounded-lg bg-[#F2F2F2] px-4 font-medium text-ink"
          >
            <span className="flex w-10 items-center justify-center">
              <img src={googleIcon} alt="" className="h-10 w-10" />
            </span>
            Google로 시작하기
          </button>
          <button
            type="button"
            onClick={handleKakaoLogin}
            className="flex h-14 items-center justify-center gap-2 rounded-lg bg-[#ffe812] px-4  font-medium text-ink"
          >
            <span className="flex w-10 items-center justify-center">
              <img src={kakaoIcon} alt="" className="h-8 w-8" />
            </span>
            카카오로 시작하기
          </button>
        </div>

        {error && <p className="text-sm text-primary">{error}</p>}

        <p className="text-sm text-ink-tertiary">
          로그인 시
          <br />
          <button type="button" onClick={() => setOpenModal('terms')} className="underline">
            이용약관
          </button>{' '}
          및{' '}
          <button type="button" onClick={() => setOpenModal('privacy')} className="underline">
            개인정보처리방침
          </button>
          에 동의합니다.
        </p>
      </div>

      {openModal === 'terms' && (
        <Modal title="이용약관" onClose={() => setOpenModal(null)}>
          이용약관 내용은 추후 확정 예정입니다.
        </Modal>
      )}
      {openModal === 'privacy' && (
        <Modal title="개인정보처리방침" onClose={() => setOpenModal(null)}>
          개인정보처리방침 내용은 추후 확정 예정입니다.
        </Modal>
      )}

      <BottomNav />
    </main>
  )
}
