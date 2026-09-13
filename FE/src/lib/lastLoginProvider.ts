// 로그인 화면에서 "최근에 이걸로 로그인했어요" 힌트를 보여주기 위한 저장소.
// 계정 속성이 아니라 이 브라우저/기기에 한정된 UI 힌트라 서버가 아니라 localStorage에 저장한다
// (useGeolocation.ts의 동의 상태 저장과 같은 방식, 2026-09-13).
const KEY = 'last-login-provider'

export type LoginProvider = 'google' | 'kakao'

export function saveLastLoginProvider(provider: LoginProvider) {
  try {
    localStorage.setItem(KEY, provider)
  } catch {
    // localStorage를 못 쓰는 환경(프라이빗 모드 등)이면 힌트 없이 넘어간다.
  }
}

export function getLastLoginProvider(): LoginProvider | null {
  try {
    const value = localStorage.getItem(KEY)
    return value === 'google' || value === 'kakao' ? value : null
  } catch {
    return null
  }
}
