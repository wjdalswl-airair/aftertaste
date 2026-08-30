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
  }

  interface Window {
    kakao: typeof kakao
  }
}
