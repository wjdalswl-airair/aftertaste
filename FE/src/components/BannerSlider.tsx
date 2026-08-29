import { useEffect, useState } from 'react'
import { getBanners, type Banner } from '../api/main'

export function BannerSlider() {
  const [banners, setBanners] = useState<Banner[]>([])

  useEffect(() => {
    getBanners()
      .then(setBanners)
      .catch(() => setBanners([]))
  }, [])

  if (banners.length === 0) {
    return null
  }

  return (
    <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto px-4">
      {banners.map((banner) => (
        <a
          key={banner.id}
          href={banner.link_url || undefined}
          className="aspect-[16/9] w-full flex-shrink-0 snap-center overflow-hidden rounded-lg"
        >
          <img src={banner.image_url} alt="" className="h-full w-full object-cover" />
        </a>
      ))}
    </div>
  )
}
