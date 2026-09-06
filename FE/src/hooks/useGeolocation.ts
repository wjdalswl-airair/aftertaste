import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/useAuthStore'

type GeolocationState = {
  status: 'pending' | 'granted' | 'denied'
  coords: { lat: number; lng: number } | null
}

type StoredConsent = { status: 'granted' } | { status: 'denied'; deniedAt: number }

// 커스텀 동의 모달에서 이미 허용/거부를 선택했는지 기기에 기억해둔다. 이게 없으면 앱을
// 다시 켤 때마다 모달이 또 뜬다 (Phase 11, 2026-09-04 — LocationPermissionModal 추가).
const CONSENT_KEY = 'location-permission-consent'
// "다음에"(거부)를 고른 로그인 사용자는 이 기간이 지나면 모달을 다시 보여준다 (2026-09-06 결정).
const RENOTIFY_INTERVAL_MS = 24 * 60 * 60 * 1000
// "다음에"를 고른 비로그인 사용자는 재요청 주기 대신, 세션(브라우저를 새로 열 때)마다 다시 물어본다.
// 같은 세션 안에서 화면을 왔다 갔다 하는 것만으로 계속 뜨지 않도록 여기에 기록해둔다.
const SESSION_ASKED_KEY = 'location-permission-asked-this-session'

function readConsent(): StoredConsent | null {
  try {
    const raw = localStorage.getItem(CONSENT_KEY)
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw)
    if (parsed?.status === 'granted') {
      return { status: 'granted' }
    }
    if (parsed?.status === 'denied' && typeof parsed.deniedAt === 'number') {
      return { status: 'denied', deniedAt: parsed.deniedAt }
    }
    return null
  } catch {
    return null
  }
}

function saveConsent(consent: StoredConsent) {
  try {
    localStorage.setItem(CONSENT_KEY, JSON.stringify(consent))
  } catch {
    // localStorage를 못 쓰는 환경(프라이빗 모드 등)이면 그냥 이번 방문에서만 다시 물어본다.
  }
}

// 마이페이지의 "위치 권한 다시 설정" 버튼에서 쓴다 — 저장된 동의를 지워서
// 메인 화면에 돌아가면 커스텀 동의 모달이 다시 뜨게 한다.
export function resetLocationConsent() {
  try {
    localStorage.removeItem(CONSENT_KEY)
    sessionStorage.removeItem(SESSION_ASKED_KEY)
  } catch {
    // 무시 — 다음 방문에서 다시 시도하면 됨
  }
}

// 위치 권한을 물어보는 주기: 허용은 영구 기억, 거부("다음에")는 로그인 여부에 따라 다르게
// 다시 물어본다 — 로그인 사용자는 1일마다, 비로그인 사용자는 세션(브라우저 재시작)마다.
// 브라우저 네이티브 권한 팝업을 바로 띄우지 않고, LocationPermissionModal로 먼저 설명하고
// "허용"을 눌러야 실제 브라우저 팝업(requestPosition)을 띄운다.
export function useGeolocation() {
  const member = useAuthStore((state) => state.member)
  const authLoading = useAuthStore((state) => state.isLoading)
  const [state, setState] = useState<GeolocationState>({ status: 'pending', coords: null })
  const [showConsentModal, setShowConsentModal] = useState(false)

  useEffect(() => {
    // 로그인 여부에 따라 재요청 주기가 달라지므로, 로그인 상태 확인이 끝날 때까지 기다린다.
    if (authLoading) {
      return
    }

    const consent = readConsent()

    if (!consent) {
      setShowConsentModal(true)
      return
    }

    if (consent.status === 'granted') {
      requestPosition()
      return
    }

    // consent.status === 'denied'
    if (member) {
      const elapsed = Date.now() - consent.deniedAt
      if (elapsed >= RENOTIFY_INTERVAL_MS) {
        setShowConsentModal(true)
      } else {
        setState({ status: 'denied', coords: null })
      }
      return
    }

    // 비로그인: 이번 세션에 이미 물어봤으면 다시 안 묻는다.
    let askedThisSession = false
    try {
      askedThisSession = sessionStorage.getItem(SESSION_ASKED_KEY) === 'true'
    } catch {
      // sessionStorage를 못 쓰면 매번 다시 물어보는 쪽으로 둔다.
    }

    if (askedThisSession) {
      setState({ status: 'denied', coords: null })
      return
    }

    try {
      sessionStorage.setItem(SESSION_ASKED_KEY, 'true')
    } catch {
      // 무시 — 이번 세션에 한 번 더 물어보게 될 수 있지만 치명적이지 않음
    }
    setShowConsentModal(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, member])

  function requestPosition() {
    if (!navigator.geolocation) {
      setState({ status: 'denied', coords: null })
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setState({
          status: 'granted',
          coords: { lat: position.coords.latitude, lng: position.coords.longitude },
        })
      },
      () => {
        setState({ status: 'denied', coords: null })
      },
    )
  }

  function handleAllow() {
    saveConsent({ status: 'granted' })
    setShowConsentModal(false)
    requestPosition()
  }

  function handleDeny() {
    saveConsent({ status: 'denied', deniedAt: Date.now() })
    setShowConsentModal(false)
    setState({ status: 'denied', coords: null })
  }

  return { ...state, showConsentModal, handleAllow, handleDeny }
}
