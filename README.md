# APT.i 관리비 명세서 자동 수집 및 Notion 대시보드 생성

아파트아이(APT.i)의 관리비 명세서를 자동으로 크롤링하여, 사용자의 Notion 데이터베이스에 시각화된 대시보드를 자동으로 생성해주는 프로젝트입니다.

## 주요 기능

- **자동 데이터 수집**: Playwright를 사용하여 APT.i 사이트에서 관리비 정보 자동 수집
- **Notion 대시보드 생성**: 수집한 데이터를 시각화된 대시보드 형식으로 Notion 페이지에 자동 생성
- **중복 방지**: 같은 월의 데이터는 자동으로 업데이트
- **상세 분석**: 관리비 항목별 증감, 에너지 사용량 비교, 납부 이력 등 제공
<<<<<<< HEAD
=======
- **전체 항목 수집**: 더보기 버튼 자동 클릭으로 모든 관리비 항목(24개) 수집
>>>>>>> 386246cedcee5519c52193727a502fbee2b3b1b8

## 1. Notion 데이터베이스 준비

### 데이터베이스 생성

1. Notion에서 새 페이지 생성
2. `/database inline` 명령어로 인라인 데이터베이스 생성
3. 또는 기존 데이터베이스 사용 (예: `https://www.notion.so/2eda8076a34780f682cacc2b1dd91150`)

### 데이터베이스 속성 설정

다음 속성들을 추가/수정합니다:

| 속성명 | 유형 | 설명 |
|--------|------|------|
| **이름** (Name) | Title | 페이지 제목 (자동 생성: "YYYY년 M월 관리비") |
| **동호수** | Text | 아파트 동호수 (예: "1306동 1001호") |
| **청구월** | Select | 부과 월 (1월~12월) |
| **총 납부액** | Number | 관리비 총액 (원) |
| **💧 수도요금** | Number | 수도 요금 (원) |
| **🔥 난방/가스** | Number | 난방/가스 요금 (원) |
| **⚡ 전기요금** | Number | 전기 요금 (원) |
| **수집일시** | Date | 데이터 수집 일시 |
| **납부기한** | Date | 납부 마감일 |

> **참고**: 현재 데이터베이스에는 위 속성들이 이미 설정되어 있습니다. 필요에 따라 추가 속성(상태, 태그 등)을 추가할 수 있습니다.

### [중요] Notion API 통합(Integration) 연결

1. **Notion My Integrations**에서 새 통합 생성
   - https://www.notion.so/my-integrations 접속
   - "New integration" 클릭
   - 이름 입력 (예: "APT.i Collector")
   - "Submit" 클릭

2. **Internal Integration Secret (토큰) 복사**
   - 생성된 통합 페이지에서 "Internal Integration Token" 복사
   - 형식: `secret_...`

3. **데이터베이스에 통합 연결**
   - 노션 데이터베이스 페이지 우측 상단 `...` 메뉴 클릭
   - "연결" (Connections) 선택
   - 만든 통합 선택하여 초대

## 2. 환경 변수 설정

### 로컬 실행 시 (.env 파일 또는 환경 변수)

프로젝트 폴더에 `.env` 파일을 만들거나, 환경 변수로 다음 값을 설정하세요:

```bash
# 아파트아이 계정 정보
APTI_USER_ID="아이디_또는_휴대폰번호"
APTI_PASSWORD="비밀번호"

# Notion API 정보
NOTION_TOKEN="secret_..."  # 위에서 발급받은 시크릿 키
NOTION_DATABASE_ID="2eda8076a34780f682cacc2b1dd91150"  # 공유해주신 링크의 ID
```

### Windows PowerShell에서 환경 변수 설정

```powershell
$env:APTI_USER_ID="01045439365"
$env:APTI_PASSWORD="your_password"
$env:NOTION_TOKEN="secret_..."
$env:NOTION_DATABASE_ID="2eda8076a34780f682cacc2b1dd91150"
```

### GitHub Actions 사용 시 (Secrets 설정)

저장소 Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 | 설명 |
|-------------|-----|------|
| `APTI_USER_ID` | APT.i 로그인 ID | APT.i 아이디 또는 휴대폰 번호 |
| `APTI_PASSWORD` | APT.i 비밀번호 | APT.i 비밀번호 |
| `NOTION_TOKEN` | Notion Integration Token | `secret_...` 형식 |
| `NOTION_DATABASE_ID` | Notion Database ID | Database URL에서 추출한 ID |

## 3. 실행 방법

### 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt
playwright install chromium

# 2. 환경 변수 설정 (위 참고)

