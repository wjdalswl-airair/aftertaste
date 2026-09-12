// 휴대폰 카메라 사진은 보통 3~8MB라 압축 없이 그대로 올리면 업로드가 눈에 띄게 오래 걸린다.
// 캔버스로 긴 변을 MAX_DIMENSION 이하로 줄이고 JPEG로 다시 인코딩해서 용량을 크게 줄인다.
const MAX_DIMENSION = 1600
const JPEG_QUALITY = 0.8

export async function compressImage(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file)
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

    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY))
    return blob ?? file
  } catch {
    // 압축이 실패해도 업로드 자체는 막지 않는다 — 원본 파일 그대로 올린다.
    return file
  }
}
