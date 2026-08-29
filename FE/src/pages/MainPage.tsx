import { BannerSlider } from '../components/BannerSlider'
import { HallOfFameCard } from '../components/HallOfFameCard'
import { NationalityPicker } from '../components/NationalityPicker'
import { RecommendedSpots } from '../components/RecommendedSpots'
import { TopPlacesCarousel } from '../components/TopPlacesCarousel'

export function MainPage() {
  return (
    <main className="flex min-h-dvh flex-col gap-8 py-6">
      <p className="px-4 font-brand text-2xl text-ink">여운</p>
      <NationalityPicker />
      <BannerSlider />
      <HallOfFameCard />
      <TopPlacesCarousel />
      <RecommendedSpots />
    </main>
  )
}