# 3. 실행
python main.py
```

### GitHub Actions 자동 실행

1. 저장소 → Actions 탭
2. "APT.i 데이터 수집 및 Notion 전송" 워크플로우 선택
3. "Run workflow" 클릭하여 수동 실행 테스트
4. 자동 실행은 `.github/workflows/parse.yml`의 스케줄에 따라 실행됩니다

## 4. 결과 확인

실행이 완료되면 노션 데이터베이스에 다음과 같은 페이지가 생성됩니다:

### 페이지 제목
- **제목**: `2025년 11월 관리비` (예시)

### 페이지 속성 (데이터베이스 컬럼)
- 동호수: 1306동 1001호
- 청구월: 11월
- 총 납부액: 347,220원
- 💧 수도요금: 22,480원
- 🔥 난방/가스: 76,380원
- ⚡ 전기요금: 35,010원
- 수집일시: 2026-01-19
- 납부기한: 2025-12-31

### 페이지 내용 (대시보드)

<<<<<<< HEAD
#### 🚨 요약 및 연간 월별 추이
- 동호 정보 및 이번 달 납부 금액
- 납부 마감일
- 전년동월 비교 데이터
- 우리아파트 동일면적 비교 (최저/평균)
- 에너지사용량 동일면적 비교
- 연간 월별 추이 테이블 (12개월)
=======
#### 🏠 요약 헤더
- 동호 정보 및 이번 달 납부 금액
- 납부 마감일 (미납 시 빨간색 표시)
- 최근 6개월 추이 텍스트
>>>>>>> 386246cedcee5519c52193727a502fbee2b3b1b8

#### 📊 에너지 상세 분석 (맨 위 위치)
- **에너지별 요약** (왼쪽 컬럼)
  - 전기, 온수, 수도, 난방 등
  - 사용량, 청구액
- **이웃 평균 비교** (오른쪽 컬럼)
  - 각 에너지 종류별 이웃 평균 대비 비교 문구

#### 📑 관리비 상세 내역 (중앙 위치, 토글 블록)
- **가로 2열 레이아웃**: 항목을 가로로 2개씩 나란히 표시
- **당월 금액 기준 내림차순 정렬**: 금액이 큰 항목부터 표시
- **토글 기능**: 접기/펼치기 가능
- 각 항목별 정보:
  - 항목명 (굵게 표시)
  - 당월 금액
  - 전월 대비 증감 (🔺 증가, 🔽 감소 표시)

#### 💳 납부 이력 (토글 블록)
- 최근 6개월 납부 내역
  - 결제일, 금액, 청구월, 마감일, 은행, 방법, 상태

#### 📎 고지서 원본 (토글 블록)
- 전체 원본 JSON 데이터

## 프로젝트 구조

```
apti/
├── .github/
│   └── workflows/
│       └── parse.yml          # GitHub Actions 워크플로우
├── apti_parser.py            # APT.i 데이터 파서 (Playwright)
├── notion_sender.py          # Notion 대시보드 생성 모듈
├── main.py                    # 메인 스크립트
<<<<<<< HEAD
├── run_parser.py           # 파서 테스트용 스크립트 (JSON 저장)
=======
>>>>>>> 386246cedcee5519c52193727a502fbee2b3b1b8
├── requirements.txt           # Python 의존성
├── README.md                  # 프로젝트 설명
└── .gitignore
```

## 수집되는 데이터

### 전체 데이터 구조

```json
{
  "timestamp": "2026-01-19T13:09:22.206384",
  "dong_ho": "13061001",
  "maint_items": [
    {
      "item": "일반관리비",
      "current": "49950",
      "previous": "49780",
      "change": "170"
    },
    ...
  ],
  "maint_payment": {
    "amount": "347220",
    "charged": "347220",
    "month": "11",
    "deadline": "2025년 12월 31일",
    "status": "납기후",
    "comparison": {
      "previous_year": "347220",
      "same_area_lowest": "...",
      "same_area_average": "..."
    }
  },
  "energy_category": [
    {
      "type": "전기",
      "usage": "232.00",
      "cost": "35010",
      "comparison": "우리집이 평균 요금보다 21,234원 적게 사용했습니다."
    },
    ...
  ],
  "energy_type": [],
  "payment_history": [
    {
      "date": "2025.12.24",
      "amount": "347220",
      "billing_month": "2025.11",
      "deadline": "2025.12.31",
      "bank": "현대카드",
      "method": "신용카드자동이체",
      "status": "납부완료"
    },
    ...
  ]
}
```

## 문제 해결

### 파싱 실패
1. APT.i 자격증명 확인
2. 사이트 구조 변경 여부 확인
3. Playwright 브라우저 설치 확인: `playwright install chromium`
4. 로그 확인: 터미널 출력 또는 GitHub Actions 로그

### Notion 전송 실패
1. Notion Integration Token 확인
2. Database ID 확인 (URL에서 추출)
3. Database에 Integration이 연결되어 있는지 확인
4. Database 속성명이 코드와 일치하는지 확인
5. Notion API 권한 확인 (읽기/쓰기 권한 필요)

### 환경 변수 오류
- Windows PowerShell: `$env:변수명="값"` 형식 사용
- Linux/Mac: `export 변수명="값"` 형식 사용
- `.env` 파일 사용 시: `python-dotenv` 패키지 필요

## 스케줄 변경

`.github/workflows/parse.yml` 파일에서 cron 표현식 수정:

```yaml
schedule:
  - cron: '0 12 * * *'  # 매일 한국시간 오후 9시 (UTC 12시)
```

## 라이선스

MIT License
