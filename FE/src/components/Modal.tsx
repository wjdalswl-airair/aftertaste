import type { ReactNode } from 'react'

type ModalProps = {
  title: string
  onClose: () => void
  children: ReactNode
}

// 화면 가운데 뜨는 범용 모달. 배경(딤) 클릭하면 닫힌다.
export function Modal({ title, onClose, children }: ModalProps) {
  return (
    <div className="fixed inset-0 z-50 mx-auto w-full max-w-[480px]">
      <button type="button" aria-label="닫기" className="absolute inset-0 bg-black/40" onClick={onClose} />
      {/* 위 배경 버튼과 똑같이 화면 전체(inset-0)를 덮는 wrapper라, 여기에도 onClose를 걸어야
          카드 바깥 여백(padding 부분)을 눌러도 닫힌다 — 안 걸면 이 div가 클릭을 가로채서 배경
          버튼까지 안 전달된다. 카드 자체 클릭은 stopPropagation으로 막아 닫히지 않게 한다. */}
      <div className="absolute inset-0 flex items-center justify-center px-4" onClick={onClose}>
        <div
          className="relative max-h-[80dvh] w-full max-w-sm overflow-y-auto rounded-2xl bg-white p-5"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-bold text-ink">{title}</h2>
            <button type="button" onClick={onClose} aria-label="닫기" className="text-ink-tertiary">
              ✕
            </button>
          </div>
          <div className="text-sm text-ink-secondary">{children}</div>
        </div>
      </div>
    </div>
  )
}
