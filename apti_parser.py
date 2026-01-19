"""APT.i Playwright 파서."""

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
        print("로그인 시도 중...")
        await self._page.goto(f"{self.BASE_URL}/aptHome/", wait_until="networkidle")
        await asyncio.sleep(2)  # 페이지 로딩 대기
        
        if is_phone_number(self.user_id):
            await self._page.evaluate("""() => {
                document.querySelectorAll('.hideHP').forEach(el => el.style.display = '');
                document.querySelectorAll('.hideID').forEach(el => el.style.display = 'none');
            }""")
            await asyncio.sleep(1)  # UI 전환 대기
            
            # evaluate로 직접 값 설정 (hidden 요소도 가능)
            await self._page.evaluate(f"""() => {{
                const hpId = document.querySelector("input[name='hp_id']");
                const hpPwd = document.querySelector("input[name='hp_pwd']");
                if (hpId) hpId.value = "{self.user_id}";
                if (hpPwd) hpPwd.value = "{self.password}";
            }}""")
            await self._page.evaluate("loginHtml('H')")
        else:
            await self._page.evaluate(f"""() => {{
                const loginId = document.querySelector("input[name='login_id']");
                const loginPwd = document.querySelector("input[name='login_pwd']");
                if (loginId) loginId.value = "{self.user_id}";
                if (loginPwd) loginPwd.value = "{self.password}";
            }}""")
            await self._page.evaluate("loginHtml('I')")

        await asyncio.sleep(3)  # 로그인 처리 대기
        await self._page.wait_for_load_state("networkidle")
        
        # 쿠키 체크로 로그인 확인
        cookies = await self._page.context.cookies()
        login_success = any("token" in c["name"].lower() for c in cookies)
        
        if login_success:
            print("로그인 성공")
            return True
        print("로그인 실패 가능성 있음")
        return False

    async def fetch_all_data(self) -> dict:
        """모든 데이터 수집."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "dong_ho": "",
            "maint_items": [],
            "maint_payment": {},
            "energy_category": [],
            "payment_history": [],
        }

        try:
            # 1. 동호 정보
            print("동호 정보 수집 중...")
            await self._page.goto(f"{self.BASE_URL}/aptHome/subpage/?cate_code=AAEB", wait_until="networkidle")
            dong_ho_text = await self._page.evaluate("""() => {
                const el = document.querySelector('div.Nbox1_txt10');
                return el ? el.textContent.trim() : '';
            }""")
            
            # 동호 텍스트에서 숫자 추출 (예: "1306동 1001호" -> "13061001")
            if dong_ho_text:
                match = re.search(r"(\d+)동\s*(\d+)호", dong_ho_text)
                if match:
                    dong = match.group(1).zfill(4)
                    ho = match.group(2).zfill(4)
                    data["dong_ho"] = dong + ho
                else:
                    data["dong_ho"] = dong_ho_text
            print(f"동호: {data['dong_ho']}")

            # 2. 관리비 항목 & 납부액
            print("관리비 정보 수집 중...")
            await self._page.goto(f"{self.BASE_URL}/apti/manage/manage_cost.asp?cate_code=AAEB", wait_until="networkidle")
            
            # 납부액 및 기본 정보
            data["maint_payment"] = await self._page.evaluate("""() => {
                const res = {};
                const costPay = document.querySelector('span.costPay');
                if (costPay) res['amount'] = costPay.textContent.trim().replace(/,/g, '');
                
                const dts = document.querySelectorAll('div.costpayBox dt');
                dts.forEach(dt => {
                   if(dt.textContent.includes('월분')) {
                       const match = dt.textContent.match(/(\\d+)월분/);
                       if(match) res['month'] = match[1];
                   } 
                });
                
                const deadline = document.querySelector('div.endBox span');
                if(deadline) res['deadline'] = deadline.textContent.trim();
                
                const status = document.querySelector('div.dayBox p');
                if(status) res['status'] = status.textContent.trim();
                
                return res;
            }""")

            # 상세 항목 리스트
            data["maint_items"] = await self._page.evaluate("""() => {
                const items = [];
                document.querySelectorAll('a.black').forEach(link => {
                    const row = link.closest('tr');
                    const tds = row.querySelectorAll('td');
                    if(tds.length >= 4) {
                        items.push({
                            'item': link.textContent.trim(),
                            'current': tds[1].textContent.trim().replace(/,/g, ''),
                            'previous': tds[2].textContent.trim().replace(/,/g, ''),
                            'change': tds[3].textContent.trim().replace(/,/g, '')
                        });
                    }
                });
                return items;
            }""")
            print(f"관리비 항목: {len(data['maint_items'])}개")

            # 3. 에너지 카테고리 (비교 문구 포함)
            print("에너지 카테고리 수집 중...")
            await self._page.goto(f"{self.BASE_URL}/apti/manage/manage_energy.asp?cate_code=AAEC", wait_until="networkidle")
            await asyncio.sleep(1)  # 페이지 로딩 대기
            data["energy_category"] = await self._page.evaluate("""() => {
                const res = [];
                document.querySelectorAll('div.engBox').forEach(box => {
                    const h3 = box.querySelector('h3');
                    if (!h3) return;
                    const type = h3.textContent.replace(/[\\n\\t]/g, '').trim();
                    if(!type) return;
                    
                    let usage = '0', cost = '0', comparison = '';
                    const engUnit = box.querySelector('ul.engUnit');
                    if (engUnit) {
                        const lis = engUnit.querySelectorAll('li');
                        let foundLine = false;
                        for (const li of lis) {
                            if (li.classList.contains('line')) { 
                                foundLine = true; 
                                continue; 
                            }
                            const strong = li.querySelector('strong');
                            if (strong) {
                                const text = strong.textContent.trim();
                                if (!foundLine) {
                                    usage = text.replace(/,/g, '');
                                } else {
                                    cost = text.replace(/,/g, '').replace('원', '');
                                }
                            }
                        }
                    }
                    const txtBox = box.querySelector('div.txtBox');
                    if (txtBox) {
                        const compElem = txtBox.querySelector('strong');
                        if (compElem) comparison = compElem.textContent.trim();
                    }
                    res.push({ type, usage, cost, comparison });
                });
                return res;
            }""")
            print(f"에너지 카테고리: {len(data['energy_category'])}개")

            # 4. 납부 내역
            print("납부내역 수집 중...")
            await self._page.goto(f"{self.BASE_URL}/apti/manage/manage_check.asp?cate_code=AAFH", wait_until="networkidle")
            data["payment_history"] = await self._page.evaluate("""() => {
                const res = [];
                const table = document.querySelector('table.table-w') || document.querySelector('div#hidden-xs2 table.table-w');
                if (table) {
                    const tbody = table.querySelector('tbody');
                    if (tbody) {
                        tbody.querySelectorAll('tr').forEach(tr => {
                            const tds = tr.querySelectorAll('td');
                            if(tds.length >= 7) {
                                const dateText = tds[0].textContent.trim();
                                if(dateText && dateText.match(/\\d{4}\\.\\d{2}\\.\\d{2}/)) {
                                    res.push({
                                        date: dateText,
                                        amount: tds[1].textContent.trim().replace(/,/g, ''),
                                        billing_month: tds[2].textContent.trim(),
                                        deadline: tds[3].textContent.trim(),
                                        bank: tds[4].textContent.trim(),
                                        method: tds[5].textContent.trim(),
                                        status: tds[6].textContent.trim()
                                    });
                                }
                            }
                        });
                    }
                }
                return res;
            }""")
            print(f"납부내역: {len(data['payment_history'])}건")

        except Exception as e:
            print(f"Data Fetch Error: {e}")
            import traceback
            traceback.print_exc()
        
        return data

    async def run(self) -> dict | None:
        """실행."""
        try:
            await self._init_browser()
            if await self.login():
                print("데이터 수집 시작...")
                data = await self.fetch_all_data()
                print("데이터 수집 완료!")
                await self._close_browser()
                return data
            print("로그인 실패로 데이터 수집 불가")
            await self._close_browser()
            return None
        except Exception as e:
            print(f"파싱 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            await self._close_browser()
            return None
