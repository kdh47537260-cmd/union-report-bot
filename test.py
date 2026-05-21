from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
import requests
import time

BOT_TOKEN = "8886052539:AAGrUs30DNxPsyRtL7RlDHOdeQGSDwV7cUk"

CHAT_IDS = [
    "1490548765",   # 도현
]

today = datetime.now()
yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
month_start = today.replace(day=1).strftime("%Y-%m-%d")
review_target_date = f"{(today - timedelta(days=1)).month}.{(today - timedelta(days=1)).day}"

union_accounts = [
    {"id": "sz77971", "pw": "04(1)"},
    {"id": "sz83661", "pw": "02506"},
]

store_order = [
    "유월의보리 본점",
    "유월의보리 양재점",
    "유월의보리 신내점",
    "유월의보리 성남신흥점",
]

TABLE_COUNTS = {
    "유월의보리 본점": 14,
    "유월의보리 양재점": 18,
    "유월의보리 신내점": 10,
    "유월의보리 성남신흥점": 14,
}

REVIEW_URLS = {
    "유월의보리 본점": "https://pcmap.place.naver.com/restaurant/1265080366/review/visitor?reviewSort=recent",
    "유월의보리 양재점": "https://pcmap.place.naver.com/restaurant/1889387567/review/visitor?reviewSort=recent",
    "유월의보리 신내점": "https://pcmap.place.naver.com/restaurant/2021210260/review/visitor?reviewSort=recent",
    "유월의보리 성남신흥점": "https://pcmap.place.naver.com/restaurant/2032544088/review/visitor?reviewSort=recent",
}


def get_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1400")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=ko-KR")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    return webdriver.Chrome(options=options)


def clean_store_name(name):
    name = name.replace(" ", "")

    if "본점" in name:
        return "유월의보리 본점"
    if "양재" in name:
        return "유월의보리 양재점"
    if "신내" in name:
        return "유월의보리 신내점"
    if "신흥" in name or "성남" in name:
        return "유월의보리 성남신흥점"

    return name


def to_int(value):
    if value is None:
        return 0

    clean = str(value).replace(",", "").replace("원", "").strip()

    if clean.startswith("-"):
        return -int(clean[1:]) if clean[1:].isdigit() else 0

    return int(clean) if clean.isdigit() else 0


def fmt(value):
    return f"{value:,}"


def fetch_unionpos_account(acc):
    driver = get_driver()
    result = {}

    try:
        driver.get("https://asp2.unionpos.co.kr")
        time.sleep(2)

        driver.find_element(By.ID, "userId").send_keys(acc["id"])
        driver.find_element(By.ID, "password").send_keys(acc["pw"])
        driver.find_element(By.ID, "btnLogin").click()
        time.sleep(3)

        driver.get("https://asp2.unionpos.co.kr/v2/sales/period/day?StandMenuView=true")
        time.sleep(3)

        def search_period(start_date, end_date, mode="day"):
            driver.execute_script(f"""
            document.getElementById('startDate').removeAttribute('readonly');
            document.getElementById('startDate').value = '{start_date}';

            document.getElementById('endDate').removeAttribute('readonly');
            document.getElementById('endDate').value = '{end_date}';
            """)

            time.sleep(1)
            driver.find_element(By.ID, "btnSearch").click()
            time.sleep(5)

            data = {}
            page = 1

            while True:
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    values = [cell.text.strip() for cell in cells]

                    if len(values) >= 8 and values[0].isdigit():
                        store_name = clean_store_name(values[2])
                        total_sales_int = to_int(values[4])
                        receipt_count_int = to_int(values[3])

                        if store_name not in data:
                            data[store_name] = {
                                "total_sales_int": 0,
                                "receipt_count_int": 0,
                                "table_price": values[5],
                            }

                        data[store_name]["total_sales_int"] += total_sales_int
                        data[store_name]["receipt_count_int"] += receipt_count_int

                        if mode == "day":
                            data[store_name]["table_price"] = values[5]

                page += 1

                next_page = driver.find_elements(
                    By.XPATH,
                    f"//a[@href='javascript:goPage({page})']"
                )

                if not next_page:
                    break

                driver.execute_script(f"goPage({page});")
                time.sleep(4)

            for store_name in data:
                data[store_name]["total_sales"] = fmt(data[store_name]["total_sales_int"])
                data[store_name]["receipt_count"] = fmt(data[store_name]["receipt_count_int"])

            return data

        day_data = search_period(yesterday, yesterday, mode="day")
        month_data = search_period(month_start, yesterday, mode="month")

        for store_name, day in day_data.items():
            result[store_name] = {
                "total_sales": day["total_sales"],
                "receipt_count": day["receipt_count"],
                "table_price": day["table_price"],
                "month_sales": month_data.get(store_name, {}).get("total_sales", "0"),
            }

        return result

    except Exception as e:
        print("UnionPOS 조회 실패:", e)
        return result

    finally:
        driver.quit()


