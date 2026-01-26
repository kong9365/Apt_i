"""APT.i 파서 실행 및 결과 저장 스크립트."""

import asyncio
import json
import os
import sys
from datetime import datetime

from apti_parser import APTiParser


async def main():
    """메인 함수."""
    # 환경 변수에서 설정 읽기
    user_id = os.environ.get("APTI_USER_ID")
    password = os.environ.get("APTI_PASSWORD")

    # 필수 환경 변수 확인
    if not user_id or not password:
        print("오류: APTI_USER_ID, APTI_PASSWORD 환경 변수 필요")
        print("예시: set APTI_USER_ID=your_id && set APTI_PASSWORD=your_password")
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

    # 결과를 JSON 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"apti_result_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 파일 저장: {output_file}")
    print(f"파일 크기: {os.path.getsize(output_file)} bytes")
    
    return output_file


if __name__ == "__main__":
    output_file = asyncio.run(main())
    print(f"\n완료! 결과 파일: {output_file}")
