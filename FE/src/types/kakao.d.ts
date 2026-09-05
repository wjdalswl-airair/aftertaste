// 카카오맵 JS SDK는 별도 npm 타입 패키지가 없어서, 이 프로젝트에서 실제로 쓰는 부분만 최소로 선언한다.
export {}

declare global {
  namespace kakao.maps {
    class LatLng {
      constructor(lat: number, lng: number)
    }

    class Map {
      constructor(container: HTMLElement, options: { center: LatLng; level?: number })
      setCenter(latlng: LatLng): void
    }

    class Marker {
      constructor(options: { position: LatLng; map?: Map; title?: string })
      setMap(map: Map | null): void
    }

    class InfoWindow {
      constructor(options: { content: string })
      open(map: Map, marker: Marker): void
      close(): void
    }

    function load(callback: () => void): void

    namespace event {
      function addListener(target: unknown, type: string, handler: () => void): void
    }

    namespace services {
      enum Status {
        OK = 'OK',
        ZERO_RESULT = 'ZERO_RESULT',
        ERROR = 'ERROR',
      }

      // 좌표 → 행정동/법정동 변환 결과. 실제 API 응답에서 쓰는 필드만 선언한다.
      type RegionCode = {
        region_type: 'H' | 'B' // H: 행정동, B: 법정동
        address_name: string
        region_1depth_name: string
        region_2depth_name: string
        region_3depth_name: string
      }

      class Geocoder {
        // 카카오 API 인자 순서는 (경도, 위도) — LatLng과 반대 순서라 헷갈리기 쉽다.
        coord2RegionCode(x: number, y: number, callback: (result: RegionCode[], status: Status) => void): void
      }
    }
  }

  interface Window {
    kakao: typeof kakao
  }
}
