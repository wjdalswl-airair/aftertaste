// 주소 앞 두 토큰을 짧은 지역명으로 쓴다 (예: "경기도 수원시 팔달구..." → "경기도 수원시").
// BE 응답엔 지역명 필드가 따로 없어서 임시로 이렇게 잘라 쓴다.
export function shortRegion(address: string): string {
  return address.split(' ').slice(0, 2).join(' ')
}
