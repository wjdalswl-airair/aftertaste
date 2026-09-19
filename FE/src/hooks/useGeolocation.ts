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
// 메인 화면에 돌아가면 커스텀 동의 모달이 다시 뜨게 한다. 이건 우리 앱만의 기억일 뿐이라,
// 브라우저/OS가 이미 이 사이트를 막아놨으면 이걸 지워도 소용없다 — 그건
// queryNativeGeolocationPermission()으로 미리 확인해서 별도 안내를 보여줘야 한다.
export function resetLocationConsent() {
  try {
    localStorage.removeItem(CONSENT_KEY)
    sessionStorage.removeItem(SESSION_ASKED_KEY)
  } catch {
    // 무시 — 다음 방문에서 다시 시도하면 됨
  }
}

// 마이페이지 "위치 권한 설정하기"에서 쓴다 — 브라우저가 이미 허용/거부로 확정해놨어도,
// 다음 useGeolocation 판단 시점 한 번은 무조건 커스텀 설명 모달부터 보여준다(2026-09-13,
// 사용자 결정). 이미 허용된 상태라면 모달에서 "허용"을 눌러도 브라우저 네이티브 팝업은
// 다시 안 뜨고 바로 위치를 가져오지만, 최소한 버튼을 누른 것에 대한 반응(모달)은 항상 보인다.
let forceNextPrompt = false

export function requestLocationConsentPrompt() {
  forceNextPrompt = true
}

// 우리 커스텀 동의와 별개로, 브라우저/OS가 이 사이트의 위치 권한을 이미 확정해놨는지 확인한다.
// 'granted'/'denied'면 이미 결정된 것 — 이제 와서 우리 모달에서 뭘 눌러도 브라우저 네이티브
// 팝업은 다시 안 뜬다. 'prompt'면 아직 미결정. Permissions API를 지원 안 하는 브라우저(구형
// Safari 등)에서는 null을 돌려주고, 그런 경우엔 기존처럼 일단 시도해보는 흐름으로 넘어간다.
export async function queryNativeGeolocationPermission(): Promise<PermissionState | null> {
  if (!navigator.permissions?.query) {
    return null
  }
  try {
    const result = await navigator.permissions.query({ name: 'geolocation' })
    return result.state
  } catch {
    return null
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

    let cancelled = false

    async function decide() {
      // 브라우저/OS가 이미 확정해놓은 상태가 있으면 그게 우선이다 — 우리 커스텀 동의 기록이
      // 뭐라고 돼 있든(예: localStorage를 지웠지만 브라우저 권한은 남아있는 경우) 무시한다.
      const nativeState = await queryNativeGeolocationPermission()
      if (cancelled) {
        return
      }

      if (forceNextPrompt) {
        forceNextPrompt = false
        setShowConsentModal(true)
        return
      }

      if (nativeState === 'denied') {
        // "다시 설정" 버튼을 눌러 우리 쪽 기억을 지웠어도, 브라우저 자체가 막아놨으면 모달을
        // 또 띄워봐야 소용없다 — 바로 거부 상태로 처리한다.
        saveConsent({ status: 'denied', deniedAt: Date.now() })
        setState({ status: 'denied', coords: null })
        return
      }

      if (nativeState === 'granted') {
        requestPosition()
        return
      }

      // nativeState === 'prompt' 또는 확인 불가(null) — 아직 미결정이므로 우리 앱의 동의
      // 기록을 따른다(기존 로직 그대로).
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
    }

    decide()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, member])

  function requestPosition() {
    if (!navigator.geolocation) {
      setState({ status: 'denied', coords: null })
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        // 실제로 성공했을 때만 "허용"으로 기록한다 — 클릭 시점이 아니라 결과가 나온 시점에
        // 저장해야, 브라우저가 실제로는 거부했는데 우리만 허용된 걸로 착각하는 일이 없다
        // (2026-09-13, fix/fe 논의).
        saveConsent({ status: 'granted' })
        setState({
          status: 'granted',
          coords: { lat: position.coords.latitude, lng: position.coords.longitude },
        })
      },
      (error) => {
        // code 1 = PERMISSION_DENIED. 지금 이 순간 브라우저 네이티브 팝업에서(또는 이미
        // 차단된 상태라 팝업 없이) 거부된 것 — 이것도 결과가 나온 시점에 저장한다.
        if (error.code === error.PERMISSION_DENIED) {
          saveConsent({ status: 'denied', deniedAt: Date.now() })
        }
        setState({ status: 'denied', coords: null })
      },
    )
  }

  function handleAllow() {
    setShowConsentModal(false)
    // 여기서 바로 saveConsent(granted)를 하지 않는다 — requestPosition의 콜백이 실제 결과에
    // 맞춰 저장한다.
    requestPosition()
  }

  function handleDeny() {
    saveConsent({ status: 'denied', deniedAt: Date.now() })
    setShowConsentModal(false)
    setState({ status: 'denied', coords: null })
  }

  // 지도의 "내 위치로 이동" 버튼처럼, 사용자가 명시적으로 위치를 다시 요청할 때 쓴다.
  // decide()와 달리 저장된 동의나 재요청 주기를 보지 않고, 매번 브라우저 상태를 새로 확인한다.
  async function requestLocation() {
    const nativeState = await queryNativeGeolocationPermission()
    if (nativeState === 'denied') {
      setState({ status: 'denied', coords: null })
      return
    }
    if (nativeState === 'granted') {
      requestPosition()
      return
    }
    // 'prompt' 또는 확인 불가 — 커스텀 동의 모달부터 보여준다.
    setShowConsentModal(true)
  }

  return { ...state, showConsentModal, handleAllow, handleDeny, requestLocation }
}
