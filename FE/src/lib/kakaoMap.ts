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
