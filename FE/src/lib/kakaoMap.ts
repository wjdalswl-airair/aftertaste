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