def fetch_menu_top_sales(acc):
    driver = get_driver()
    result = {}

    try:
        driver.get("https://asp2.unionpos.co.kr")
        time.sleep(2)

        driver.find_element(By.ID, "userId").send_keys(acc["id"])
        driver.find_element(By.ID, "password").send_keys(acc["pw"])
        driver.find_element(By.ID, "btnLogin").click()
        time.sleep(3)

        try:
            selected_store_name = clean_store_name(
                driver.find_element(By.CSS_SELECTOR, ".top-storeName").text.strip()
            )
        except Exception:
            selected_store_name = ""

        driver.get("https://asp2.unionpos.co.kr/v2/sales/product/storeItem")
        time.sleep(3)

        driver.execute_script(f"""
        document.getElementById('startDate').removeAttribute('readonly');
        document.getElementById('startDate').value = '{yesterday}';

        document.getElementById('endDate').removeAttribute('readonly');
        document.getElementById('endDate').value = '{yesterday}';

        if (document.getElementById('pageSize')) {{
            document.getElementById('pageSize').value = '100';
        }}
        """)

        time.sleep(1)
        driver.find_element(By.ID, "btnSearch").click()
        time.sleep(5)

        page = 1

        while True:
            rows = driver.find_elements(By.CSS_SELECTOR, "#tableList tbody tr, table tbody tr")

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                values = [cell.text.strip() for cell in cells]

                if len(values) < 5:
                    continue

                if not values[0].isdigit():
                    continue

                parsed = None

                # 다중매장 선택 화면 컬럼 예시:
                # 0 번호 / 1 매장명 / 2 분류명 / 3 상품코드 / 4 상품명 / 5 수량 / 6 매출금액
                if len(values) >= 7 and "유월" in values[1]:
                    parsed = {
                        "store_name": clean_store_name(values[1]),
                        "item_name": values[4],
                        "qty": to_int(values[5]),
                        "sales": to_int(values[6]),
                    }

                # 단일매장 선택 화면 컬럼 예시:
                # 0 번호 / 1 분류명 / 2 상품코드 / 3 상품명 / 4 수량 / 5 매출금액
                elif len(values) >= 6:
                    parsed = {
                        "store_name": selected_store_name,
                        "item_name": values[3],
                        "qty": to_int(values[4]),
                        "sales": to_int(values[5]),
                    }

                if not parsed:
                    continue

                store_name = parsed["store_name"]
                item_name = parsed["item_name"]
                qty = parsed["qty"]
                sales = parsed["sales"]

                if not store_name or "외" in store_name:
                    continue
                if not item_name or qty <= 0 or sales <= 0:
                    continue

                if store_name not in result:
                    result[store_name] = {}

                if item_name not in result[store_name]:
                    result[store_name][item_name] = {
                        "item": item_name,
                        "qty": 0,
                        "sales": 0,
                    }

                result[store_name][item_name]["qty"] += qty
                result[store_name][item_name]["sales"] += sales

            page += 1

            next_page = driver.find_elements(
                By.XPATH,
                f"//a[@href='javascript:goPage({page})']"
            )

            if not next_page:
                break

            driver.execute_script(f"goPage({page});")
            time.sleep(4)

        final_result = {}

        for store_name, item_map in result.items():
            final_result[store_name] = list(item_map.values())

        return final_result

    except Exception as e:
        print("메뉴 TOP 조회 실패:", e)
        return {}

    finally:
        driver.quit()

def switch_to_frame_containing_element(driver, element_id):
    try:
        exists = driver.execute_script(
            "return document.getElementById(arguments[0]) !== null;",
            element_id
        )

        if exists:
            return True

    except Exception:
        pass

    frames = driver.find_elements(By.TAG_NAME, "frame") + driver.find_elements(By.TAG_NAME, "iframe")

    for frame in frames:
        try:
            driver.switch_to.frame(frame)

            found = switch_to_frame_containing_element(driver, element_id)

            if found:
                return True

            driver.switch_to.parent_frame()

        except Exception:
            try:
                driver.switch_to.parent_frame()
            except Exception:
                pass

    return False


