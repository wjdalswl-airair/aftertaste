import { Cloud, CloudDrizzle, CloudFog, CloudLightning, CloudRain, CloudSnow, Sun, type LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { SEOUL_COORDS, type WeatherCondition } from '../api/weather'
import { useWeather } from '../hooks/useWeather'
import { getCityName } from '../lib/kakaoMap'
import { Skeleton } from './Skeleton'

const CONDITION_ICONS: Record<WeatherCondition, LucideIcon> = {
  clear: Sun,
  clouds: Cloud,
  rain: CloudRain,
  drizzle: CloudDrizzle,
  snow: CloudSnow,
  thunderstorm: CloudLightning,
  fog: CloudFog,
}

// SpotDetailPage의 날씨 칩에서도 재사용한다.
export function WeatherConditionIcon({ condition, size = 16 }: { condition: WeatherCondition; size?: number }) {
  const Icon = CONDITION_ICONS[condition]
  return <Icon size={size} />
}

type Props = {
  status: 'pending' | 'granted' | 'denied'
  coords: { lat: number; lng: number } | null
}

// 메인 화면 전용 — "내 위치" 날씨. 위치를 거부했거나 아직 응답 전이면 서울 날씨로 대체해서
// 계속 보여준다(위젯을 숨기지 않기로 함, 2026-09-20 사용자 결정). 위치 권한 요청 자체는
// MainPage가 소유한 useGeolocation 하나로 처리하고(중복 프롬프트 방지), 이 컴포넌트는
// status/coords만 props로 받는다.
export function WeatherWidget({ status, coords }: Props) {
  const effectiveCoords = status === 'granted' && coords ? coords : status === 'pending' ? null : SEOUL_COORDS
  const weather = useWeather(effectiveCoords)
  // OpenWeatherMap의 지명(weather.locationName)은 lang 파라미터를 줘도 "Hanam"처럼 영문/로마자로
  // 온다 — 카카오맵으로 같은 좌표를 다시 역지오코딩해서 한글 지명("하남시")을 따로 구한다.
  // 실패하면(SDK 미로딩 등) 원래 영문 지명으로 폴백한다.
  const [cityName, setCityName] = useState<string | null>(null)

  useEffect(() => {
    if (!effectiveCoords) {
      setCityName(null)
      return
    }
    getCityName(effectiveCoords.lat, effectiveCoords.lng).then(setCityName)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveCoords?.lat, effectiveCoords?.lng])

  if (status === 'pending' || weather === undefined) {
    return <Skeleton className="h-9 w-40 shrink-0 rounded-full" />
  }

  if (!weather) {
    return null
  }

  return (
    <div className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-accent/15 px-3 py-1.5 text-sm text-ink">
      <WeatherConditionIcon condition={weather.condition} />
      <span>
        {cityName ?? weather.locationName} · {weather.description} {weather.tempC}°
      </span>
    </div>
  )
}
