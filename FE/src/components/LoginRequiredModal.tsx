import { useNavigate } from 'react-router-dom'
import loginCharacter from '../assets/characters/login.png'
import { Modal } from './Modal'

type LoginRequiredModalProps = {
  onClose: () => void
}

// 로그인이 필요한 기능(즐겨찾기, 좋아요, 리뷰 작성, 메뉴 열기, 마이페이지 진입 등)을
// 비로그인 상태로 시도하면 공통으로 띄우는 팝업. "취소"는 팝업만 닫고, "로그인 하러가기"는
// /login으로 이동한다.
export function LoginRequiredModal({ onClose }: LoginRequiredModalProps) {
  const navigate = useNavigate()

  return (
    <Modal title="" onClose={onClose}>
      <img src={loginCharacter} alt="" className="mx-auto h-24 w-24 object-contain" />
      <p className="mt-2 text-center text-base font-medium text-ink">로그인이 필요합니다</p>
      <div className="mt-6 flex gap-3">
        <button
          type="button"
          onClick={onClose}
          className="flex-1 rounded-full border border-primary py-3 text-sm font-medium text-primary"
        >
          취소
        </button>
        <button
          type="button"
          onClick={() => navigate('/login')}
          className="flex-1 rounded-full bg-primary py-3 text-sm font-medium text-white"
        >
          로그인 하러가기
        </button>
      </div>
    </Modal>
  )
}