def fetch_okpos():
    driver = get_driver()

    try:
        driver.get("https://nicepay.okpos.co.kr/")
        time.sleep(2)

        driver.find_element(By.ID, "user_id").send_keys("n46083")
        driver.find_element(By.ID, "user_pwd").send_keys("02504")
        driver.execute_script("doSubmit();")
        time.sleep(5)

        driver.execute_script("""
        cswmButtonSelect('cswmMenuButtonGroup_15', 'Group_15');
        cswmButtonDown('cswmMenuButtonGroup_15', 'Group_15');
        """)

        time.sleep(2)

        sales_status = driver.find_element(By.ID, "cswmItemGroup_15_10")

        driver.execute_script("""
        arguments[0].dispatchEvent(
            new MouseEvent('mouseover', {
                bubbles:true,
                cancelable:true,
                view:window
            })
        );
        """, sales_status)

        time.sleep(2)

        day_menu = driver.find_element(By.ID, "cswmItem10_56")

        driver.execute_script("""
        arguments[0].dispatchEvent(
            new MouseEvent('click', {
                bubbles:true,
                cancelable:true,
                view:window
            })
        );
        """, day_menu)

        time.sleep(8)

        driver.switch_to.default_content()

        found = switch_to_frame_containing_element(driver, "date1_1")

        if not found:
            return {}

        def search_period(start_date, end_date):
            driver.execute_script(f"""
            document.getElementById('date1_1').removeAttribute('readonly');
            document.getElementById('date1_1').value = '{start_date}';

            document.getElementById('date1_2').removeAttribute('readonly');
            document.getElementById('date1_2').value = '{end_date}';
            """)

            time.sleep(1)
            driver.execute_script("fnSearch();")
            time.sleep(8)

            cells = driver.find_elements(By.CSS_SELECTOR, "td")
            values = [c.text.strip() for c in cells if c.text.strip()]

            number_values = []

            for v in values:
                clean = v.replace(",", "")

                if clean.isdigit():
                    number_values.append(v)

            return {
                "total_sales": number_values[-13],
                "receipt_count": number_values[-8],
                "table_price": number_values[-5],
            }

        day_data = search_period(yesterday, yesterday)
        month_data = search_period(month_start, yesterday)

        receipt_count = to_int(day_data["receipt_count"])
        table_price = fmt(round(to_int(day_data["total_sales"]) / receipt_count)) if receipt_count else "0"

        return {
            "유월의보리 본점": {
                "total_sales": day_data["total_sales"],
                "receipt_count": day_data["receipt_count"],
                "table_price": table_price,
                "month_sales": month_data["total_sales"],
            }
        }

    except Exception as e:
        print("OKPOS 조회 실패:", e)
        return {}

    finally:
        driver.quit()


