"""Notion으로 데이터 전송 모듈."""

import json
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

    def format_maint_items_table(self, items: list[dict]) -> list[dict]:
        """관리비 항목을 테이블 형식으로 포맷팅."""
        if not items:
            return []
        
        rows = []
        for item in items:
            item_name = item.get("item", "")
            current = item.get("current", "0")
            previous = item.get("previous", "0")
            change = item.get("change", "0")
            
            try:
                current_int = int(current)
                previous_int = int(previous)
                change_int = int(change)
            except (ValueError, TypeError):
                current_int = 0
                previous_int = 0
                change_int = 0
            
            rows.append({
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": [
                        [{"type": "text", "text": {"content": item_name}}],
                        [{"type": "text", "text": {"content": f"{current_int:,}원"}}],
                        [{"type": "text", "text": {"content": f"{previous_int:,}원"}}],
                        [{"type": "text", "text": {"content": f"{change_int:+,}원"}}]
                    ]
                }
            })
        
        return rows

    def format_energy_category_table(self, energy_list: list[dict]) -> list[dict]:
        """에너지 카테고리를 테이블 형식으로 포맷팅."""
        if not energy_list:
            return []
        
        rows = []
        for energy in energy_list:
            energy_type = energy.get("type", "")
            usage = energy.get("usage", "0")
            cost = energy.get("cost", "0")
            comparison = energy.get("comparison", "")
            
            try:
                cost_int = int(cost)
            except (ValueError, TypeError):
                cost_int = 0
            
            rows.append({
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": [
                        [{"type": "text", "text": {"content": energy_type}}],
                        [{"type": "text", "text": {"content": usage}}],
                        [{"type": "text", "text": {"content": f"{cost_int:,}원"}}],
                        [{"type": "text", "text": {"content": comparison}}]
                    ]
                }
            })
        
        return rows

    def format_energy_type_details(self, energy_type_list: list[dict]) -> list[dict]:
        """에너지 종류별 상세 정보를 포맷팅."""
        if not energy_type_list:
            return []
        
        blocks = []
        for energy in energy_type_list:
            energy_type = energy.get("type", "")
            total = energy.get("total", "0")
            comparison = energy.get("comparison", "")
            
            try:
                total_int = int(total)
            except (ValueError, TypeError):
                total_int = 0
            
            # 에너지 종류 제목
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"text": {"content": f"{energy_type} (총 {total_int:,}원, {comparison})"}}]
                }
            })
            
            # 상세 항목들
            detail_items = []
            for key, value in energy.items():
                if key not in ["type", "total", "comparison"]:
                    try:
                        value_int = int(value)
                        detail_items.append(f"• {key}: {value_int:,}원")
                    except (ValueError, TypeError):
                        detail_items.append(f"• {key}: {value}")
            
            if detail_items:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "\n".join(detail_items)}}]
                    }
                })
        
        return blocks

    def format_payment_history_table(self, history: list[dict]) -> list[dict]:
        """납부내역을 테이블 형식으로 포맷팅."""
        if not history:
            return []
        
        rows = []
        for item in history:
            date = item.get("date", "")
            amount = item.get("amount", "0")
            billing_month = item.get("billing_month", "")
            deadline = item.get("deadline", "")
            bank = item.get("bank", "")
            method = item.get("method", "")
            status = item.get("status", "")
            
            try:
                amount_int = int(amount)
            except (ValueError, TypeError):
                amount_int = 0
            
            rows.append({
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": [
                        [{"type": "text", "text": {"content": date}}],
                        [{"type": "text", "text": {"content": f"{amount_int:,}원"}}],
                        [{"type": "text", "text": {"content": billing_month}}],
                        [{"type": "text", "text": {"content": deadline}}],
                        [{"type": "text", "text": {"content": bank}}],
                        [{"type": "text", "text": {"content": method}}],
                        [{"type": "text", "text": {"content": status}}]
                    ]
                }
            })
        
        return rows

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
            maint_charged = maint_payment.get("charged", "0")
            maint_deadline = maint_payment.get("deadline", "")
            maint_status = maint_payment.get("status", "")
            maint_month = maint_payment.get("month", "")

            # 페이지 제목 (날짜 + 동호)
            page_title = f"{date_obj.strftime('%Y-%m-%d')} {dong_ho_str}"

            # 페이지 속성 구성
            properties: dict[str, Any] = {
                "Name": {
                    "title": [{"text": {"content": page_title}}]
                },
                "date:날짜:start": date_obj.strftime("%Y-%m-%d"),
                "date:날짜:is_datetime": 0
            }

            # 동호
            if dong_ho_str:
                properties["동호"] = {
                    "rich_text": [{"text": {"content": dong_ho_str}}]
                }

            # 월
            if maint_month:
                try:
                    month_num = int(maint_month)
                    if 1 <= month_num <= 12:
                        properties["월"] = {
                            "select": {"name": f"{month_num}월"}
                        }
                except (ValueError, TypeError):
                    pass

            # 관리비 총액
            try:
                maint_amount_int = int(maint_amount)
                properties["관리비 총액"] = {
                    "number": maint_amount_int
                }
            except (ValueError, TypeError):
                pass

            # 부과 금액
            try:
                maint_charged_int = int(maint_charged)
                properties["부과 금액"] = {
                    "number": maint_charged_int
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

            # 통계 정보
            maint_items = data.get("maint_items", [])
            energy_category = data.get("energy_category", [])
            payment_history = data.get("payment_history", [])
            
            properties["관리비 항목 수"] = {"number": len(maint_items)}
            properties["에너지 카테고리 수"] = {"number": len(energy_category)}
            properties["납부내역 수"] = {"number": len(payment_history)}

            # 페이지 내용 구성
            children = []

            # 기본 정보 섹션
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": "📊 기본 정보"}}]
                }
            })
            
            info_text = f"• 동호: {dong_ho_str}\n"
            info_text += f"• 수집 시간: {date_obj.strftime('%Y-%m-%d %H:%M:%S')}\n"
            info_text += f"• 관리비 총액: {int(maint_amount):,}원\n"
            if maint_charged:
                info_text += f"• 부과 금액: {int(maint_charged):,}원\n"
            if maint_deadline:
                info_text += f"• 납부 마감일: {maint_deadline}\n"
            if maint_status:
                info_text += f"• 납부 상태: {maint_status}"
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": info_text}}]
                }
            })

            # 관리비 항목 섹션
            if maint_items:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "💰 관리비 항목"}}]
                    }
                })
                
                # 테이블 헤더
                table_rows = [{
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": "항목명"}}],
                            [{"type": "text", "text": {"content": "이번 달"}}],
                            [{"type": "text", "text": {"content": "전월"}}],
                            [{"type": "text", "text": {"content": "증감"}}]
                        ]
                    }
                }]
                table_rows.extend(self.format_maint_items_table(maint_items))
                
                children.append({
                    "object": "block",
                    "type": "table",
                    "table": {
                        "table_width": 4,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": table_rows
                    }
                })

            # 에너지 카테고리 섹션
            if energy_category:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "⚡ 에너지 카테고리"}}]
                    }
                })
                
                # 테이블 헤더
                table_rows = [{
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": "종류"}}],
                            [{"type": "text", "text": {"content": "사용량"}}],
                            [{"type": "text", "text": {"content": "요금"}}],
                            [{"type": "text", "text": {"content": "전월 대비"}}]
                        ]
                    }
                }]
                table_rows.extend(self.format_energy_category_table(energy_category))
                
                children.append({
                    "object": "block",
                    "type": "table",
                    "table": {
                        "table_width": 4,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": table_rows
                    }
                })

            # 에너지 종류별 상세 섹션
            energy_type = data.get("energy_type", [])
            if energy_type:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🔋 에너지 종류별 상세"}}]
                    }
                })
                children.extend(self.format_energy_type_details(energy_type))

            # 납부내역 섹션
            if payment_history:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "💳 납부내역"}}]
                    }
                })
                
                # 테이블 헤더
                table_rows = [{
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": "결제일"}}],
                            [{"type": "text", "text": {"content": "금액"}}],
                            [{"type": "text", "text": {"content": "청구월"}}],
                            [{"type": "text", "text": {"content": "마감일"}}],
                            [{"type": "text", "text": {"content": "은행"}}],
                            [{"type": "text", "text": {"content": "방법"}}],
                            [{"type": "text", "text": {"content": "상태"}}]
                        ]
                    }
                }]
                table_rows.extend(self.format_payment_history_table(payment_history))
                
                children.append({
                    "object": "block",
                    "type": "table",
                    "table": {
                        "table_width": 7,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": table_rows
                    }
                })

            # 원본 데이터 (JSON 형식으로 저장 - 디버깅용)
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": "📄 원본 데이터 (JSON)"}}]
                }
            })
            children.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"text": {"content": json.dumps(data, ensure_ascii=False, indent=2)}}],
                    "language": "json"
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

            # 해당 날짜의 페이지 찾기
            response = self.notion.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "날짜",
                    "date": {
                        "equals": date_str
                    }
                }
            )

            # 기존 페이지가 있으면 삭제 후 재생성 (내용이 복잡하므로)
            if response.get("results"):
                page_id = response["results"][0]["id"]
                print(f"기존 페이지 발견, 삭제 후 재생성: {page_id}")
                try:
                    self.notion.pages.update(
                        page_id=page_id,
                        archived=True
                    )
                except:
                    pass
            
            # 새 페이지 생성 (항상 최신 데이터로)
            return self.create_page(data)

        except Exception as e:
            print(f"Notion 페이지 업데이트/생성 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
