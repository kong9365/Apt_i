"""APT.i 데이터 수집 및 Notion 전송 메인 스크립트."""

import asyncio
import os
import sys

from apti_parser import APTiParser
from notion_sender import NotionSender


async def main():
    """메인 함수."""
    # 환경 변수에서 설정 읽기
    user_id = os.environ.get("APTI_USER_ID")
    password = os.environ.get("APTI_PASSWORD")
    notion_token = os.environ.get("NOTION_TOKEN")
    notion_database_id = os.environ.get("NOTION_DATABASE_ID")

    # 필수 환경 변수 확인
    if not user_id or not password:
        print("오류: APTI_USER_ID, APTI_PASSWORD 환경 변수 필요")
        sys.exit(1)

    if not notion_token:
        print("오류: NOTION_TOKEN 환경 변수 필요")
        sys.exit(1)

    if not notion_database_id:
        print("오류: NOTION_DATABASE_ID 환경 변수 필요")
        sys.exit(1)

    # APT.i 데이터 파싱
    print("=== APT.i 데이터 수집 시작 ===")
    parser = APTiParser(user_id, password)
    data = await parser.run()

    if not data:
        print("파싱 실패!")
        sys.exit(1)

    print(f"\n=== 파싱 결과 ===")
    print(f"동호: {data['dong_ho']}")
    print(f"관리비 항목: {len(data['maint_items'])}개")
    print(f"납부액: {data['maint_payment'].get('amount', 'N/A')}원")
    print(f"에너지: {len(data['energy_category'])}개")
    print(f"납부내역: {len(data['payment_history'])}건")

    # Notion으로 전송
    print(f"\n=== Notion 전송 시작 ===")
    sender = NotionSender(notion_token, notion_database_id)
    success = sender.update_or_create_page(data)

    if success:
        print("\nNotion 전송 성공!")
        sys.exit(0)
    else:
        print("\nNotion 전송 실패!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
