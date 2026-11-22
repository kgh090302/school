# 🏫 학교 대신 전해드립니다 (학생용 + 관리자용)

학생 건의사항을 AI가 요약·부서 배정하고, 학생회가 처리 상태를 관리하는 Streamlit 웹사이트입니다.
데이터는 예전의 `complaints.csv` 대신 **Supabase(Postgres)** 에 저장됩니다.

## 폴더 구성

| 파일 | 설명 |
|---|---|
| `student_app.py` | 학생용 앱 (민원 작성 / 공개 게시판) |
| `admin_app.py` | 관리자용 앱 (비밀 민원 / 상태 관리 / AI 보고서) |
| `db.py` | CSV 읽기·쓰기를 Supabase로 바꿔주는 데이터 계층 (이 파일만 DB를 만집니다) |
| `ui.py` | 두 앱이 함께 쓰는 CSS 스타일과 상단 배너 |
| `supabase_setup.sql` | Supabase 테이블 + 보안 규칙 + 권한 설정 (이미 적용 완료) |
| `streamlit_secrets_student.toml` | 학생용 앱 배포 시 Secrets 에 붙여넣을 내용 (URL·공개 키 입력됨) |
| `streamlit_secrets_admin.toml` | 관리자용 앱 배포 시 Secrets 에 붙여넣을 내용 (secret 키·비밀번호 채워야 함) |
| `.streamlit/config.toml` | 테마 색상 |
| `.streamlit/secrets.toml.example` | 내 컴퓨터에서 실행할 때 쓰는 키 설정 예시 |

> 기존 `complaints.csv` 는 Supabase로 옮겼기 때문에 이 폴더에 넣지 않았습니다. 학생 글(비밀글 포함)이 GitHub 에 올라가지 않도록 **저장소는 Private 으로** 만들고, 원본 CSV 는 따로 보관하세요.

기존 앱 로직(AI 프롬프트, 부서 배정, 비밀글 분리, 공감, 상태 관리, 월간 보고서)은 그대로입니다.
바뀐 것은 ① CSV 읽기/쓰기 → `db.py` 호출, ② UI 스타일, ③ 비밀번호·API 키를 `secrets`에서 읽을 수 있게 한 것뿐입니다.

## 1. Supabase 준비 (한 번만)

1. [supabase.com](https://supabase.com) 에서 새 프로젝트 생성 (무료 플랜 가능)
2. 왼쪽 메뉴 **SQL Editor** → `supabase_setup.sql` 내용을 전부 붙여넣고 **Run**
3. **Table Editor → complaints** 에서 기존 6건이 들어왔는지 확인 ← 여기서 데이터를 눈으로 확인할 수 있습니다
4. **Project Settings → API Keys** 에서 아래 값을 복사해 둡니다
   - Project URL → `SUPABASE_URL`
   - publishable (또는 anon) 키 → `SUPABASE_KEY` (학생용 앱)
   - secret (또는 service_role) 키 → `SUPABASE_SERVICE_KEY` (관리자용 앱)

## 2. 내 컴퓨터에서 실행

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # 열어서 값 채우기

streamlit run student_app.py                       # 학생용
streamlit run admin_app.py --server.port 8502      # 관리자용
```

## 3. 인터넷에 배포 (Streamlit Community Cloud)

1. 이 폴더를 GitHub에 올립니다. **`.streamlit/secrets.toml` 은 올리지 마세요.**
2. [share.streamlit.io](https://share.streamlit.io) 에서 앱을 **2개** 만듭니다 (같은 저장소, 메인 파일만 다르게)
   - 학생용: `student_app.py`
   - 관리자용: `admin_app.py`
3. 각 앱의 **Settings → Secrets** 에 아래처럼 입력합니다.

학생용 앱
```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "sb_publishable_..."
# OPENAI_API_KEY = "sk-..."   # 선택
```

관리자용 앱
```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_SERVICE_KEY = "sb_secret_..."
ADMIN_PASSWORD = "바꾼-비밀번호"
# OPENAI_API_KEY = "sk-..."   # 선택
```

## 보안 구조

- 학생용 앱은 공개용 키만 가지며, DB 규칙(RLS) 때문에 **비밀글 행 자체를 받아올 수 없습니다.**
  (코드의 `비밀글 == False` 필터가 없어도 DB가 먼저 막아줍니다.)
- 학생용 앱은 테이블에 직접 쓰지 못하고, `submit_complaint` / `add_like` 함수로만 쓸 수 있습니다.
  상태는 항상 `접수 완료`, 공감수는 항상 0으로 시작하고, 공감은 DB 안에서 +1 됩니다.
- **`SUPABASE_SERVICE_KEY` 는 관리자용 앱에만** 넣으세요. 모든 데이터를 읽고 쓸 수 있는 키입니다.
- 관리자 비밀번호 기본값은 `1234` 입니다. 배포할 때는 반드시 `ADMIN_PASSWORD` 로 바꾸세요.
  (바꾸면 로그인 실패 메시지에서 기본값 안내도 사라집니다.)

## 참고

- 기존에는 학생이 사이드바에 OpenAI API 키를 직접 입력해야 했습니다. 그 방식은 그대로 동작하고,
  `OPENAI_API_KEY` 를 secrets에 넣으면 입력 없이 바로 쓸 수 있습니다. (사용 비용은 키 주인이 부담)
- 관리자 화면의 "변경된 상태 서버에 저장"은 달라진 행의 상태·담당 부서·비밀 여부만 DB에 반영합니다.