def fetch_reviews():
    driver = get_driver()
    review_data = {}

    try:
        for store_name, url in REVIEW_URLS.items():
            driver.get(url)
            time.sleep(8)

            try:
                driver.find_element(
                    By.XPATH,
                    "//a[contains(text(), '최신순')]"
                ).click()
                time.sleep(4)
            except Exception:
                pass

            last_count = 0
            same_count = 0

            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                more_buttons = driver.find_elements(By.CSS_SELECTOR, "span.TeItc")

                for btn in more_buttons:
                    try:
                        if "펼쳐서 더보기" in btn.text:
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(1)
                    except Exception:
                        pass

                cards = driver.find_elements(By.XPATH, "//li[.//time]")

                current_count = 0

                for card in cards:
                    try:
                        date_text = card.find_element(By.TAG_NAME, "time").text.strip()

                        if date_text.startswith(review_target_date):
                            current_count += 1

                    except Exception:
                        pass

                if current_count == last_count:
                    same_count += 1
                else:
                    same_count = 0
                    last_count = current_count

                if same_count >= 3:
                    break

                if len(cards) > 250:
                    break

            cards = driver.find_elements(By.XPATH, "//li[.//time]")
            review_texts = []

            for card in cards:
                try:
                    date_text = card.find_element(By.TAG_NAME, "time").text.strip()

                    if not date_text.startswith(review_target_date):
                        continue

                    candidates = []

                    review_candidates = card.find_elements(
                        By.CSS_SELECTOR,
                        "a[data-pui-click-code='rvshowless'], a[data-pui-click-code='rvshowmore']"
                    )

                    for review_el in review_candidates:
                        candidates.append(review_el.text.strip())

                    if not candidates:
                        for line in card.text.split("\n"):
                            line = line.strip()
                            if len(line) >= 10:
                                candidates.append(line)

                    for review_text in candidates:
                        if not review_text:
                            continue
                        if len(review_text) < 10:
                            continue
                        if review_text == date_text:
                            continue
                        if review_text.startswith(review_target_date):
                            continue
                        if "리뷰" in review_text and "사진" in review_text:
                            continue
                        if "팔로우" in review_text:
                            continue
                        if "개의 리뷰가 더 있습니다" in review_text:
                            continue
                        if "반응 남기기" in review_text:
                            continue
                        if "방문예약" in review_text:
                            continue
                        if "대기 시간" in review_text:
                            continue
                        if "친목" in review_text:
                            continue
                        if "데이트" in review_text:
                            continue
                        if "연인・배우자" in review_text:
                            continue
                        if "지인・동료" in review_text:
                            continue
                        if review_text.startswith("+"):
                            continue

                        review_texts.append(review_text)
                        break

                except Exception:
                    pass

            review_data[store_name] = list(dict.fromkeys(review_texts))

        return review_data

    except Exception as e:
        print("리뷰 조회 실패:", e)
        return review_data

    finally:
        driver.quit()


all_store_data = {}

all_store_data.update(fetch_okpos())

for acc in union_accounts:
    all_store_data.update(fetch_unionpos_account(acc))

menu_top_data = {}

for acc in union_accounts:
    account_menu_data = fetch_menu_top_sales(acc)

    for store_name, items in account_menu_data.items():
        if store_name not in menu_top_data:
            menu_top_data[store_name] = []

        menu_top_data[store_name].extend(items)

review_data = fetch_reviews()

report_lines = [
    "[유월의보리 일매출 리포트]",
    f"조회일자: {yesterday}",
    ""
]

for store_name in store_order:
    data = all_store_data.get(store_name)

    if not data:
        reviews = review_data.get(store_name, [])
        review_text = f"전일 신규리뷰: {len(reviews)}건"

        for idx, review in enumerate(reviews, start=1):
            review_text += f"\n{idx}. {review}"

        report_lines.append(f"""
[{store_name}]
조회 실패 또는 데이터 없음

{review_text}
""")
        continue

    receipt_count_int = to_int(data["receipt_count"])
    sales_int = to_int(data["total_sales"])
    table_count = TABLE_COUNTS.get(store_name, 1)
    rotation = round(receipt_count_int / table_count, 1)
    table_price = fmt(round(sales_int / receipt_count_int)) if receipt_count_int else "0"

    menu_text = "메뉴 TOP5: 데이터 없음"

    if store_name in menu_top_data:
        sorted_items = sorted(
            menu_top_data[store_name],
            key=lambda x: x["sales"],
            reverse=True
        )

        menu_lines = ["메뉴 TOP5"]

        for idx, item in enumerate(sorted_items[:5], start=1):
            ratio = (item["sales"] / sales_int * 100) if sales_int else 0

            menu_lines.append(
                f"{idx}. {item['item']} / {item['qty']}개 / {fmt(item['sales'])}원 / 매출비중 {ratio:.1f}%"
            )

        menu_text = "\n".join(menu_lines)

    reviews = review_data.get(store_name, [])
    review_text = f"전일 신규리뷰: {len(reviews)}건"

    for idx, review in enumerate(reviews, start=1):
        review_text += f"\n{idx}. {review}"

    report_lines.append(f"""
[{store_name}]
총매출: {data['total_sales']}원
영수건수(회전수): {data['receipt_count']}건 ({rotation}회전)
테이블단가: {table_price}원
월누적매출: {data['month_sales']}원

{menu_text}

{review_text}
""")

report = "\n".join(report_lines)

print(report)

telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

for chat_id in CHAT_IDS:
    payload = {
        "chat_id": chat_id,
        "text": report
    }

    requests.post(telegram_url, data=payload)

print("텔레그램 전송 완료")
