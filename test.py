from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.service import Service
from datetime import datetime, timedelta
import requests
import time

BOT_TOKEN = "8886052539:AAGrUs30DNxPsyRtL7RlDHOdeQGSDwV7cUk"

CHAT_IDS = [
    "1490548765",   # 도현
    "8650028323",   # 대표님
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


from selenium.webdriver.chrome.options import Options

def get_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,1000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    return webdriver.Chrome(options=options)

    
def clean_store_name(name):
    name = name.replace(" ", "")

    if "양재" in name:
        return "유월의보리 양재점"

    if "신내" in name:
        return "유월의보리 신내점"

    if "신흥" in name or "성남" in name:
        return "유월의보리 성남신흥점"

    return name


def to_int(value):
    return int(value.replace(",", "").strip()) if value and value.replace(",", "").strip().isdigit() else 0


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

        url = (
            "https://asp2.unionpos.co.kr/v2/sales/product/storeItem"
            f"?pageNo=1"
            f"&rangeDate={yesterday}+~+{yesterday}"
            f"&startDate={yesterday}"
            f"&endDate={yesterday}"
            f"&searchType=ItemName"
            f"&searchKeyword="
            f"&pageSize=100"
        )

        driver.get(url)

        time.sleep(5)

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        for row in rows:

            cells = row.find_elements(By.TAG_NAME, "td")
            values = [cell.text.strip() for cell in cells]

            if len(values) < 5:
                continue

            try:
                store_name = clean_store_name(values[0])
                item_name = values[1]

                qty = to_int(values[2])
                sales = to_int(values[3])

                if sales <= 0:
                    continue

                if store_name not in result:
                    result[store_name] = []

                result[store_name].append({
                    "item": item_name,
                    "qty": qty,
                    "sales": sales,
                })

            except Exception:
                continue

        return result

    except Exception as e:
        print("메뉴 TOP 조회 실패:", e)
        return {}

    finally:
        driver.quit()

def fetch_item2_top_sales(acc):

    driver = get_driver()
    result = {}

    try:
        driver.get("https://asp2.unionpos.co.kr")
        time.sleep(2)

        driver.find_element(By.ID, "userId").send_keys(acc["id"])
        driver.find_element(By.ID, "password").send_keys(acc["pw"])
        driver.find_element(By.ID, "btnLogin").click()
        time.sleep(3)

        url = (
            "https://asp2.unionpos.co.kr/v2/sales/product/item2"
            f"?pageNo=1"
            f"&SortMethod="
            f"&SortType="
            f"&SortOrder="
            f"&rangeDate={yesterday}+~+{yesterday}"
            f"&startDate={yesterday}"
            f"&endDate={yesterday}"
            f"&searchType=ItemName"
            f"&searchKeyword="
            f"&codeSearch=CodeSearchName"
            f"&pageSize=100"
        )

        driver.get(url)
        time.sleep(5)

        store_name = "유월의보리 성남신흥점"
        result[store_name] = []

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            values = [cell.text.strip() for cell in cells]

            if len(values) < 5:
                continue

            try:
                # item2 단독매장 기준: 번호 / 상품명 / 수량 / 매출 ... 형태
                if not values[0].isdigit():
                    continue

                item_name = values[1]
                qty = to_int(values[2])
                sales = to_int(values[3])

                if not item_name or sales <= 0:
                    continue

                result[store_name].append({
                    "item": item_name,
                    "qty": qty,
                    "sales": sales,
                })

            except Exception:
                continue

        return result

    except Exception as e:
        print("신흥점 item2 메뉴 TOP 조회 실패:", e)
        return {}

    finally:
        driver.quit()
        
    driver = get_driver()
    result = {}

    try:
        driver.get("https://asp2.unionpos.co.kr")
        time.sleep(2)

        driver.find_element(By.ID, "userId").send_keys(acc["id"])
        driver.find_element(By.ID, "password").send_keys(acc["pw"])
        driver.find_element(By.ID, "btnLogin").click()

        time.sleep(3)

        url = (
            "https://asp2.unionpos.co.kr/v2/sales/product/storeItem"
            f"?pageNo=1"
            f"&rangeDate={yesterday}+~+{yesterday}"
            f"&startDate={yesterday}"
            f"&endDate={yesterday}"
            f"&searchType=ItemName"
            f"&searchKeyword="
            f"&pageSize=100"
        )

        driver.get(url)

        time.sleep(5)

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        for row in rows:

            cells = row.find_elements(By.TAG_NAME, "td")
            values = [cell.text.strip() for cell in cells]

            if len(values) < 5:
                continue

            try:
                store_name = clean_store_name(values[0])
                item_name = values[1]

                qty = to_int(values[2])
                sales = to_int(values[3])

                if sales <= 0:
                    continue

                if store_name not in result:
                    result[store_name] = []

                result[store_name].append({
                    "item": item_name,
                    "qty": qty,
                    "sales": sales,
                })

            except Exception:
                continue

        return result

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

        return {
            "유월의보리 본점": {
                "total_sales": day_data["total_sales"],
                "receipt_count": day_data["receipt_count"],
              "table_price": fmt(round(to_int(day_data["total_sales"]) / to_int(day_data["receipt_count"]))),
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
            time.sleep(5)

            try:
                driver.find_element(
                    By.XPATH,
                    "//a[contains(text(), '최신순')]"
                ).click()

                time.sleep(3)

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

                    review_candidates = card.find_elements(
                        By.CSS_SELECTOR,
                        "a[data-pui-click-code='rvshowless'], a[data-pui-click-code='rvshowmore']"
                    )

                    for review_el in review_candidates:
                        review_text = review_el.text.strip()

                        if not review_text:
                            continue
                        if len(review_text) < 10:
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

    if acc["id"] == "sz77971":
        menu_data = fetch_menu_top_sales(acc)
    elif acc["id"] == "sz83661":
        menu_data = fetch_item2_top_sales(acc)
    else:
        menu_data = {}

    for store_name, items in menu_data.items():

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

    receipt_count_int = int(data["receipt_count"].replace(",", ""))
    table_count = TABLE_COUNTS.get(store_name, 1)
    rotation = round(receipt_count_int / table_count, 1)

    reviews = review_data.get(store_name, [])
    review_text = f"전일 신규리뷰: {len(reviews)}건"

    for idx, review in enumerate(reviews, start=1):
        review_text += f"\n{idx}. {review}"

    menu_text = "메뉴 TOP5: 데이터 없음"

    if store_name in menu_top_data:
        sorted_items = sorted(
            menu_top_data[store_name],
            key=lambda x: x["sales"],
            reverse=True
        )

        sales_int = to_int(data["total_sales"])

        menu_lines = ["메뉴 TOP5"]

        for idx, item in enumerate(sorted_items[:5], start=1):
            ratio = (item["sales"] / sales_int * 100) if sales_int else 0

            menu_lines.append(
                f"{idx}. {item['item']} / {item['qty']}개 / {fmt(item['sales'])}원 / 매출비중 {ratio:.1f}%"
            )

        menu_text = "\n".join(menu_lines)

    report_lines.append(f"""
[{store_name}]
총매출: {data['total_sales']}원
영수건수(회전수): {data['receipt_count']}건 ({rotation}회전)
테이블단가: {data['table_price']}원
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
