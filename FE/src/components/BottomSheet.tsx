import type { ReactNode } from 'react'

type BottomSheetProps = {
  onClose: () => void
  children: ReactNode
}

// 화면 아래에서 올라오는 범용 바텀시트 껍데기. 배경(딤) 클릭하면 닫힌다.
// 리뷰 상세의 수정/삭제 메뉴 스타일을 기준으로 통일했다 (드래그 핸들바 포함).
export function BottomSheet({ onClose, children }: BottomSheetProps) {
  return (
    <div className="fixed inset-0 z-50 mx-auto w-full max-w-[480px]">
      <button type="button" aria-label="닫기" className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="absolute inset-x-0 bottom-0 flex flex-col">
        <div className="w-full animate-[sheet-up_0.2s_ease-out] rounded-t-2xl bg-white pb-8 pt-2">
          <div className="mx-auto mt-1.5 h-[3px] w-[46px] rounded-full bg-divider" />
          {children}
        </div>
      </div>
    </div>
  )
}