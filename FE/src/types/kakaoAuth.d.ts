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
      // 카카오톡 공유하기(share.ts에서 사용). 카카오 개발자 콘솔에서 "카카오톡 공유" 기능이
      // 활성화돼 있어야 실제로 전송된다 — 로그인용 JS 키와 앱은 같지만 별도 켜야 하는 기능이다.
      Share: {
        sendDefault(settings: {
          objectType: 'feed'
          content: {
            title: string
            description?: string
            imageUrl: string
            link: { mobileWebUrl: string; webUrl: string }
          }
          buttons?: { title: string; link: { mobileWebUrl: string; webUrl: string } }[]
        }): void
      }
    }
  }
}
