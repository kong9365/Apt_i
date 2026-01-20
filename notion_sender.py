"""Notion Dashboard Generator - 아파트 관리비 원장 (Design Optimized)."""

import json
from datetime import datetime
from typing import Any

from notion_client import Client


class NotionSender:
    """Notion Database에 디자인된 대시보드 형식으로 데이터를 전송하는 클래스."""

    def __init__(self, token: str, database_id: str) -> None:
        """초기화."""
        import httpx
        # SSL 인증서 검증 우회 (회사 네트워크 환경 대응)
        client = httpx.Client(verify=False)
        self.notion = Client(auth=token, client=client)
        self.database_id = database_id

    def format_currency(self, amount: str | int) -> str:
        """금액 포맷팅 (콤마 추가)."""
        try:
            if isinstance(amount, str):
                amount = int(amount.replace(",", ""))
            return f"{amount:,}"
        except (ValueError, TypeError):
            return "0"

    def parse_int(self, value: Any) -> int:
        """안전한 정수 변환."""
        try:
            if isinstance(value, str):
                return int(value.replace(",", "").replace("원", ""))
            return int(value)
        except (ValueError, TypeError):
            return 0

    def parse_date(self, date_str: str) -> str | None:
        """날짜 문자열을 Notion Date 형식으로 변환."""
        if not date_str:
            return None
        try:
            if "." in date_str:
                date_str = date_str.replace(".", "-")
            elif "/" in date_str:
                date_str = date_str.replace("/", "-")
            
            # YYYY년 MM월 DD일 형식 처리
            if "년" in date_str and "월" in date_str:
                date_str = date_str.replace("년", "-").replace("월", "-").replace("일", "").replace(" ", "")
                # 2025-12-31 형식이 되도록 정리
            
            if "T" in date_str:
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                date_obj = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            
            return date_obj.strftime("%Y-%m-%d")
        except:
            return None

    def extract_energy_costs(self, energy_category: list[dict]) -> dict[str, int]:
        """에너지 카테고리에서 전기/수도/가스/난방 요금 추출."""
        costs = {"전기": 0, "수도": 0, "난방": 0, "가스": 0}
        
        for energy in energy_category:
            energy_type = energy.get("type", "")
            cost_str = energy.get("cost", "0")
            cost = self.parse_int(cost_str)
            
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
            # --- 1. 데이터 전처리 ---
            maint_payment = data.get("maint_payment", {})
            maint_items = data.get("maint_items", [])
            payment_history = data.get("payment_history", [])
            energy_category = data.get("energy_category", [])
            
            dong_ho = data.get("dong_ho", "")
            dong = dong_ho[:4].lstrip("0") if len(dong_ho) >= 4 else ""
            ho = dong_ho[4:].lstrip("0") if len(dong_ho) > 4 else ""
            dong_ho_str = f"{dong}동 {ho}호" if dong and ho else dong_ho
            
            amount = self.parse_int(maint_payment.get("amount", 0))
            month_str = maint_payment.get("month", str(datetime.now().month))
            deadline_str = maint_payment.get("deadline", "")
            maint_status = maint_payment.get("status", "")
            
            # 연도 추정 (납부 이력 기반)
            timestamp = data.get("timestamp", datetime.now().isoformat())
            try:
                date_obj = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                date_obj = datetime.now()
            
            current_year = date_obj.year
            if payment_history:
                try:
                    last_bill = payment_history[0].get("billing_month", "")  # 2025.11
                    if last_bill:
                        current_year = int(last_bill.split(".")[0])
                except:
                    pass
            
            page_title = f"{current_year}년 {month_str}월 관리비"
            
            # 납부 상태 판단
            status_val = "미납"
            status_color = "red"
            
            # 이번 달 청구월이 납부 이력에 있고 '완료' 상태인지 확인
            target_billing_month = f"{current_year}.{month_str.zfill(2)}"
            is_paid = any(
                h.get("billing_month") == target_billing_month and "완료" in h.get("status", "") 
                for h in payment_history
            )
            
            if is_paid:
                status_val = "납부완료"
                status_color = "green"
            elif "납기후" in maint_status:
                status_val = "미납 (연체)"
            elif maint_status and "납기내" in maint_status:
                status_val = "납기내"
                status_color = "yellow"
            
            # 에너지 요금 추출
            energy_costs = self.extract_energy_costs(energy_category)
            
            # --- 2. 페이지 속성 (Properties) 설정 ---
            # 실제 데이터베이스 속성에 맞춰 설정
            # 속성 순서: Name -> 청구월 -> 동호수 -> 총 납부액 -> 난방 -> 수도 -> 전기 -> 납부기한 -> 수집일시
            properties = {
                "Name": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": page_title}
                        }
                    ]
                }
            }
            
            # 청구월 (number 타입)
            try:
                month_num_int = int(month_str)
                if 1 <= month_num_int <= 12:
                    properties["청구월"] = {
                        "number": month_num_int
                    }
            except (ValueError, TypeError):
                pass
            
            # 동호수
            if dong_ho_str:
                properties["동호수"] = {
                    "rich_text": [{"type": "text", "text": {"content": dong_ho_str}}]
                }
            
            # 총 납부액
            properties["총 납부액"] = {"number": amount}
            
            # 에너지 요금 (난방 -> 수도 -> 전기 순서)
            if energy_costs["난방"] > 0 or energy_costs["가스"] > 0:
                properties["🔥 난방/가스"] = {"number": energy_costs["난방"] + energy_costs["가스"]}
            if energy_costs["수도"] > 0:
                properties["💧 수도요금"] = {"number": energy_costs["수도"]}
            if energy_costs["전기"] > 0:
                properties["⚡ 전기요금"] = {"number": energy_costs["전기"]}
            
            # 납부기한
            deadline_date = self.parse_date(deadline_str)
            if deadline_date:
                properties["납부기한"] = {
                    "date": {
                        "start": deadline_date
                    }
                }
            
            # 수집일시
            properties["수집일시"] = {
                "date": {
                    "start": date_obj.strftime("%Y-%m-%dT%H:%M:%S")
                }
            }

            # --- 3. 페이지 본문 (Block) 구성 ---
            children = []

            # 3.1 Header Area (Callout Block)
            # 최근 6개월 추이 텍스트 생성
            trend_texts = []
            recent_history = payment_history[:6]  # 최신순
            # 역순으로 정렬 (오래된 -> 최신)하여 표시
            for h in reversed(recent_history):
                billing_month = h.get("billing_month", "")
                if "." in billing_month:
                    m = billing_month.split(".")[-1]
                else:
                    m = ""
                amt = self.parse_int(h.get("amount", 0)) // 10000  # 만원 단위
                if m:
                    trend_texts.append(f"{int(m)}월: {amt}만")
            trend_str = " | ".join(trend_texts) if trend_texts else "데이터 없음"

            header_callout = {
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"emoji": "🏠"},
                    "color": "gray_background",
                    "rich_text": [
                        # Line 1: Dong/Ho + Title
                        {
                            "type": "text",
                            "text": {"content": f"{dong_ho_str} | {month_str}월분 관리비 명세서\n"},
                            "annotations": {"bold": True}
                        },
                        # Line 2: Amount
                        {
                            "type": "text",
                            "text": {"content": f"이번 달 청구액: "},
                        },
                        {
                            "type": "text",
                            "text": {"content": f"{self.format_currency(amount)}원"},
                            "annotations": {"bold": True, "code": True}
                        }
                    ]
                }
            }
            
            # 미납 시 납기일 표시 추가
            if status_val != "납부완료":
                header_callout["callout"]["rich_text"].append({
                    "type": "text",
                    "text": {"content": f" (납기일: {deadline_str})"},
                    "annotations": {"color": "red"}
                })
            
            # Line 3: Trend
            header_callout["callout"]["rich_text"].append({
                "type": "text",
                "text": {"content": f"\n📅 최근 6개월 추이: {trend_str}"},
                "annotations": {"color": "gray"}
            })

            children.append(header_callout)

            # 3.2 Energy & Comparison (2-Column Layout) - 맨 위로 이동
            # Column 1: Usage & Cost
            col1_children = [
                {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": "⚡ 에너지 및 주요 지출"}}]}}
            ]
            
            for energy in energy_category:
                e_type = energy.get("type", "")
                usage = energy.get("usage", "0")
                cost = energy.get("cost", "0")
                cost_int = self.parse_int(cost)
                
                col1_children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"{e_type}: {usage}"}}
                        ],
                        "children": [
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {"type": "text", "text": {"content": f"비용: {self.format_currency(cost_int)}원"}}
                                    ]
                                }
                            }
                        ]
                    }
                })

            # Column 2: Neighbor Comparison
            col2_children = [
                {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": "📊 이웃 평균 비교"}}]}}
            ]
            
            for energy in energy_category:
                comp_text = energy.get("comparison", "")
                if comp_text:
                    col2_children.append({
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "icon": {"emoji": "💬"},
                            "color": "blue_background",
                            "rich_text": [{"type": "text", "text": {"content": comp_text}}]
                        }
                    })

            children.append({
                "object": "block",
                "type": "column_list",
                "column_list": {
                    "children": [
                        {"object": "block", "type": "column", "column": {"children": col1_children}},
                        {"object": "block", "type": "column", "column": {"children": col2_children}}
                    ]
                }
            })

            children.append({"object": "block", "type": "divider", "divider": {}})

            # 3.3 Detailed Fee Table (Toggle Block) - 중앙에 위치, 가로 2열 레이아웃
            # 항목 정렬: 당월 금액 기준 내림차순
            sorted_items = sorted(
                maint_items, 
                key=lambda x: self.parse_int(x.get("current", 0)), 
                reverse=True
            )

            # 가로 2열로 항목 분할
            left_column_items = []
            right_column_items = []
            
            for i, item in enumerate(sorted_items):
                name = item.get("item", "")
                curr = self.parse_int(item.get("current", 0))
                change = self.parse_int(item.get("change", 0))
                
                # Trend Display Logic
                if change > 0:
                    trend_text = f"🔺 +{self.format_currency(change)}원"
                    trend_color = "red"
                elif change < 0:
                    trend_text = f"🔽 {self.format_currency(change)}원"
                    trend_color = "blue"
                else:
                    trend_text = "-"
                    trend_color = "gray"
                
                # 항목 정보를 Callout 형식으로 구성
                item_block = {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "icon": {"emoji": "💰"},
                        "color": "gray_background",
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": f"{name}\n"},
                                "annotations": {"bold": True}
                            },
                            {
                                "type": "text",
                                "text": {"content": f"당월: {self.format_currency(curr)}원\n"}
                            },
                            {
                                "type": "text",
                                "text": {"content": f"증감: "}
                            },
                            {
                                "type": "text",
                                "text": {"content": trend_text},
                                "annotations": {"color": trend_color}
                            }
                        ]
                    }
                }
                
                # 짝수 인덱스는 왼쪽, 홀수 인덱스는 오른쪽
                if i % 2 == 0:
                    left_column_items.append(item_block)
                else:
                    right_column_items.append(item_block)
            
            # 2-컬럼 레이아웃 생성
            detail_col1 = left_column_items
            detail_col2 = right_column_items
            
            # 토글 내부에 직접 callout 블록들을 나열
            # Notion API가 toggle 내부의 column_list를 지원하지 않으므로
            # 모든 항목을 순서대로 나열 (왼쪽 컬럼 먼저, 그 다음 오른쪽 컬럼)
            toggle_children = []
            max_len = max(len(detail_col1), len(detail_col2))
            for i in range(max_len):
                if i < len(detail_col1):
                    toggle_children.append(detail_col1[i])
                if i < len(detail_col2):
                    toggle_children.append(detail_col2[i])
            
            children.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": "📑 명세서 상세 항목"}}],
                    "children": toggle_children
                }
            })
            
            children.append({"object": "block", "type": "divider", "divider": {}})

            # 3.4 Archive (Toggle Blocks)
            # Toggle 1: Payment History
            history_rows = [
                {
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": "납기월"}}],
                            [{"type": "text", "text": {"content": "결제일"}}],
                            [{"type": "text", "text": {"content": "금액"}}],
                            [{"type": "text", "text": {"content": "상태"}}]
                        ]
                    }
                }
            ]
            
            for h in payment_history[:6]:
                h_month = h.get("billing_month", "")
                h_date = h.get("date", "")
                h_amt = self.format_currency(self.parse_int(h.get("amount", 0)))
                h_status = h.get("status", "")
                
                s_color = "blue" if "완료" in h_status else "default"
                
                history_rows.append({
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": h_month}}],
                            [{"type": "text", "text": {"content": h_date}}],
                            [{"type": "text", "text": {"content": f"{h_amt}원"}}],
                            [{"type": "text", "text": {"content": h_status}, "annotations": {"color": s_color}}]
                        ]
                    }
                })

            children.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": "🕒 최근 6개월 납부 기록"}}],
                    "children": [{
                        "object": "block",
                        "type": "table",
                        "table": {
                            "table_width": 4,
                            "has_column_header": True,
                            "has_row_header": False,
                            "children": history_rows
                        }
                    }]
                }
            })

            # Toggle 2: Original Bill (JSON 데이터 - 여러 블록으로 분할)
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            toggle2_children = []
            
            # 2000자씩 분할하여 여러 code 블록 생성
            max_length = 1900  # 안전 마진
            if len(json_data) > max_length:
                chunks = [json_data[i:i+max_length] for i in range(0, len(json_data), max_length)]
                for i, chunk in enumerate(chunks):
                    toggle2_children.append({
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}],
                            "language": "json"
                        }
                    })
            else:
                toggle2_children.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": json_data}}],
                        "language": "json"
                    }
                })
            
            children.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": "📎 고지서 원본"}}],
                    "children": toggle2_children
                }
            })

            # --- 4. 페이지 생성 요청 ---
            # 먼저 properties만으로 페이지 생성
            response = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            # 페이지 생성 후 children 추가
            if children:
                page_id = response.get("id")
                # children을 추가하기 위해 페이지 업데이트
                # Notion API는 페이지 생성 시 children을 함께 전달할 수 있지만,
                # 문제가 있을 경우 별도로 추가
                try:
                    # append_block_children 사용 (notion-client 2.x)
                    self.notion.blocks.children.append(
                        block_id=page_id,
                        children=children
                    )
                except:
                    # append가 실패하면 각 블록을 개별적으로 추가
                    for child in children:
                        try:
                            self.notion.blocks.children.append(
                                block_id=page_id,
                                children=[child]
                            )
                        except:
                            pass
            print(f"Notion Page Created: {response.get('url')}")
            return True

        except Exception as e:
            print(f"Error creating page: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_or_create_page(self, data: dict[str, Any]) -> bool:
        """기존 페이지 검색 후 업데이트 또는 생성."""
        try:
            # 간단하게 바로 페이지 생성 (중복은 Notion에서 수동 관리)
            # 또는 필요시 수동으로 기존 페이지 삭제 후 재생성
            return self.create_dashboard_page(data)

        except Exception as e:
            print(f"Notion 페이지 업데이트/생성 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
