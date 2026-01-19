# APT.i 데이터 수집 및 Notion 전송

APT.i (아파트아이) 관리비 정보를 자동으로 수집하여 Notion Database에 저장하는 프로젝트입니다.

## 주요 기능

- **자동 데이터 수집**: GitHub Actions를 통해 매일 자동으로 APT.i 사이트에서 데이터 수집
- **Notion 연동**: 수집한 데이터를 Notion Database에 자동 저장
- **중복 방지**: 같은 날짜의 데이터는 자동으로 업데이트

## 작동 방식

```
GitHub Actions (매일 자동 실행)
    ↓ Playwright로 APT.i 사이트 파싱
    ↓
데이터 수집 (관리비, 에너지, 납부내역)
    ↓
Notion Database에 페이지 생성/업데이트
```

## 수집되는 데이터

1. **동호 정보**: 아파트 동호수
2. **관리비 항목**: 각 항목별 금액 (이번 달, 전월, 증감)
3. **관리비 납부액**: 총액, 마감일, 상태
4. **에너지 정보**: 전기, 가스, 수도 등 사용량 및 요금
5. **납부내역**: 최근 납부 내역

## 설치 및 설정

### 1. 저장소 클론

```bash
git clone https://github.com/kong9365/Apt_i.git
cd Apt_i
```

### 2. Notion Database 생성

1. Notion에서 새 Database 생성
2. 다음 속성들을 추가:
   - **날짜** (Date): 날짜 필드
   - **동호** (Text): 동호 정보
   - **관리비 총액** (Number): 관리비 총액
   - **납부 마감일** (Text): 납부 마감일
   - **납부 상태** (Text): 납부 상태

3. Database ID 확인:
   - Database URL에서 ID 추출
   - 예: `https://www.notion.so/workspace/abc123def456...`
   - ID는 `abc123def456...` 부분

### 3. Notion Integration 생성

1. https://www.notion.so/my-integrations 접속
2. "New integration" 클릭
3. 이름 입력 (예: "APT.i Collector")
4. Integration Token 복사
5. 생성한 Database에 Integration 연결:
   - Database 우측 상단 "..." 메뉴
   - "Connections" → Integration 선택

### 4. GitHub Secrets 설정

저장소 Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 | 설명 |
|-------------|-----|------|
| `APTI_USER_ID` | APT.i 로그인 ID | APT.i 아이디 또는 휴대폰 번호 |
| `APTI_PASSWORD` | APT.i 비밀번호 | APT.i 비밀번호 |
| `NOTION_TOKEN` | Notion Integration Token | `secret_...` 형식 |
| `NOTION_DATABASE_ID` | Notion Database ID | Database URL에서 추출한 ID |

### 5. GitHub Actions 실행

1. 저장소 → Actions 탭
2. "APT.i 데이터 수집 및 Notion 전송" 워크플로우 선택
3. "Run workflow" 클릭하여 수동 실행 테스트

## 프로젝트 구조

```
apti/
├── .github/
│   └── workflows/
│       └── parse.yml          # GitHub Actions 워크플로우
├── apti_parser.py            # APT.i 데이터 파서
├── notion_sender.py         # Notion 전송 모듈
├── main.py                  # 메인 스크립트
├── requirements.txt         # Python 의존성
├── README.md               # 프로젝트 설명
└── .gitignore
```

## 로컬 테스트

```bash
# 의존성 설치
pip install -r requirements.txt
playwright install chromium

# 환경 변수 설정
export APTI_USER_ID="your_id"
export APTI_PASSWORD="your_password"
export NOTION_TOKEN="secret_..."
export NOTION_DATABASE_ID="database_id"

# 실행
python main.py
```

## Notion Database 스키마

권장 Database 속성:

| 속성명 | 타입 | 설명 |
|--------|------|------|
| 날짜 | Date | 데이터 수집 날짜 |
| 동호 | Text | 아파트 동호수 |
| 관리비 총액 | Number | 관리비 총액 (원) |
| 납부 마감일 | Text | 납부 마감일 |
| 납부 상태 | Text | 납부 상태 (납기내, 납기경과 등) |

페이지 내용에는 다음 섹션이 자동으로 추가됩니다:
- 관리비 항목 (상세 내역)
- 에너지 정보 (사용량 및 요금)
- 납부내역 (최근 10건)

## 스케줄 변경

`.github/workflows/parse.yml` 파일에서 cron 표현식 수정:

```yaml
schedule:
  - cron: '0 12 * * *'  # 매일 한국시간 오후 9시 (UTC 12시)
```

## 문제 해결

### 파싱 실패
1. APT.i 자격증명 확인
2. 사이트 구조 변경 여부 확인
3. GitHub Actions 로그 확인

### Notion 전송 실패
1. Notion Integration Token 확인
2. Database ID 확인
3. Database에 Integration이 연결되어 있는지 확인
4. Database 속성명이 코드와 일치하는지 확인

## 라이선스

MIT License