from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


def lower_similarity_threshold(apps, schema_editor):
    """pg_trgm의 기본 유사 판정 기준(0.3)을 0.1로 낮춘다.

    "경보궁"으로 "경복궁"을 찾는 예시처럼, 짧은 한글 이름은 글자 하나만 바뀌어도
    기본값 0.3 기준으로는 다른 이름으로 취급돼 못 찾는다(직접 계산해보니 실제
    유사도는 약 0.14). 완전히 다른 이름끼리는 유사도가 0으로 나오는 걸 확인했으므로
    0.1로 낮춰도 엉뚱한 결과가 섞일 위험은 낮다.
    """

    db_name = schema_editor.connection.settings_dict["NAME"]
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'ALTER DATABASE "{db_name}" SET pg_trgm.similarity_threshold = 0.1')


def reset_similarity_threshold(apps, schema_editor):
    db_name = schema_editor.connection.settings_dict["NAME"]
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'ALTER DATABASE "{db_name}" RESET pg_trgm.similarity_threshold')


class Migration(migrations.Migration):
    """오타·끝글자 누락 검색(유사 검색)을 위해 PostgreSQL의 pg_trgm 확장을 켠다.

    이름이 완전히 똑같지 않아도 글자가 비슷하면 찾아주는 기능(TrigramSimilarity,
    trigram_similar 조회)이 이 확장에 의존한다.
    """

    dependencies = [
        ("places", "0003_alter_placesource_source_id"),
    ]

    operations = [
        TrigramExtension(),
        migrations.RunPython(lower_similarity_threshold, reset_similarity_threshold),
    ]
