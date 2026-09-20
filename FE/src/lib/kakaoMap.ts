// 카카오맵 JS SDK 로더. index.html의 <script>가 SDK 자체는 이미 받아오지만,
// autoload=false라서 kakao.maps.load()로 지도 리소스 로딩 완료를 직접 기다려야 한다.
// 여러 컴포넌트가 동시에 불러도 한 번만 로드되도록 Promise를 모듈 스코프에 캐싱한다.
let loadPromise: Promise<typeof window.kakao> | null = null

// .env에 VITE_KAKAO_JS_KEY가 없으면 index.html의 appkey가 빈 값이 되어 SDK 스크립트가
// 정상 동작하지 않는다. 이 경우 지도를 그리려 하지 않고 null을 돌려줘서 호출부가 폴백을 보여주게 한다.
export function loadKakaoMaps(): Promise<typeof window.kakao> | null {
  if (!import.meta.env.VITE_KAKAO_JS_KEY) {
    return null
  }

  if (!loadPromise) {
    loadPromise = new Promise((resolve, reject) => {
      const start = Date.now()
      const waitForScript = () => {
        if (window.kakao?.maps) {
          window.kakao.maps.load(() => resolve(window.kakao))
          return
        }
        if (Date.now() - start > 10000) {
          reject(new Error('카카오맵 SDK 로딩 시간이 초과됐어요'))
          return
        }
        setTimeout(waitForScript, 100)
      }
      waitForScript()
    })
  }

  return loadPromise
}

// 위도/경도를 "역삼동" 같은 행정동 이름으로 바꾼다. SDK가 없거나(키 미설정) 변환에
// 실패하면 null을 돌려줘서, 호출부가 "내 주변 명소" 같은 기존 문구로 대체할 수 있게 한다.
export async function getDongName(lat: number, lng: number): Promise<string | null> {
  const loadResult = loadKakaoMaps()
  if (!loadResult) {
    return null
  }

  const kakao = await loadResult
  return new Promise((resolve) => {
    const geocoder = new kakao.maps.services.Geocoder()
    // coord2RegionCode는 (경도, 위도) 순서로 받는다.
    geocoder.coord2RegionCode(lng, lat, (result, status) => {
      if (status !== kakao.maps.services.Status.OK || result.length === 0) {
        resolve(null)
        return
      }
      const dong = result.find((r) => r.region_type === 'H') ?? result[0]
      resolve(dong.region_3depth_name || null)
    })
  })
}

// 위도/경도를 "하남시" 같은 시/군/구 이름으로 바꾼다. 날씨 위젯에서 쓴다 — OpenWeatherMap의
// 지명(`name`)은 lang 파라미터를 줘도 한글로 안 오고 "Hanam"처럼 영문/로마자로만 내려주기 때문에,
// 위경도를 카카오맵으로 다시 역지오코딩해서 한글 지명을 얻는다 (2026-09-20).
export async function getCityName(lat: number, lng: number): Promise<string | null> {
  const loadResult = loadKakaoMaps()
  if (!loadResult) {
    return null
  }

  const kakao = await loadResult
  return new Promise((resolve) => {
    const geocoder = new kakao.maps.services.Geocoder()
    geocoder.coord2RegionCode(lng, lat, (result, status) => {
      if (status !== kakao.maps.services.Status.OK || result.length === 0) {
        resolve(null)
        return
      }
      const region = result.find((r) => r.region_type === 'H') ?? result[0]
      // 세종처럼 시/군/구가 없는 지역은 region_2depth_name이 빈 문자열로 온다 — 그때는 시/도로 대체한다.
      resolve(region.region_2depth_name || region.region_1depth_name || null)
    })
  })
}

// 카카오맵 기본 마커(빨간 핀)를 index.css --color-primary 색으로 바꾼 SVG 데이터 URL을 만든다.
// kakao.maps.MarkerImage에 이 값을 넘기면 원하는 색의 핀 마커를 그릴 수 있다.
// label을 주면 가운데 흰 원 안에 그 숫자를 넣는다 (코스 상세의 방문 순서 표시용).
export function pinIconDataUrl(color: string, label?: string | number): string {
  // label이 있을 땐 숫자가 잘 보이게 흰 원을 조금 더 키운다 (label 없는 기존 핀들은 그대로 r=5).
  const circleRadius = label === undefined ? 5 : 6.5
  const labelMarkup =
    label === undefined
      ? ''
      : `<text x="14" y="14.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-weight="700" font-family="sans-serif" fill="${color}">${label}</text>`
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36"><path d="M14 0C6.3 0 0 6.3 0 14c0 10.5 14 22 14 22s14-11.5 14-22C28 6.3 21.7 0 14 0z" fill="${color}"/><circle cx="14" cy="14" r="${circleRadius}" fill="white"/>${labelMarkup}</svg>`
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}

// "내 위치"를 나타내는 파란 점 마커용 SVG 데이터 URL. 명소 핀(pinIconDataUrl, 물방울 모양)과
// 모양을 다르게 해서 지도에서 한눈에 구분되게 한다(흐린 파란 원 + 흰 테두리의 진한 파란 점).
export function myLocationDotDataUrl(): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="15" fill="#4285F4" fill-opacity="0.25"/><circle cx="16" cy="16" r="9" fill="#4285F4" stroke="white" stroke-width="3"/></svg>`
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}
