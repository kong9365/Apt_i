"""메인 실행 스크립트."""

import asyncio
import os
import sys

from apti_parser import APTiParser
from notion_sender import NotionSender


async def main():
    """메인 함수."""
    # 1. 환경 변수 로드
    user_id = os.environ.get("APTI_USER_ID")
    password = os.environ.get("APTI_PASSWORD")
    notion_token = os.environ.get("NOTION_TOKEN")
    notion_db_id = os.environ.get("NOTION_DATABASE_ID")
    notion_parent_page_id = os.environ.get("NOTION_PARENT_PAGE_ID")  # 대시보드 페이지 부모 (선택)
    create_dashboard = os.environ.get("CREATE_DASHBOARD", "false").lower() == "true"  # 대시보드 생성 여부

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
    print(f"수집 완료: {data.get('dong_ho')} / 청구액 {amount}원")
    print(f"   - 관리비 항목: {len(data.get('maint_items', []))}개")
    print(f"   - 에너지 카테고리: {len(data.get('energy_category', []))}개")
    print(f"   - 납부내역: {len(data.get('payment_history', []))}건")

    # 3. Notion 전송
    print("\nNotion 대시보드 생성 시작...")
    sender = NotionSender(notion_token, notion_db_id, parent_page_id=notion_parent_page_id)
    success = sender.update_or_create_page(data)

    if not success:
        print("Notion 전송 실패")
        sys.exit(1)
    
    # 4. 차트 대시보드 페이지 생성 (옵션)
    if create_dashboard and notion_parent_page_id:
        print("\n차트 대시보드 페이지 생성 시작...")
        dashboard_success = sender.create_chart_dashboard_page()
        if dashboard_success:
            print("차트 대시보드 페이지 생성 완료!")
        else:
            print("차트 대시보드 페이지 생성 실패 (계속 진행)")

    print("모든 작업이 성공적으로 완료되었습니다!")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
