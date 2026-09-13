import type { ReactNode } from 'react'

// 개인정보처리방침·이용약관처럼 조항이 많은 법적 문서 본문을 만들 때 쓰는 공통 조각들.
export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-base font-bold text-ink">{title}</h2>
      {children}
    </section>
  )
}

export function SubSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-bold text-ink">{title}</h3>
      {children}
    </div>
  )
}

export function Bullets({ items, ordered = false }: { items: ReactNode[]; ordered?: boolean }) {
  const ListTag = ordered ? 'ol' : 'ul'
  return (
    <ListTag className={ordered ? 'list-decimal space-y-1 pl-5' : 'list-disc space-y-1 pl-5'}>
      {items.map((item, index) => (
        // eslint-disable-next-line react/no-array-index-key -- 목록 내용 자체가 고유 key로 쓰기엔 너무 길고 순서가 안 바뀌는 정적 데이터라 index를 그대로 쓴다.
        <li key={index}>{item}</li>
      ))}
    </ListTag>
  )
}

export function Divider() {
  return <div className="border-t border-divider" />
}
