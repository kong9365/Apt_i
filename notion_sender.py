"""Notion으로 데이터 전송 모듈."""

import os
from datetime import datetime
from typing import Any

from notion_client import Client


class NotionSender:
    """Notion Database에 데이터를 전송하는 클래스."""

    def __init__(self, token: str, database_id: str) -> None:
        """초기화."""
        self.notion = Client(auth=token)
        self.database_id = database_id

    def format_maint_items(self, items: list[dict]) -> str:
        """관리비 항목을 포맷팅."""
        if not items:
            return "내역 없음"
        
        lines = []
        for item in items:
            item_name = item.get("item", "")
            current = item.get("current", "0")
            previous = item.get("previous", "0")
            change = item.get("change", "0")
            
            try:
                change_int = int(change)
                change_str = f"{change_int:+,}원" if change_int != 0 else "0원"
            except (ValueError, TypeError):
                change_str = change
            
            lines.append(f"• {item_name}: {int(current):,}원 (전월: {int(previous):,}원, 증감: {change_str})")
        
        return "\n".join(lines)

    def format_energy_category(self, energy_list: list[dict]) -> str:
        """에너지 카테고리를 포맷팅."""
        if not energy_list:
            return "내역 없음"
        
        lines = []
        for energy in energy_list:
            energy_type = energy.get("type", "")
            usage = energy.get("usage", "0")
            cost = energy.get("cost", "0")
            comparison = energy.get("comparison", "")
            
            lines.append(f"• {energy_type}: 사용량 {usage}, 요금 {int(cost):,}원 ({comparison})")
        
        return "\n".join(lines)

    def format_payment_history(self, history: list[dict]) -> str:
        """납부내역을 포맷팅."""
        if not history:
            return "내역 없음"
        
        lines = []
        for item in history[:10]:  # 최근 10건만
            date = item.get("date", "")
            amount = item.get("amount", "0")
            status = item.get("status", "")
            method = item.get("method", "")
            
            try:
                amount_int = int(amount)
                lines.append(f"• {date}: {amount_int:,}원 ({method}) - {status}")
            except (ValueError, TypeError):
                lines.append(f"• {date}: {amount} ({method}) - {status}")
        
        return "\n".join(lines)

    def create_page(self, data: dict[str, Any]) -> bool:
        """Notion Database에 페이지 생성."""
        try:
            # 날짜 파싱
            timestamp = data.get("timestamp", datetime.now().isoformat())
            try:
                date_obj = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                date_obj = datetime.now()
            
            # 동호 정보
            dong_ho = data.get("dong_ho", "")
            dong = dong_ho[:4].lstrip("0") if len(dong_ho) >= 4 else ""
            ho = dong_ho[4:].lstrip("0") if len(dong_ho) > 4 else ""
            dong_ho_str = f"{dong}동 {ho}호" if dong and ho else dong_ho

            # 관리비 정보
            maint_payment = data.get("maint_payment", {})
            maint_amount = maint_payment.get("amount", "0")
            maint_deadline = maint_payment.get("deadline", "")
            maint_status = maint_payment.get("status", "")
            maint_month = maint_payment.get("month", "")

            # 페이지 제목 (날짜 + 동호)
            page_title = f"{date_obj.strftime('%Y-%m-%d')} {dong_ho_str}"

            # 페이지 속성 구성
            properties: dict[str, Any] = {
                "날짜": {
                    "date": {
                        "start": date_obj.strftime("%Y-%m-%d")
                    }
                }
            }

            # 동호 (Title 속성이 있다면)
            # Notion Database 스키마에 따라 속성명이 다를 수 있음
            # 여기서는 일반적인 속성명 사용
            if dong_ho_str:
                properties["동호"] = {
                    "rich_text": [{"text": {"content": dong_ho_str}}]
                }

            # 관리비 총액
            try:
                maint_amount_int = int(maint_amount)
                properties["관리비 총액"] = {
                    "number": maint_amount_int
                }
            except (ValueError, TypeError):
                pass

            # 관리비 마감일
            if maint_deadline:
                properties["납부 마감일"] = {
                    "rich_text": [{"text": {"content": maint_deadline}}]
                }

            # 관리비 상태
            if maint_status:
                properties["납부 상태"] = {
                    "rich_text": [{"text": {"content": maint_status}}]
                }

            # 페이지 내용 구성
            children = []

            # 관리비 항목 섹션
            maint_items = data.get("maint_items", [])
            if maint_items:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "관리비 항목"}}]
                    }
                })
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": self.format_maint_items(maint_items)}}]
                    }
                })

            # 에너지 정보 섹션
            energy_category = data.get("energy_category", [])
            if energy_category:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "에너지 정보"}}]
                    }
                })
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": self.format_energy_category(energy_category)}}]
                    }
                })

            # 납부내역 섹션
            payment_history = data.get("payment_history", [])
            if payment_history:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "납부내역"}}]
                    }
                })
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": self.format_payment_history(payment_history)}}]
                    }
                })

            # 페이지 생성
            response = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children if children else None
            )

            print(f"Notion 페이지 생성 성공: {response.get('url', 'N/A')}")
            return True

        except Exception as e:
            print(f"Notion 페이지 생성 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_or_create_page(self, data: dict[str, Any]) -> bool:
        """날짜 기준으로 기존 페이지 업데이트 또는 새로 생성."""
        try:
            # 날짜 파싱
            timestamp = data.get("timestamp", datetime.now().isoformat())
            try:
                date_obj = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                date_obj = datetime.now()
            
            date_str = date_obj.strftime("%Y-%m-%d")

            # 오늘 날짜의 페이지 찾기
            response = self.notion.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "날짜",
                    "date": {
                        "equals": date_str
                    }
                }
            )

            # 기존 페이지가 있으면 업데이트
            if response.get("results"):
                page_id = response["results"][0]["id"]
                print(f"기존 페이지 발견, 업데이트: {page_id}")
                
                # 페이지 속성 업데이트
                properties: dict[str, Any] = {}
                
                dong_ho = data.get("dong_ho", "")
                dong = dong_ho[:4].lstrip("0") if len(dong_ho) >= 4 else ""
                ho = dong_ho[4:].lstrip("0") if len(dong_ho) > 4 else ""
                dong_ho_str = f"{dong}동 {ho}호" if dong and ho else dong_ho

                if dong_ho_str:
                    properties["동호"] = {
                        "rich_text": [{"text": {"content": dong_ho_str}}]
                    }

                maint_payment = data.get("maint_payment", {})
                maint_amount = maint_payment.get("amount", "0")
                try:
                    maint_amount_int = int(maint_amount)
                    properties["관리비 총액"] = {
                        "number": maint_amount_int
                    }
                except (ValueError, TypeError):
                    pass

                maint_deadline = maint_payment.get("deadline", "")
                if maint_deadline:
                    properties["납부 마감일"] = {
                        "rich_text": [{"text": {"content": maint_deadline}}]
                    }

                maint_status = maint_payment.get("status", "")
                if maint_status:
                    properties["납부 상태"] = {
                        "rich_text": [{"text": {"content": maint_status}}]
                    }

                # 페이지 업데이트
                self.notion.pages.update(
                    page_id=page_id,
                    properties=properties
                )

                print("Notion 페이지 업데이트 성공")
                return True
            else:
                # 새 페이지 생성
                return self.create_page(data)

        except Exception as e:
            print(f"Notion 페이지 업데이트/생성 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
