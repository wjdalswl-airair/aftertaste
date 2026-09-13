import { loadKakaoAuth } from './kakaoAuth'

export type ShareContent = {
  url: string
  title: string
  description?: string
  imageUrl: string
  // 카카오톡 카드의 버튼 문구. 명소는 "촬영지 보러가기", 코스는 "나만의 코스 보러가기"처럼
  // 공유하는 대상에 맞게 각 페이지에서 넘겨준다. 안 넘기면 기본값을 쓴다.
  buttonLabel?: string
}

// 카카오톡 공유하기. loadKakaoAuth()가 로그인 버튼과 똑같이 SDK 로딩+init을 기다려준다
// (이름은 "Auth"지만 카카오 JS SDK 자체를 한 번만 로딩하는 공용 로더라 공유에도 그대로 쓴다).
// 카카오 개발자 콘솔에서 "카카오톡 공유" 기능이 켜져 있어야 실제로 전송된다.
export async function shareToKakao(content: ShareContent): Promise<void> {
  const kakao = await loadKakaoAuth()
  if (!kakao) {
    throw new Error('카카오 공유를 사용할 수 없습니다')
  }
  kakao.Share.sendDefault({
    objectType: 'feed',
    content: {
      title: content.title,
      description: content.description,
      imageUrl: content.imageUrl,
      link: { mobileWebUrl: content.url, webUrl: content.url },
    },
    // 카카오톡 공유는 한국어 사용자가 주 대상이라 버튼 문구를 다국어로 안 뺐다.
    buttons: [
      { title: content.buttonLabel ?? '자세히 보기', link: { mobileWebUrl: content.url, webUrl: content.url } },
    ],
  })
}

// X(트위터) 공유 — 웹 인텐트라 SDK 없이 새 창만 열면 된다. text엔 제목+설명을 같이 넣지만,
// 트위터 자체 글자수 제한(280자)에 걸리면 트위터가 알아서 잘라 보여준다.
export function shareToX({ url, title, description }: { url: string; title: string; description?: string }): void {
  const text = [title, description].filter(Boolean).join('\n')
  const params = new URLSearchParams({ url, text })
  window.open(`https://twitter.com/intent/tweet?${params.toString()}`, '_blank', 'noopener,noreferrer')
}

// LINE 공유 — 일본어(ja)·중국어 번체(zh-TW) 사용자권에서 카카오톡만큼 지배적인 메신저.
// lineit/share는 공식적으로 url만 받는다(자체 텍스트 삽입 기능이 없음) — 미리보기는 그 URL의
// OG 태그를 LINE이 직접 읽어서 만드는데, 이 앱은 페이지별 OG 태그가 없어 기본값만 뜬다.
export function shareToLine({ url }: { url: string }): void {
  const params = new URLSearchParams({ url })
  window.open(`https://social-plugins.line.me/lineit/share?${params.toString()}`, '_blank', 'noopener,noreferrer')
}

// WhatsApp 공유 — 그 외 해외권에서 범용적으로 쓰이는 메신저. text 파라미터 하나가 메시지 전체라
// 제목+설명+링크를 그대로 다 채워 넣을 수 있다(이미지·카드는 지원 안 함).
export function shareToWhatsApp({
  url,
  title,
  description,
}: {
  url: string
  title: string
  description?: string
}): void {
  const text = [title, description, url].filter(Boolean).join('\n')
  const params = new URLSearchParams({ text })
  window.open(`https://wa.me/?${params.toString()}`, '_blank', 'noopener,noreferrer')
}

export function copyShareLink(url: string): Promise<void> {
  return navigator.clipboard.writeText(url)
}
