from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from main.models import Banner
from main.serializers import BannerListResponseSerializer, BannerSerializer


class BannerListView(ListAPIView):
    """메인 화면 배너 목록. 로그인 없이 볼 수 있고, 활성화된 배너만 노출 순서대로 보여준다."""

    serializer_class = BannerSerializer
    queryset = Banner.objects.filter(is_active=True)

    @extend_schema(
        summary="배너 목록 조회",
        description="활성화된 배너를 노출 순서대로 반환한다. 로그인이 필요 없다.",
        responses={200: BannerListResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"banners": serializer.data})
