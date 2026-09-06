"""(title_key, category) 유일 제약. 0009의 중복 병합이 끝난 뒤 별도 트랜잭션에서 건다."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("places", "0009_work_title_key"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="work",
            constraint=models.UniqueConstraint(
                fields=("title_key", "category"), name="uniq_work_title_key_category"
            ),
        ),
    ]
