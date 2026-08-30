# 로컬에서 BE 서버 켜는 법

FE에서 로그인 같은 기능을 실제로 테스트하려면 BE 서버가 내 컴퓨터에서 켜져 있어야 한다. 이 문서는 그 방법과, 처음 설정할 때 겪었던 문제들을 정리한 것이다.

## Docker가 뭔지 모르겠다면

**Docker**는 "프로그램을 필요한 환경까지 통째로 포장해서, 어느 컴퓨터에서 실행해도 똑같이 동작하게 만들어주는 도구"다.

우리 프로젝트는 데이터베이스로 Postgres를 쓰는데, 이걸 팀원 각자 컴퓨터에 따로따로 설치하면 버전이나 설정(계정, 비밀번호, DB 이름 등)이 조금씩 달라질 수 있다. Docker를 쓰면 "이런 설정의 Postgres를 띄워라"는 내용을 파일 하나(`docker-compose.yml`)에 적어두고, 누가 실행하든 완전히 똑같은 Postgres가 뜬다.

헷갈리기 쉬운 용어 3개만 구분하면 된다.

| 용어 | 뜻 | 비유 |
|---|---|---|
| **이미지 (image)** | "이렇게 생긴 프로그램을 만들어라"는 설계도/포장 | 밀키트 (재료 + 레시피) |
| **컨테이너 (container)** | 그 설계도로 실제 켜진, 진짜 돌아가는 프로그램 | 밀키트로 실제 만든 요리 |
| **Docker Desktop** | 이미지를 내려받고 컨테이너를 켜고 끄는 걸 관리해주는 앱 (Windows에서 Docker를 쓰려면 이게 켜져 있어야 함) | 요리를 만드는 주방 |

우리가 쓰는 `docker-compose`는 이미지·컨테이너를 하나씩 다루는 대신, `docker-compose.yml`에 적힌 여러 개를 한 번에 켜고 끄게 해주는 **도구**다 (컨테이너 자체가 아니다). `docker compose up -d`라고 치면 그 파일에 적힌 Postgres 컨테이너가 만들어지고 백그라운드에서 켜진다.

## 한 번만 하면 되는 준비

### 1. Docker Desktop 설치

Postgres(데이터베이스)를 내 컴퓨터에 직접 설치하지 않고 Docker로 띄우기 위해 필요하다.

- https://www.docker.com/products/docker-desktop/ 에서 Windows용(AMD64) 다운로드
- 설치 후 재부팅
- Docker Desktop 실행 → 트레이에 고래 아이콘 뜨면 준비 완료

### 2. Python 가상환경 만들고 패키지 설치

```
cd BE
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

> ⚠️ **겪었던 문제**: Python 3.14 환경에서 `requirements.txt`에 적힌 `psycopg2-binary==2.9.10`이 설치가 안 됐다. 이 버전엔 Python 3.14용으로 미리 빌드된 파일이 없어서 직접 빌드를 시도하다가 실패했다(`pg_config` 없음 에러).
> **해결**: 더 최신 버전인 `psycopg2-binary==2.9.12`엔 Python 3.14용 파일이 있어서, 이것만 따로 설치했다.
> ```
> venv\Scripts\python.exe -m pip install psycopg2-binary==2.9.12
> venv\Scripts\python.exe -m pip install Django==5.2.17 django-cors-headers==4.9.0 djangorestframework==3.17.2 drf-spectacular==0.30.0 firebase-admin==6.9.0
> ```
> `requirements.txt`엔 여전히 2.9.10으로 적혀 있으니, BE 담당자에게 버전을 올려달라고 알려주는 게 좋다.

## 매번 켤 때 하는 것

### 1. Postgres 컨테이너 켜기

```
cd BE
docker compose up -d
```

> ⚠️ **겪었던 문제 1**: Docker Desktop을 설치해도 터미널에서 `docker` 명령어가 안 먹혔다. 원인은 이 컴퓨터에서 Docker가 `C:\Program Files\Docker\...`가 아니라 `C:\Users\내계정\AppData\Local\Programs\DockerDesktop\...`(사용자 폴더 안)에 설치돼서, 이 경로가 PATH(명령어를 찾는 목록)에 없었기 때문이다.
> **해결**: 새 터미널을 열거나 컴퓨터를 재시작하면 보통 자동으로 잡힌다. 그래도 안 되면 그 폴더의 `resources\bin`을 PATH에 추가하면 된다.

> ⚠️ **겪었던 문제 2**: `docker compose up -d`를 처음 실행했을 때 `docker-credential-desktop 못 찾음` 에러가 났다. 이것도 같은 폴더(`resources\bin`)에 있는데 PATH에 없어서 생긴 문제였다. 문제 1이 해결되면 같이 해결된다.

정상적으로 켜지면 이렇게 보인다:
```
docker compose ps
NAME      IMAGE         STATUS         PORTS
be-db-1   postgres:16   Up             0.0.0.0:5432->5432/tcp
```

### 2. DB 마이그레이션 (테이블이 없거나 바뀌었을 때만)

```
venv\Scripts\python.exe manage.py migrate
```

### 3. 서버 실행

```
venv\Scripts\python.exe manage.py runserver
```

### 4. 확인

브라우저에서 http://127.0.0.1:8000/api/docs/ 열어서 Swagger 문서가 보이면 성공.

## 아직 남은 것

- `BE/firebase-service-account.json` 파일이 없으면, 서버는 켜져도 로그인 API를 실제로 호출할 때(토큰 검증 시점) 에러가 날 수 있다. Firebase 콘솔 → 프로젝트 설정 → 서비스 계정 → "새 비공개 키 생성"으로 받아서 `BE/` 폴더에 넣어야 한다.
