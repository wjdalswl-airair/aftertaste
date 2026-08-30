import { getDownloadURL, ref, uploadBytes } from 'firebase/storage'
import { auth, storage } from './firebase'

// 리뷰 사진을 Firebase Storage에 올리고 다운로드 URL을 돌려준다.
// BE는 이미 업로드된 사진 URL만 받는 구조라(ReviewWriteSerializer의 photo_urls),
// 실제 파일 업로드는 FE가 여기서 직접 처리한다.
export async function uploadReviewPhoto(file: File): Promise<string> {
  const uid = auth.currentUser?.uid
  if (!uid) {
    throw new Error('로그인이 필요합니다')
  }

  const path = `reviews/${uid}/${Date.now()}-${file.name}`
  const fileRef = ref(storage, path)
  await uploadBytes(fileRef, file)
  return getDownloadURL(fileRef)
}
