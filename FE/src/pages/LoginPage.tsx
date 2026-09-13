import { signInWithCustomToken, signInWithPopup } from 'firebase/auth'
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { kakaoLogin } from '../api/auth'
import googleIcon from '../assets/icons/google.svg'
import kakaoIcon from '../assets/icons/kakao.svg'
import yeounCharacter from '../assets/characters/yeoun.png'
import { BottomNav } from '../components/BottomNav'
import { auth, googleProvider } from '../lib/firebase'
import { loadKakaoAuth } from '../lib/kakaoAuth'
import { getLastLoginProvider, saveLastLoginProvider } from '../lib/lastLoginProvider'
import { useAuthStore } from '../store/useAuthStore'

type LocationState = { message?: string } | null

// 카카오는 리다이렉트 방식(Kakao.Auth.authorize())이라, 로그인 화면 자기 자신을 돌아올 주소로 쓴다.
const KAKAO_REDIRECT_URI = `${window.location.origin}/login`

export function LoginPage() {
  const member = useAuthStore((state) => state.member)
  const isLoading = useAuthStore((state) => state.isLoading)
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  // 한 번만 읽으면 되는 값이라(로그인 성공하면 바로 화면을 떠남) state로 관리 안 하고 그냥 상수로 둔다.
  const lastProvider = getLastLoginProvider()

  const state = location.state as LocationState

  // 로그인이 완료되면(useInitAuth가 member를 채우면) 원래 가려던 곳이 아니라 메인으로 이동한다.
  useEffect(() => {
    if (!isLoading && member) {
      navigate('/', { replace: true })
    }
  }, [isLoading, member, navigate])

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
      .then(() => saveLastLoginProvider('kakao'))
      // 로그인 성공 후 회원 조회/가입 처리는 useInitAuth의 onAuthStateChanged가 담당한다.
      .catch(() => setError('로그인에 실패했어요. 다시 시도해주세요.'))
    // 페이지 진입 시(주소에 code가 있을 때) 딱 한 번만 처리한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleGoogleLogin() {
    setError(null)
    try {
      await signInWithPopup(auth, googleProvider)
      saveLastLoginProvider('google')
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
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="flex items-center px-4 pt-4">
        <Link to="/" className="font-brand text-2xl font-bold text-primary">여운</Link>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center gap-12 px-6 text-center">
        <div className="flex flex-col items-center gap-3">
          <img src={yeounCharacter} alt="" className="h-34 w-34 object-contain" />
          <p className='text-ink'>당신의 여운을 위해 <br /> 지금 바로 로그인 해보세요!</p>
        </div>
        {/* {state?.message && <p className="text-sm text-primary">{state.message}</p>} */}

        <div className="flex w-full max-w-xs flex-col gap-4">
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="relative flex h-14 items-center justify-center gap-2 rounded-lg bg-[#F2F2F2] px-4 font-medium text-ink"
          >
            {lastProvider === 'google' && <LastLoginBadge />}
            <span className="flex w-10 items-center justify-center">
              <img src={googleIcon} alt="" className="h-10 w-10" />
            </span>
            Google로 시작하기
          </button>
          <button
            type="button"
            onClick={handleKakaoLogin}
            className="relative flex h-14 items-center justify-center gap-2 rounded-lg bg-[#ffe812] px-4  font-medium text-ink"
          >
            {lastProvider === 'kakao' && <LastLoginBadge />}
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
          <Link to="/terms/service" className="underline">
            이용약관
          </Link>{' '}
          및{' '}
          <Link to="/terms/privacy" className="underline">
            개인정보처리방침
          </Link>
          에 동의합니다.
        </p>
      </div>

      <BottomNav />
    </main>
  )
}

// 지난번에 로그인했던 방법 버튼 위에 붙는 말풍선 뱃지 — 버튼을 가리키는 작은 꼬리(45도 회전한
// 정사각형)를 말풍선 아래에 겹쳐서 붙인다. 이 화면은 다국어 처리가 안 돼 있어서(다른 텍스트도
// 전부 한국어 그대로) 이 뱃지만 따로 i18n을 넣지 않는다.
function LastLoginBadge() {
  return (
    <span className="absolute -top-3 right-3 flex flex-col items-center">
      <span className="whitespace-nowrap rounded-lg bg-primary px-2 py-1 text-[10px] font-medium text-white">
        최근 로그인
      </span>
      <span className="-mt-1 h-2 w-2 rotate-45 bg-primary" />
    </span>
  )
}
