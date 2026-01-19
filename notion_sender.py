"""Notion Dashboard Generator - 아파트 관리비 원장."""

import json
from datetime import datetime
from typing import Any

from notion_client import Client


class NotionSender:
    """Notion Database에 대시보드 형식으로 데이터를 전송하는 클래스."""

    def __init__(self, token: str, database_id: str) -> None:
        """초기화."""
        self.notion = Client(auth=token)
        self.database_id = database_id

    def format_currency(self, amount: str | int) -> str:
        """금액 포맷팅 (콤마 추가)."""
        try:
            if isinstance(amount, str):
                amount = int(amount)
            return f"{amount:,}"
        except (ValueError, TypeError):
            return "0"

    def parse_date(self, date_str: str) -> str | None:
        """날짜 문자열을 Notion Date 형식으로 변환."""
        if not date_str:
            return None
        try:
            # 다양한 날짜 형식 처리
            if "." in date_str:
                # "2026.01.25" 형식
                date_str = date_str.replace(".", "-")
            elif "/" in date_str:
                # "2026/01/25" 형식
                date_str = date_str.replace("/", "-")
            
            # ISO 형식으로 변환 시도
            if "T" in date_str:
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            return date_obj.strftime("%Y-%m-%d")
        except:
            return None

    def get_payment_status(self, status: str) -> dict[str, Any]:
        """납부 상태를 Notion Status 형식으로 변환."""
        status_lower = status.lower() if status else ""
        
        if "완납" in status_lower or "완료" in status_lower:
            return {"name": "완납"}
        elif "미납" in status_lower or "미결제" in status_lower:
            return {"name": "미납"}
        else:
            return {"name": "납기내"}

    def extract_energy_costs(self, energy_category: list[dict]) -> dict[str, int]:
        """에너지 카테고리에서 전기/수도/난방 요금 추출."""
        costs = {"전기": 0, "수도": 0, "난방": 0, "가스": 0}
        
        for energy in energy_category:
            energy_type = energy.get("type", "")
            cost_str = energy.get("cost", "0")
            
            try:
                cost = int(cost_str)
            except (ValueError, TypeError):
                cost = 0
            
            if "전기" in energy_type:
                costs["전기"] = cost
            elif "수도" in energy_type:
                costs["수도"] = cost
            elif "난방" in energy_type or "열" in energy_type:
                costs["난방"] = cost
            elif "가스" in energy_type:
                costs["가스"] = cost
        
        return costs

    def create_dashboard_page(self, data: dict[str, Any]) -> bool:
        """대시보드 형식의 Notion 페이지 생성."""
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

            # 페이지 제목 (YYYY년 M월 관리비)
            year = date_obj.year
            month_str = f"{int(maint_month)}월" if maint_month else date_obj.strftime("%-m월")
            page_title = f"{year}년 {month_str} 관리비"

            # 에너지 요금 추출
            energy_category = data.get("energy_category", [])
            energy_costs = self.extract_energy_costs(energy_category)

            # 페이지 속성 구성
            properties: dict[str, Any] = {
                "이름": {
                    "title": [{"text": {"content": page_title}}]
                },
                "date:수집일시:start": date_obj.strftime("%Y-%m-%d"),
                "date:수집일시:is_datetime": 1
            }

            # 청구월
            if maint_month:
                try:
                    month_num = int(maint_month)
                    if 1 <= month_num <= 12:
                        properties["청구월"] = {
                            "select": {"name": f"{month_num}월"}
                        }
                except (ValueError, TypeError):
                    pass

            # 총 납부액
            try:
                maint_amount_int = int(maint_amount)
                properties["총 납부액"] = {
                    "number": maint_amount_int
                }
            except (ValueError, TypeError):
                pass

            # 납부기한
            deadline_date = self.parse_date(maint_deadline)
            if deadline_date:
                properties["date:납부기한:start"] = deadline_date
                properties["date:납부기한:is_datetime"] = 0

            # 납부상태
            properties["납부상태"] = self.get_payment_status(maint_status)

            # 에너지 요금
            if energy_costs["전기"] > 0:
                properties["⚡ 전기요금"] = {"number": energy_costs["전기"]}
            if energy_costs["수도"] > 0:
                properties["💧 수도요금"] = {"number": energy_costs["수도"]}
            if energy_costs["난방"] > 0 or energy_costs["가스"] > 0:
                properties["🔥 난방/가스"] = {"number": energy_costs["난방"] + energy_costs["가스"]}

            # 동호수
            if dong_ho_str:
                properties["동호수"] = {
                    "rich_text": [{"text": {"content": dong_ho_str}}]
                }

            # 페이지 내용 구성
            children = []

            # 1. Header Section (Callout Block)
            callout_text = f"이번 달 관리비: **{self.format_currency(maint_amount)}원**\n"
            callout_text += f"납부 마감일은 **{maint_deadline}**까지 입니다. (상태: {maint_status})"
            
            children.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": callout_text},
                            "annotations": {
                                "bold": False
                            }
                        }
                    ],
                    "icon": {"emoji": "💡"},
                    "color": "gray_background"
                }
            })

            # 2. Main Body (Column List Block)
            column_list_children = []

            # Left Column: Management Fee Details
            left_column_blocks = []
            
            # Heading
            left_column_blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"text": {"content": "📋 관리비 세부 내역"}}]
                }
            })

            # Table
            maint_items = data.get("maint_items", [])
            table_rows = [
                {
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": "항목"}}],
                            [{"type": "text", "text": {"content": "당월 금액"}}],
                            [{"type": "text", "text": {"content": "전월 금액"}}],
                            [{"type": "text", "text": {"content": "증감"}}]
                        ]
                    }
                }
            ]

            total_current = 0
            total_previous = 0

            for item in maint_items:
                item_name = item.get("item", "")
                current = item.get("current", "0")
                previous = item.get("previous", "0")
                change = item.get("change", "0")

                try:
                    current_int = int(current)
                    previous_int = int(previous)
                    change_int = int(change)
                    total_current += current_int
                    total_previous += previous_int
                except (ValueError, TypeError):
                    current_int = 0
                    previous_int = 0
                    change_int = 0

                # 증감 스타일링
                if change_int > 0:
                    change_text = f"🔺 {self.format_currency(change_int)}"
                    change_annotations = {"color": "red"}
                elif change_int < 0:
                    change_text = f"▼ {self.format_currency(abs(change_int))}"
                    change_annotations = {"color": "blue"}
                else:
                    change_text = "-"
                    change_annotations = {}

                table_rows.append({
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": item_name}}],
                            [{"type": "text", "text": {"content": f"{self.format_currency(current_int)}원"}}],
                            [{"type": "text", "text": {"content": f"{self.format_currency(previous_int)}원"}}],
                            [{"type": "text", "text": {"content": change_text}, "annotations": change_annotations}]
                        ]
                    }
                })

            # Footer Row (Summary)
            table_rows.append({
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": [
                        [{"type": "text", "text": {"content": "**합계**", "annotations": {"bold": True}}}],
                        [{"type": "text", "text": {"content": f"**{self.format_currency(total_current)}원**", "annotations": {"bold": True}}}],
                        [{"type": "text", "text": {"content": f"**{self.format_currency(total_previous)}원**", "annotations": {"bold": True}}}],
                        [{"type": "text", "text": {"content": f"**{self.format_currency(total_current - total_previous)}원**", "annotations": {"bold": True}}}]
                    ]
                }
            })

            left_column_blocks.append({
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": 4,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": table_rows
                }
            })

            # Right Column: Energy Analysis
            right_column_blocks = []

            # Heading
            right_column_blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"text": {"content": "📊 에너지 사용량 분석"}}]
                }
            })

            # Energy Category Content
            for energy in energy_category:
                energy_type = energy.get("type", "")
                usage = energy.get("usage", "0")
                cost = energy.get("cost", "0")
                comparison = energy.get("comparison", "")

                # Energy Type (Bold)
                right_column_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": energy_type},
                                "annotations": {"bold": True}
                            }
                        ]
                    }
                })

                # Bulleted List
                bullet_items = [
                    f"사용량: {usage}",
                    f"청구액: {self.format_currency(cost)}원"
                ]

                # 전월대비 색상 적용
                if comparison:
                    if "+" in comparison or comparison.startswith(("증가", "상승")):
                        comparison_color = "red"
                    elif "-" in comparison or comparison.startswith(("감소", "하락")):
                        comparison_color = "blue"
                    else:
                        comparison_color = "default"
                    
                    bullet_items.append({
                        "text": f"전월대비: {comparison}",
                        "color": comparison_color
                    })
                else:
                    bullet_items.append(f"전월대비: -")

                for item in bullet_items:
                    if isinstance(item, dict):
                        right_column_blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {"content": item["text"]},
                                        "annotations": {"color": item["color"]}
                                    }
                                ]
                            }
                        })
                    else:
                        right_column_blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [{"type": "text", "text": {"content": item}}]
                            }
                        })

                # Spacing
                right_column_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": ""}}]
                    }
                })

            # Create Column List
            column_list_children.append({
                "object": "block",
                "type": "column",
                "column": {
                    "children": left_column_blocks
                }
            })

            column_list_children.append({
                "object": "block",
                "type": "column",
                "column": {
                    "children": right_column_blocks
                }
            })

            children.append({
                "object": "block",
                "type": "column_list",
                "column_list": {
                    "children": column_list_children
                }
            })

            # 3. Footer Details (Toggle Blocks)

            # Toggle 1: 에너지 상세 요금 내역
            energy_type = data.get("energy_type", [])
            if energy_type:
                energy_toggle_children = []
                
                for energy in energy_type:
                    energy_type_name = energy.get("type", "")
                    total = energy.get("total", "0")
                    comparison = energy.get("comparison", "")
                    
                    try:
                        total_int = int(total)
                    except (ValueError, TypeError):
                        total_int = 0
                    
                    # Energy Type Heading
                    energy_toggle_children.append({
                        "object": "block",
                        "type": "heading_4",
                        "heading_4": {
                            "rich_text": [{"text": {"content": f"{energy_type_name} (총 {self.format_currency(total_int)}원, {comparison})"}}]
                        }
                    })
                    
                    # Sub-fields as bulleted list
                    detail_items = []
                    for key, value in energy.items():
                        if key not in ["type", "total", "comparison"]:
                            try:
                                value_int = int(value)
                                detail_items.append(f"• {key}: {self.format_currency(value_int)}원")
                            except (ValueError, TypeError):
                                detail_items.append(f"• {key}: {value}")
                    
                    if detail_items:
                        for item in detail_items:
                            energy_toggle_children.append({
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"type": "text", "text": {"content": item}}]
                                }
                            })
                    
                    energy_toggle_children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": ""}}]
                        }
                    })
                
                children.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [{"type": "text", "text": {"content": "▶️ 에너지 상세 요금 내역"}}],
                        "children": energy_toggle_children
                    }
                })

            # Toggle 2: 납부 처리 이력
            payment_history = data.get("payment_history", [])
            if payment_history:
                payment_toggle_children = []
                
                for payment in payment_history:
                    date = payment.get("date", "")
                    amount = payment.get("amount", "0")
                    bank = payment.get("bank", "")
                    method = payment.get("method", "")
                    status = payment.get("status", "")
                    
                    try:
                        amount_int = int(amount)
                    except (ValueError, TypeError):
                        amount_int = 0
                    
                    payment_text = f"{date} | {self.format_currency(amount_int)}원 | {bank} ({method}) | {status}"
                    
                    payment_toggle_children.append({
                        "object": "block",
                        "type": "to_do",
                        "to_do": {
                            "rich_text": [{"type": "text", "text": {"content": payment_text}}],
                            "checked": status in ["완납", "완료", "결제완료"]
                        }
                    })
                
                children.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [{"type": "text", "text": {"content": "▶️ 납부 처리 이력"}}],
                        "children": payment_toggle_children
                    }
                })

            # 페이지 생성
            response = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children if children else None
            )

            print(f"Notion 대시보드 페이지 생성 성공: {response.get('url', 'N/A')}")
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
            
            maint_payment = data.get("maint_payment", {})
            maint_month = maint_payment.get("month", "")
            
            # 해당 월의 페이지 찾기
            if maint_month:
                try:
                    month_num = int(maint_month)
                    month_str = f"{month_num}월"
                except:
                    month_str = None
            else:
                month_str = None

            # Database 쿼리로 해당 월의 페이지 찾기
            filter_conditions = []
            
            if month_str:
                filter_conditions.append({
                    "property": "청구월",
                    "select": {
                        "equals": month_str
                    }
                })
            else:
                filter_conditions.append({
                    "property": "수집일시",
                    "date": {
                        "equals": date_obj.strftime("%Y-%m-%d")
                    }
                })

            response = self.notion.databases.query(
                database_id=self.database_id,
                filter={
                    "and": filter_conditions
                } if len(filter_conditions) > 1 else filter_conditions[0]
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
            
            # 새 페이지 생성
            return self.create_dashboard_page(data)

        except Exception as e:
            print(f"Notion 페이지 업데이트/생성 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
