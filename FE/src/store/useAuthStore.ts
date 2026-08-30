import { create } from 'zustand'
import type { Member } from '../api/auth'

type AuthState = {
  member: Member | null
  // Firebase 로그인 상태를 아직 확인 중이면 true. 확인 전까지는 로그인 화면으로 보내지 않는다.
  isLoading: boolean
  setMember: (member: Member | null) => void
  setLoading: (isLoading: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  member: null,
  isLoading: true,
  setMember: (member) => set({ member }),
  setLoading: (isLoading) => set({ isLoading }),
}))
