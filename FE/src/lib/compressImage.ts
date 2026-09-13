// 휴대폰 카메라 사진은 보통 3~8MB라 압축 없이 그대로 올리면 업로드가 눈에 띄게 오래 걸린다.
// 캔버스로 긴 변을 MAX_DIMENSION 이하로 줄이고 WebP로 다시 인코딩해서 용량을 크게 줄인다.
// WebP는 같은 화질 기준으로 JPEG보다 파일이 더 작다(Storage 비용 절감) — 모바일 전용 서비스라
// 지원 브라우저 문제도 거의 없다(2026-09-13, JPEG에서 전환).
const MAX_DIMENSION = 1600
const OUTPUT_MIME_TYPE = 'image/webp'
const OUTPUT_QUALITY = 0.8

// 브라우저가 <img>로 그대로 띄울 수 있다고 보장되는 포맷만 압축 실패 시 원본으로 폴백한다.
const DISPLAYABLE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']

// 아이폰 기본 사진 포맷(HEIC/HEIF)처럼 createImageBitmap이 디코딩 자체를 못 하는 파일에서 던진다.
// 이런 파일은 압축은커녕 대부분의 브라우저 <img>에서도 안 보이므로, 원본을 그대로 올려봐야
// 나중에 리뷰 피드에 깨진 이미지로 나타난다 — 업로드 시도 전에 바로 알려준다.
export class UnsupportedImageError extends Error {}

// 업로드 용량 제한(Storage 보안 규칙과 동일한 기준)을 넘겼을 때 reviewPhotoUpload·profilePhotoUpload가 던진다.
export class PhotoTooLargeError extends Error {}

export async function compressImage(file: File): Promise<Blob> {
  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file)
  } catch {
    if (!DISPLAYABLE_TYPES.includes(file.type)) {
      throw new UnsupportedImageError(`지원하지 않는 이미지 형식: ${file.type || 'unknown'}`)
    }
    // 표준 이미지 포맷인데도 디코딩이 실패한 드문 경우(파일 손상 등) — 압축만 포기하고
    // 원본은 그대로 올려본다(형식 자체는 브라우저가 표시할 수 있는 것으로 신뢰).
    return file
  }

  const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height))
  const width = Math.round(bitmap.width * scale)
  const height = Math.round(bitmap.height * scale)

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return file
  }
  ctx.drawImage(bitmap, 0, 0, width, height)

  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, OUTPUT_MIME_TYPE, OUTPUT_QUALITY))
  return blob ?? file
}
