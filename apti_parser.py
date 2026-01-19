"""APT.i Playwright 파서 - GitHub Actions용."""

import asyncio
import re
from datetime import datetime

from playwright.async_api import async_playwright


def is_phone_number(text: str) -> bool:
    """휴대폰 번호 여부 확인."""
    return bool(re.match(r"^0\d{9,10}$", text.replace("-", "")))


class APTiParser:
    """APT.i 파서."""

    BASE_URL = "https://xn--3-v85erd9xh0vctai95f4a637hvqbda945jmkaw30h.apti.co.kr"

    def __init__(self, user_id: str, password: str) -> None:
        """초기화."""
        self.user_id = user_id
        self.password = password
        self._playwright = None
        self._browser = None
        self._page = None

    async def _init_browser(self) -> None:
        """브라우저 초기화."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self._page = await context.new_page()

    async def _close_browser(self) -> None:
        """브라우저 종료."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def login(self) -> bool:
        """로그인."""
        print("로그인 시작...")

        await self._page.goto(f"{self.BASE_URL}/aptHome/", wait_until="networkidle")
        await asyncio.sleep(2)

        is_phone = is_phone_number(self.user_id)

        if is_phone:
            await self._page.evaluate("""
                () => {
                    document.querySelectorAll('.hideHP').forEach(el => el.style.display = '');
                    document.querySelectorAll('.hideID').forEach(el => el.style.display = 'none');
                }
            """)
            await asyncio.sleep(0.5)

            await self._page.evaluate(f"""
                () => {{
                    document.querySelector("input[name='hp_id']").value = "{self.user_id}";
                    document.querySelector("input[name='hp_pwd']").value = "{self.password}";
                }}
            """)
            await self._page.evaluate("loginHtml('H')")
        else:
            await self._page.fill("input[name='login_id']", self.user_id)
            await self._page.fill("input[name='login_pwd']", self.password)
            await self._page.evaluate("loginHtml('I')")

        await asyncio.sleep(3)
        await self._page.wait_for_load_state("networkidle")

        cookies = await self._page.context.cookies()
        for cookie in cookies:
            if "se_token" in cookie["name"]:
                print("로그인 성공!")
                return True

        print("로그인 실패!")
        return False

    async def fetch_all_data(self) -> dict:
        """모든 데이터 수집."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "dong_ho": "",
            "maint_items": [],
            "maint_payment": {},
            "energy_category": [],
            "energy_type": [],
            "payment_history": [],
        }

        # 동호 정보
        data["dong_ho"] = await self._get_dong_ho()

        # 관리비 항목
        data["maint_items"] = await self._fetch_maint_items()

        # 관리비 납부액
        data["maint_payment"] = await self._fetch_maint_payment()

        # 에너지 카테고리
        data["energy_category"] = await self._fetch_energy_category()

        # 에너지 종류별
        data["energy_type"] = await self._fetch_energy_type()

        # 납부내역
        data["payment_history"] = await self._fetch_payment_history()

        return data

    async def _get_dong_ho(self) -> str:
        """동호 정보."""
        try:
            url = f"{self.BASE_URL}/aptHome/subpage/?cate_code=AAEB"
            await self._page.goto(url, wait_until="networkidle")
            await asyncio.sleep(1)

            dong_ho = await self._page.evaluate("""
                () => {
                    const elem = document.querySelector('div.Nbox1_txt10');
                    if (elem) {
                        const match = elem.textContent.match(/(\\d+)동\\s*(\\d+)호/);
                        if (match) return match[1].padStart(4, '0') + match[2].padStart(4, '0');
                    }
                    return '';
                }
            """)
            return dong_ho
        except Exception as e:
            print(f"동호 정보 오류: {e}")
            return ""

    async def _fetch_maint_items(self) -> list:
        """관리비 항목."""
        try:
            url = f"{self.BASE_URL}/apti/manage/manage_cost.asp?cate_code=AAEB"
            await self._page.goto(url, wait_until="networkidle")
            await asyncio.sleep(2)

            items = await self._page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a.black');
                    links.forEach(link => {
                        const row = link.closest('tr');
                        if (row) {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 4) {
                                results.push({
                                    'item': link.textContent.trim(),
                                    'current': cells[1].textContent.trim().replace(/,/g, ''),
                                    'previous': cells[2].textContent.trim().replace(/,/g, ''),
                                    'change': cells[3].textContent.trim().replace(/,/g, '')
                                });
                            }
                        }
                    });
                    return results;
                }
            """)
            print(f"관리비 항목: {len(items)}개")
            return items
        except Exception as e:
            print(f"관리비 항목 오류: {e}")
            return []

    async def _fetch_maint_payment(self) -> dict:
        """관리비 납부액 및 비교 데이터."""
        try:
            url = f"{self.BASE_URL}/apti/manage/manage_cost.asp?cate_code=AAEB"
            await self._page.goto(url, wait_until="networkidle")
            await asyncio.sleep(2)

            payment = await self._page.evaluate("""
                () => {
                    const result = {};
                    const costPayElem = document.querySelector('span.costPay');
                    if (costPayElem) {
                        result['amount'] = costPayElem.textContent.trim().replace(/,/g, '');
                    }
                    const dtElements = document.querySelectorAll('div.costpayBox dt');
                    for (const dt of dtElements) {
                        const dtText = dt.textContent.trim();
                        if (dtText.includes('월분 부과 금액')) {
                            const dd = dt.nextElementSibling;
                            if (dd && dd.tagName === 'DD') {
                                result['charged'] = dd.textContent.trim().replace(/[원,]/g, '');
                            }
                            const monthMatch = dtText.match(/(\\d+)월분/);
                            if (monthMatch) result['month'] = monthMatch[1];
                            break;
                        }
                    }
                    const deadlineElem = document.querySelector('div.endBox span');
                    if (deadlineElem) result['deadline'] = deadlineElem.textContent.trim();
                    const dayBox = document.querySelector('div.dayBox p');
                    if (dayBox) result['status'] = dayBox.textContent.trim();
                    
                    // 비교 데이터 수집
                    result['comparison'] = {};
                    
                    // 전체 페이지에서 비교 데이터 찾기
                    const allText = document.body.textContent || '';
                    
                    // 전년 비교 (전년동월) - ₩317,860 형식 찾기
                    const prevYearRegex = /전년동월[\\s\\S]{0,100}?[₩원]?[\\s]*([\\d,]+)/;
                    const prevYearMatch = allText.match(prevYearRegex);
                    if (prevYearMatch) {
                        result['comparison']['previous_year'] = prevYearMatch[1].replace(/,/g, '');
                    }
                    
                    // 우리아파트 동일면적 비교 - 최저, 평균 찾기
                    const sameAreaSection = document.querySelector('*:contains("우리아파트"), *:contains("동일면적")');
                    if (!sameAreaSection) {
                        // 텍스트 기반으로 찾기
                        const sameAreaRegex = /우리아파트[\\s\\S]{0,200}?동일면적[\\s\\S]{0,500}?최저[\\s\\S]{0,50}?[₩원]?[\\s]*([\\d,]+)[\\s\\S]{0,100}?평균[\\s\\S]{0,50}?[₩원]?[\\s]*([\\d,]+)/;
                        const sameAreaMatch = allText.match(sameAreaRegex);
                        if (sameAreaMatch) {
                            result['comparison']['same_area_lowest'] = sameAreaMatch[1].replace(/,/g, '');
                            result['comparison']['same_area_average'] = sameAreaMatch[2].replace(/,/g, '');
                        }
                    }
                    
                    // 에너지사용량 동일면적 비교
                    const energyRegex = /에너지[\\s\\S]{0,100}?동일면적[\\s\\S]{0,500}?최저[\\s\\S]{0,50}?[₩원]?[\\s]*([\\d,]+)[\\s\\S]{0,100}?평균[\\s\\S]{0,50}?[₩원]?[\\s]*([\\d,]+)/;
                    const energyMatch = allText.match(energyRegex);
                    if (energyMatch) {
                        result['comparison']['energy_same_area_lowest'] = energyMatch[1].replace(/,/g, '');
                        result['comparison']['energy_same_area_average'] = energyMatch[2].replace(/,/g, '');
                    }
                    
                    // 더 정확한 방법: 특정 클래스나 ID를 가진 요소 찾기
                    const compareCards = document.querySelectorAll('div.card, div.compare-card, div[class*="compare"], div[class*="comparison"]');
                    compareCards.forEach(card => {
                        const cardHTML = card.innerHTML || '';
                        const cardText = card.textContent || '';
                        
                        // 전년 비교 카드
                        if (cardText.includes('전년') || cardText.includes('전년동월')) {
                            const amounts = cardText.match(/[₩원]?[\\s]*([\\d,]+)/g);
                            if (amounts && amounts.length > 0) {
                                // 첫 번째 금액이 전년동월 금액일 가능성
                                const amount = amounts[0].replace(/[^\\d]/g, '');
                                if (amount && amount.length >= 5 && !result['comparison']['previous_year']) {
                                    result['comparison']['previous_year'] = amount;
                                }
                            }
                        }
                        
                        // 동일면적 비교 카드
                        if (cardText.includes('동일면적') && cardText.includes('우리아파트')) {
                            const amounts = cardText.match(/[₩원]?[\\s]*([\\d,]+)/g);
                            if (amounts && amounts.length >= 2) {
                                // 최저와 평균 찾기
                                const lowestMatch = cardText.match(/최저[\\s\\S]{0,50}?[₩원]?[\\s]*([\\d,]+)/);
                                const avgMatch = cardText.match(/평균[\\s\\S]{0,50}?[₩원]?[\\s]*([\\d,]+)/);
                                if (lowestMatch) {
                                    result['comparison']['same_area_lowest'] = lowestMatch[1].replace(/,/g, '');
                                }
                                if (avgMatch) {
                                    result['comparison']['same_area_average'] = avgMatch[1].replace(/,/g, '');
                                }
                            }
                        }
                        
                        // 에너지 비교 카드
                        if (cardText.includes('에너지') && cardText.includes('동일면적')) {
                            const lowestMatch = cardText.match(/최저[\\s\\S]{0,50}?[₩원]?[\\s]*([\\d,]+)/);
                            const avgMatch = cardText.match(/평균[\\s\\S]{0,50}?[₩원]?[\\s]*([\\d,]+)/);
                            if (lowestMatch) {
                                result['comparison']['energy_same_area_lowest'] = lowestMatch[1].replace(/,/g, '');
                            }
                            if (avgMatch) {
                                result['comparison']['energy_same_area_average'] = avgMatch[1].replace(/,/g, '');
                            }
                        }
                    });
                    
                    return result;
                }
            """)
            print(f"관리비 납부액: {payment.get('amount', 'N/A')}원")
            if payment.get('comparison'):
                print(f"비교 데이터: {payment.get('comparison')}")
            return payment
        except Exception as e:
            print(f"관리비 납부액 오류: {e}")
            import traceback
            traceback.print_exc()
            return {}

    async def _fetch_energy_category(self) -> list:
        """에너지 카테고리."""
        try:
            url = f"{self.BASE_URL}/apti/manage/manage_energy.asp?cate_code=AAEC"
            await self._page.goto(url, wait_until="networkidle")
            await asyncio.sleep(2)

            data = await self._page.evaluate("""
                () => {
                    const results = [];
                    const boxes = document.querySelectorAll('div.engBox');
                    boxes.forEach(box => {
                        const h3 = box.querySelector('h3');
                        if (!h3) return;
                        const energyType = h3.textContent.replace(/[\\n\\t]/g, '').trim();
                        let usage = '0', cost = '0', comparison = '';
                        const engUnit = box.querySelector('ul.engUnit');
                        if (engUnit) {
                            const lis = engUnit.querySelectorAll('li');
                            let foundLine = false;
                            for (const li of lis) {
                                if (li.classList.contains('line')) { foundLine = true; continue; }
                                const strong = li.querySelector('strong');
                                if (strong) {
                                    const text = strong.textContent.trim();
                                    if (!foundLine) usage = text.replace(/,/g, '');
                                    else cost = text.replace(/,/g, '').replace('원', '');
                                }
                            }
                        }
                        const txtBox = box.querySelector('div.txtBox');
                        if (txtBox) {
                            const compElem = txtBox.querySelector('strong');
                            if (compElem) comparison = compElem.textContent.trim();
                        }
                        if (energyType) results.push({ type: energyType, usage, cost, comparison });
                    });
                    return results;
                }
            """)
            print(f"에너지 카테고리: {len(data)}개")
            return data
        except Exception as e:
            print(f"에너지 카테고리 오류: {e}")
            return []

    async def _fetch_energy_type(self) -> list:
        """에너지 종류별."""
        try:
            url = f"{self.BASE_URL}/apti/manage/manage_energyGogi.asp"
            await self._page.goto(url, wait_until="networkidle")
            await asyncio.sleep(2)

            data = await self._page.evaluate("""
                () => {
                    const results = [];
                    const boxes = document.querySelectorAll('div.bill_box');
                    boxes.forEach(box => {
                        const info = {};
                        const h3 = box.querySelector('h3');
                        if (h3) info['type'] = h3.textContent.replace(/[\\n\\t]/g, '').trim();
                        const totalElem = box.querySelector('span.totalBill strong');
                        if (totalElem) info['total'] = totalElem.textContent.trim().replace(/,/g, '');
                        const compareDiv = box.querySelector('div.energy_data');
                        if (compareDiv) {
                            const txt = compareDiv.querySelector('p.txt');
                            if (txt) info['comparison'] = txt.textContent.trim();
                        }
                        const tblBill = box.querySelector('div.tbl_bill');
                        if (tblBill) {
                            const rows = tblBill.querySelectorAll('tr');
                            rows.forEach(row => {
                                const ths = row.querySelectorAll('th');
                                const tds = row.querySelectorAll('td');
                                for (let i = 0; i < ths.length && i < tds.length; i++) {
                                    const key = ths[i].textContent.trim();
                                    const value = tds[i].textContent.trim().replace('원', '').replace(/,/g, '');
                                    info[key] = value;
                                }
                            });
                        }
                        if (info['type']) results.push(info);
                    });
                    return results;
                }
            """)
            print(f"에너지 종류별: {len(data)}개")
            return data
        except Exception as e:
            print(f"에너지 종류별 오류: {e}")
            return []

    async def _fetch_payment_history(self) -> list:
        """납부내역."""
        try:
            url = f"{self.BASE_URL}/apti/manage/manage_check.asp?cate_code=AAFH"
            await self._page.goto(url, wait_until="networkidle")
            await asyncio.sleep(2)

            data = await self._page.evaluate(r"""
                () => {
                    const results = [];
                    let table = document.querySelector('div#hidden-xs2 table.table-w');
                    if (!table) table = document.querySelector('table.table-w');
                    if (table) {
                        const tbody = table.querySelector('tbody');
                        if (tbody) {
                            const rows = tbody.querySelectorAll('tr');
                            rows.forEach(row => {
                                const cells = row.querySelectorAll('td');
                                if (cells.length >= 7) {
                                    const dateText = cells[0].textContent.trim();
                                    if (dateText && dateText.match(/\d{4}\.\d{2}\.\d{2}/)) {
                                        results.push({
                                            date: dateText,
                                            amount: cells[1].textContent.trim().replace(/,/g, ''),
                                            billing_month: cells[2].textContent.trim(),
                                            deadline: cells[3].textContent.trim(),
                                            bank: cells[4].textContent.trim(),
                                            method: cells[5].textContent.trim(),
                                            status: cells[6].textContent.trim()
                                        });
                                    }
                                }
                            });
                        }
                    }
                    return results;
                }
            """)
            print(f"납부내역: {len(data)}건")
            return data
        except Exception as e:
            print(f"납부내역 오류: {e}")
            return []

    async def run(self) -> dict | None:
        """실행."""
        try:
            await self._init_browser()
            if await self.login():
                return await self.fetch_all_data()
            return None
        finally:
            await self._close_browser()
