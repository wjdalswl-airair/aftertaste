import { useEffect, useState } from 'react'

type GeolocationState = {
  status: 'pending' | 'granted' | 'denied'
  coords: { lat: number; lng: number } | null
}

// 커스텀 동의 모달에서 이미 허용/거부를 선택했는지 기기에 기억해둔다. 이게 없으면 앱을
// 다시 켤 때마다 모달이 또 뜬다 (Phase 11, 2026-09-04 — LocationPermissionModal 추가).
const CONSENT_KEY = 'location-permission-consent'

function readConsent(): 'granted' | 'denied' | null {
  try {
    const value = localStorage.getItem(CONSENT_KEY)
    return value === 'granted' || value === 'denied' ? value : null
  } catch {
    return null
  }
}

function saveConsent(value: 'granted' | 'denied') {
  try {
    localStorage.setItem(CONSENT_KEY, value)
  } catch {
    // localStorage를 못 쓰는 환경(프라이빗 모드 등)이면 그냥 이번 방문에서만 다시 물어본다.
  }
}

// 위치 권한을 한 번만 물어본다. 거부해도 다시 묻지 않는다
// ("위치 권한 거부는 정상적인 사용자 선택이다", PHASE2.md 넘어가기 전 확인).
// 브라우저 네이티브 권한 팝업을 바로 띄우지 않고, LocationPermissionModal로 먼저 설명하고
// "허용"을 눌러야 실제 브라우저 팝업(requestPosition)을 띄운다.
export function useGeolocation() {
  const [state, setState] = useState<GeolocationState>({ status: 'pending', coords: null })
  // 이미 답한 적 있으면 모달을 다시 안 보여준다.
  const [showConsentModal, setShowConsentModal] = useState(() => readConsent() === null)

  useEffect(() => {
    const consent = readConsent()
    if (consent === 'denied') {
      setState({ status: 'denied', coords: null })
    } else if (consent === 'granted') {
      requestPosition()
    }
    // consent가 null이면 모달 응답(handleAllow/handleDeny)이 올 때까지 기다린다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
    saveConsent('granted')
    setShowConsentModal(false)
    requestPosition()
  }

  function handleDeny() {
    saveConsent('denied')
    setShowConsentModal(false)
    setState({ status: 'denied', coords: null })
  }

  return { ...state, showConsentModal, handleAllow, handleDeny }
}
