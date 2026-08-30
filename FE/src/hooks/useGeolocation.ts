import { useEffect, useState } from 'react'

type GeolocationState = {
  status: 'pending' | 'granted' | 'denied'
  coords: { lat: number; lng: number } | null
}

// 위치 권한을 한 번만 물어본다. 거부해도 다시 묻지 않는다
// ("위치 권한 거부는 정상적인 사용자 선택이다", PHASE2.md 넘어가기 전 확인).
export function useGeolocation() {
  const [state, setState] = useState<GeolocationState>({ status: 'pending', coords: null })

  useEffect(() => {
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
  }, [])

  return state
}
