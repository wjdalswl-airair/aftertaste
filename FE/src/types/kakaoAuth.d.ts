// 카카오 로그인 JS SDK(window.Kakao)는 지도 SDK(window.kakao)와 별개의 전역이고,
// 별도 npm 타입 패키지가 없어서 이 프로젝트에서 실제로 쓰는 부분만 최소로 선언한다.
export {}

declare global {
  interface Window {
    Kakao?: {
      init(jsKey: string): void
      isInitialized(): boolean
      Auth: {
        // redirectUri로 카카오 로그인 동의 화면을 띄우고, 성공하면 그 주소로 ?code=...를 붙여 되돌아온다.
        authorize(options: { redirectUri: string; scope?: string }): void
      }
    }
  }
}
