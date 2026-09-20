import { type Language, useLocaleStore } from '../store/useLocaleStore'

export type WeatherCondition = 'clear' | 'clouds' | 'rain' | 'snow' | 'thunderstorm' | 'drizzle' | 'fog'

export type WeatherInfo = {
  // OpenWeatherMap 응답의 지명 (예: "Seoul"). 위/경도만으로 역지오코딩 없이 지명을 같이 보여줄 수 있다.
  locationName: string
  tempC: number
  condition: WeatherCondition
  // lang 파라미터에 맞춘 현지어 날씨 설명 (예: "흐림").
  description: string
}

// 위치 권한을 거부했을 때 메인 화면 날씨 위젯이 대신 보여줄 기본 좌표.
export const SEOUL_COORDS = { lat: 37.5665, lng: 126.978 }

const OWM_LANG: Record<Language, string> = {
  ko: 'kr',
  en: 'en',
  ja: 'ja',
  'zh-CN': 'zh_cn',
  'zh-TW': 'zh_tw',
}

// OpenWeatherMap의 condition code(https://openweathermap.org/weather-conditions)를
// 아이콘 매핑용 그룹 6개로 축약한다.
function mapConditionCode(code: number): WeatherCondition {
  if (code >= 200 && code < 300) return 'thunderstorm'
  if (code >= 300 && code < 400) return 'drizzle'
  if (code >= 500 && code < 600) return 'rain'
  if (code >= 600 && code < 700) return 'snow'
  if (code >= 700 && code < 800) return 'fog'
  if (code === 800) return 'clear'
  return 'clouds'
}

type OwmResponse = {
  weather: { id: number; description: string }[]
  main: { temp: number }
  name: string
}

// 백엔드를 거치지 않고 FE가 OpenWeatherMap을 직접 호출한다 (../BE/docs/DETAIL_SPEC.md #24,
// 2026-08-28 결정 — 키 보안·캐싱이 문제되면 그때 백엔드 프록시로 바꾸기로 함).
// publicFetch(client.ts)는 우리 BE 전용(VITE_API_BASE_URL)이라 여긴 재사용하지 않는다.
export async function getWeather(lat: number, lng: number): Promise<WeatherInfo> {
  const apiKey = import.meta.env.VITE_OPENWEATHER_API_KEY
  if (!apiKey) {
    throw new Error('날씨 API 키가 설정되지 않았어요')
  }

  const language = useLocaleStore.getState().language
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lng),
    appid: apiKey,
    units: 'metric',
    lang: OWM_LANG[language],
  })

  const response = await fetch(`https://api.openweathermap.org/data/2.5/weather?${params}`)
  if (!response.ok) {
    throw new Error('날씨 정보를 가져오지 못했어요')
  }

  const body: OwmResponse = await response.json()
  return {
    locationName: body.name,
    tempC: Math.round(body.main.temp),
    condition: mapConditionCode(body.weather[0].id),
    description: body.weather[0].description,
  }
}
