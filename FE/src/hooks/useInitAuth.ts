import { onAuthStateChanged } from 'firebase/auth'
import { useEffect } from 'react'
import { loginWithFirebase } from '../api/auth'
import { auth } from '../lib/firebase'
import { useAuthStore } from '../store/useAuthStore'

// 앱이 켜질 때 한 번, Firebase 로그인 상태를 감지해서 우리 서버 회원 정보와 맞춘다.
// 새로고침해도 Firebase가 로그인 상태를 기억하고 있으면 여기서 다시 회원 정보를 받아온다.
export function useInitAuth() {
  const setMember = useAuthStore((state) => state.setMember)
  const setLoading = useAuthStore((state) => state.setLoading)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (!user) {
        setMember(null)
        setLoading(false)
        return
      }

      try {
        const member = await loginWithFirebase()
        setMember(member)
      } catch (error) {
        console.error('로그인 처리에 실패했어요', error)
        setMember(null)
      } finally {
        setLoading(false)
      }
    })

    return unsubscribe
  }, [setMember, setLoading])
}
