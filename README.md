# APT.i 데이터 수집 및 Notion 전송

APT.i (아파트아이) 관리비 정보를 자동으로 수집하여 Notion Database에 저장하는 프로젝트입니다.

## 주요 기능

- **자동 데이터 수집**: GitHub Actions를 통해 매일 자동으로 APT.i 사이트에서 데이터 수집
- **Notion 연동**: 수집한 데이터를 Notion Database에 자동 저장
- **상세 데이터 저장**: 모든 관리비 항목, 에너지 정보, 납부내역을 테이블 형식으로 저장
- **월별 필터링**: 월별로 데이터를 쉽게 조회할 수 있는 속성 제공
- **중복 방지**: 같은 날짜의 데이터는 자동으로 업데이트

## 작동 방식

```
GitHub Actions (매일 자동 실행)
    ↓ Playwright로 APT.i 사이트 파싱
    ↓
데이터 수집 (관리비, 에너지, 납부내역)
    ↓
Notion Database에 페이지 생성/업데이트
    ↓
테이블 및 구조화된 형식으로 저장
```

## 수집되는 데이터

### 전체 데이터 구조

```json
{
  "timestamp": "2026-01-18T09:00:00.000000",
  "dong_ho": "13061001",
  "maint_items": [...],
  "maint_payment": {...},
  "energy_category": [...],
  "energy_type": [...],
  "payment_history": [...]
}
```

### 상세 데이터

1. **기본 정보**
   - `timestamp`: 데이터 수집 시간 (ISO 형식)
   - `dong_ho`: 동호 정보 (8자리 숫자, 예: "13061001" = 1306동 1001호)

2. **관리비 항목** (`maint_items`)
   - 각 항목별: 항목명, 이번 달 금액, 전월 금액, 증감액
   - 예: 일반관리비, 청소비, 수선유지비 등

3. **관리비 납부액** (`maint_payment`)
   - 납부할 총액, 부과 금액, 부과 월, 납부 마감일, 납부 상태

4. **에너지 카테고리** (`energy_category`)
   - 전기, 가스, 수도, 난방 등
   - 각각: 사용량, 요금, 전월 대비 비교

5. **에너지 종류별 상세** (`energy_type`)
   - 각 에너지 종류별 상세 요금 내역
   - 예: 세대전기료, 기본요금, 전력량요금 등

6. **납부내역** (`payment_history`)
   - 결제일, 금액, 청구월, 마감일, 은행, 결제 방법, 납부 상태

## 설치 및 설정

### 1. 저장소 클론

```bash
git clone https://github.com/kong9365/Apt_i.git
cd Apt_i
```

### 2. Notion Database 생성

1. Notion에서 새 Database 생성 (또는 기존 Database 사용)
2. 다음 속성들을 추가:
   - **Name** (Title): 페이지 제목 (자동 생성)
   - **날짜** (Date): 데이터 수집 날짜
   - **동호** (Text): 동호 정보
   - **월** (Select): 부과 월 (1월~12월)
   - **관리비 총액** (Number): 관리비 총액
   - **부과 금액** (Number): 부과 금액
   - **납부 마감일** (Text): 납부 마감일
   - **납부 상태** (Text): 납부 상태
   - **관리비 항목 수** (Number): 관리비 항목 개수
   - **에너지 카테고리 수** (Number): 에너지 카테고리 개수
   - **납부내역 수** (Number): 납부내역 개수

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

### Database 속성

| 속성명 | 타입 | 설명 |
|--------|------|------|
| Name | Title | 페이지 제목 (날짜 + 동호) |
| 날짜 | Date | 데이터 수집 날짜 |
| 동호 | Text | 아파트 동호수 |
| 월 | Select | 부과 월 (1월~12월) |
| 관리비 총액 | Number | 관리비 총액 (원) |
| 부과 금액 | Number | 부과 금액 (원) |
| 납부 마감일 | Text | 납부 마감일 |
| 납부 상태 | Text | 납부 상태 (납기내, 납기경과 등) |
| 관리비 항목 수 | Number | 관리비 항목 개수 |
| 에너지 카테고리 수 | Number | 에너지 카테고리 개수 |
| 납부내역 수 | Number | 납부내역 개수 |

### 페이지 내용

각 페이지에는 다음 섹션이 테이블 및 구조화된 형식으로 자동 추가됩니다:

1. **📊 기본 정보**: 동호, 수집 시간, 관리비 총액, 부과 금액, 납부 마감일, 납부 상태
2. **💰 관리비 항목**: 항목명, 이번 달, 전월, 증감을 테이블로 표시
3. **⚡ 에너지 카테고리**: 종류, 사용량, 요금, 전월 대비를 테이블로 표시
4. **🔋 에너지 종류별 상세**: 각 에너지 종류별 상세 요금 내역
5. **💳 납부내역**: 결제일, 금액, 청구월, 마감일, 은행, 방법, 상태를 테이블로 표시
6. **📄 원본 데이터 (JSON)**: 전체 원본 데이터를 JSON 형식으로 저장 (디버깅용)

## 월별 뷰 설정

Notion Database에서 월별로 데이터를 보기 좋게 정리하는 방법:

### 방법 1: Database 뷰 생성

1. Database 상단의 "Add a view" 클릭
2. 뷰 이름 입력 (예: "1월", "2월" 등)
3. 필터 추가:
   - Property: **월**
   - Condition: **Is**
   - Value: **1월** (또는 원하는 월)
4. 정렬 추가 (선택사항):
   - Property: **날짜**
   - Direction: **Descending** (최신순)

### 방법 2: 별도 페이지에 Database 연결

1. 별도 페이지 생성 (예: `https://www.notion.so/2026-...`)
2. Database를 해당 페이지에 연결:
   - `/` 입력 후 Database 선택
   - 또는 Database를 드래그하여 페이지에 추가
3. 연결된 Database에 필터 적용:
   - Database 상단 "Filter" 클릭
   - **월** 속성으로 필터링
4. 각 월별로 별도 뷰 생성하여 정리

### 방법 3: 월별 그룹화

1. Database 뷰에서 "Group by" 클릭
2. Property: **월** 선택
3. 각 월별로 그룹화된 뷰 확인

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
