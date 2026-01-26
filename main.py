"""메인 실행 스크립트."""

import asyncio
import os
import sys
from datetime import datetime

from apti_parser import APTiParser
from notion_sender import NotionSender


async def main():
    """메인 함수."""
    # 1. 환경 변수 로드
    user_id = os.environ.get("APTI_USER_ID")
    password = os.environ.get("APTI_PASSWORD")
    notion_token = os.environ.get("NOTION_TOKEN")
    notion_db_id = os.environ.get("NOTION_DATABASE_ID")

    if not all([user_id, password, notion_token, notion_db_id]):
        print("필수 환경 변수가 누락되었습니다.")
        print("필요한 환경 변수: APTI_USER_ID, APTI_PASSWORD, NOTION_TOKEN, NOTION_DATABASE_ID")
        sys.exit(1)

    # 2. 데이터 수집
    print("아파트아이 데이터 수집 시작...")
    parser = APTiParser(user_id, password)
    data = await parser.run()

    if not data:
        print("데이터 수집 실패")
        sys.exit(1)

    # 수집 결과 요약
    maint_payment = data.get("maint_payment", {})
    amount = maint_payment.get("amount", "N/A")
    month_str = maint_payment.get("month", str(datetime.now().month))
    
    print(f"수집 완료: {data.get('dong_ho')} / 청구액 {amount}원")
    print(f"   - 관리비 항목: {len(data.get('maint_items', []))}개")
    print(f"   - 에너지 카테고리: {len(data.get('energy_category', []))}개")
    print(f"   - 납부내역: {len(data.get('payment_history', []))}건")

    # 2.5. 중복 체크
    print("\n중복 데이터 체크 중...")
    sender = NotionSender(notion_token, notion_db_id)
    
    # 연도 추정
    timestamp = data.get("timestamp", datetime.now().isoformat())
    try:
        date_obj = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except:
        date_obj = datetime.now()
    
    current_year = date_obj.year
    if data.get("payment_history"):
        try:
            last_bill = data["payment_history"][0].get("billing_month", "")  # 2025.11
            if last_bill:
                current_year = int(last_bill.split(".")[0])
        except:
            pass
    
    month_int = int(month_str) if month_str.isdigit() else datetime.now().month
    
    if sender.check_month_exists(current_year, month_int):
        print(f"⚠️  {current_year}년 {month_int}월 데이터가 이미 존재합니다. 중복 실행을 건너뜁니다.")
        sys.exit(0)
    
    print(f"✅ 중복 없음. 데이터 수집 및 전송을 진행합니다.")

    # 3. Notion 전송
    print("\nNotion 대시보드 생성 시작...")
    success = sender.update_or_create_page(data)

    if success:
        print("모든 작업이 성공적으로 완료되었습니다!")
        sys.exit(0)
    else:
        print("Notion 전송 실패")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
