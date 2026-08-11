from rest_framework import serializers

from accounts.models import Member


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = [
            "id",
            "email",
            "nickname",
            "profile_image_url",
            "provider",
            "nationality",
            "language",
            "created_at",
        ]
        read_only_fields = fields
