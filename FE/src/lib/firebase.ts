import { initializeApp } from 'firebase/app'
import { GoogleAuthProvider, getAuth } from 'firebase/auth'
import { getStorage } from 'firebase/storage'

// Firebase 프로젝트 설정값. 실제 값은 .env에서 읽는다 (코드에 직접 쓰지 않음).
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

export const firebaseApp = initializeApp(firebaseConfig)
export const auth = getAuth(firebaseApp)
export const storage = getStorage(firebaseApp)

// PRD 결정(2026-09-04 변경): 로그인은 Google/Kakao만 지원한다 (Apple 제외).
// Kakao는 Firebase 기본 제공자가 아니라서 Provider 객체가 따로 없다 — signInWithCustomToken으로 로그인한다
// (DETAIL_SPEC 5장, src/pages/LoginPage.tsx 참고).
export const googleProvider = new GoogleAuthProvider()
