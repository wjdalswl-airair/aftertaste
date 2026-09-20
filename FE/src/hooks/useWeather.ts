import { useEffect, useState } from 'react'
import { getWeather, type WeatherInfo } from '../api/weather'

// undefined: 로딩 중, null: 실패했거나 좌표가 없음(위젯을 그냥 숨기면 됨).
export function useWeather(coords: { lat: number; lng: number } | null) {
  const [weather, setWeather] = useState<WeatherInfo | null | undefined>(undefined)

  useEffect(() => {
    if (!coords) {
      setWeather(null)
      return
    }
    setWeather(undefined)
    getWeather(coords.lat, coords.lng)
      .then(setWeather)
      .catch(() => setWeather(null))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coords?.lat, coords?.lng])

  return weather
}
