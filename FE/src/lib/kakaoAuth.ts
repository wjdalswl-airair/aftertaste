// 카카오 로그인 JS SDK 로더. index.html의 <script>가 SDK 자체는 받아오지만 defer라서,
// window.Kakao가 실제로 준비됐는지 기다렸다가 Kakao.init()까지 해줘야 한다.
// kakaoMap.ts의 loadKakaoMaps()와 같은 패턴 — 여러 곳에서 불러도 한 번만 초기화되도록 캐싱한다.
let initPromise: Promise<NonNullable<Window['Kakao']>> | null = null

// .env에 VITE_KAKAO_JS_KEY가 없으면 로그인 버튼을 눌러도 동작하지 않게 null을 돌려준다.
export function loadKakaoAuth(): Promise<NonNullable<Window['Kakao']>> | null {
  const jsKey = import.meta.env.VITE_KAKAO_JS_KEY
  if (!jsKey) {
    return null
  }

  if (!initPromise) {
    initPromise = new Promise((resolve, reject) => {
      const start = Date.now()
      const waitForScript = () => {
        if (window.Kakao) {
          if (!window.Kakao.isInitialized()) {
            window.Kakao.init(jsKey)
          }
          resolve(window.Kakao)
          return
        }
        if (Date.now() - start > 10000) {
          reject(new Error('카카오 로그인 SDK 로딩 시간이 초과됐어요'))
          return
        }
        setTimeout(waitForScript, 100)
      }
      waitForScript()
    })
  }

  return initPromise
}
