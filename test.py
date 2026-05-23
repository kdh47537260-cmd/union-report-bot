from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import requests
import time

BOT_TOKEN = "8886052539:AAGrUs30DNxPsyRtL7RlDHOdeQGSDwV7cUk"

CHAT_IDS = [
    "1490548765",   # 도현
    "8650028323",   # 대표님
    "8960843374",   # 경란님
]

today = datetime.now() + timedelta(hours=9)
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
            print("MENU_ROW:", values)
            
            if len(values) < 4:
                continue

            try:

                if not values[0].isdigit():
                    continue
                store_name = clean_store_name(values[1])
                item_name = values[4]

                qty = to_int(values[5])
                sales = to_int(values[6])

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
            print("ITEM2_ROW:", values)
            
            if len(values) < 6:
                continue

            try:
                # item2 단독매장 기준: 번호 / 상품명 / 수량 / 매출 ... 형태
                if not values[0].isdigit():
                    continue

                item_name = values[3]
                qty = to_int(values[4])
                sales = to_int(values[5])

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

PLACE_IDS = {
    "유월의보리 본점": "1265080366",
    "유월의보리 양재점": "1889387567",
    "유월의보리 신내점": "2021210260",
    "유월의보리 성남신흥점": "2032544088",
}

QUERY = """
query getVisitorReviews($input: VisitorReviewsInput) {
  visitorReviews(input: $input) {
    items {
      body
      created
      businessName
      item { name }
      author { nickname }
    }
    total
  }
}
"""

def fetch_reviews():
    review_data = {}

    for store_name, place_id in PLACE_IDS.items():
        try:
            url = "https://pcmap-api.place.naver.com/graphql"

            headers = {
                "accept": "*/*",
                "accept-language": "ko",
                "content-type": "application/json",
                "origin": "https://pcmap.place.naver.com",
                "referer": f"https://pcmap.place.naver.com/restaurant/{place_id}/review/visitor?reviewSort=recent",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
            }

            payload = [{
                "operationName": "getVisitorReviews",
                "variables": {
                    "input": {
                        "businessId": place_id,
                        "businessType": "restaurant",
                        "item": "0",
                        "bookingBusinessId": place_id,
                        "cidList": ["220036", "220037", "220053"],
                        "getReactions": True,
                        "getTrailer": True,
                        "getUserStats": True,
                        "includeContent": True,
                        "includeReceiptPhotos": True,
                        "isPhotoUsed": False,
                        "size": 30,
                        "sort": "recent",
                    }
                },
                "query": QUERY,
            }]

            res = requests.post(url, headers=headers, json=payload)
            data = res.json()
            items = data[0]["data"]["visitorReviews"]["items"]

            review_texts = []

            for item in items:
                created = item.get("created") or ""
                body = (item.get("body") or "").replace("\n", " ").strip()

                if review_target_date not in created:
                    continue

                if body:
                    review_texts.append(body)

            review_data[store_name] = list(dict.fromkeys(review_texts))
            print("리뷰 수집 완료:", store_name, len(review_data[store_name]), "건")

        except Exception as e:
            print("리뷰 조회 실패:", store_name, e)
            review_data[store_name] = []

    return review_data


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
        
def is_hansang_menu(item_name):
    name = (
        item_name
        .replace(" ", "")
        .replace("&", "")
        .replace("+", "")
        .replace("SET", "")
        .replace("set", "")
        .replace("세트", "")
        .lower()
    )

    return "한상보쌈" in name and "칼국수" in name


def is_plate_menu(item_name):
    name = (
        item_name
        .replace(" ", "")
        .replace("&", "")
        .replace("+", "")
        .replace("SET", "")
        .replace("set", "")
        .replace("세트", "")
        .lower()
    )

    return "접시보쌈" in name and "무김치" in name
    
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

    hansang_text = "한상보쌈&칼국수: 데이터 없음"
    plate_text = "접시보쌈&무김치: 데이터 없음"

    if store_name in menu_top_data:

        hansang_items = [
            item for item in menu_top_data[store_name]
            if is_hansang_menu(item["item"])
        ]

        if hansang_items:
            qty = sum(item["qty"] for item in hansang_items)
            sales = sum(item["sales"] for item in hansang_items)

            hansang_text = f"한상보쌈&칼국수: {qty}개 / {fmt(sales)}원"

        plate_items = [
            item for item in menu_top_data[store_name]
            if is_plate_menu(item["item"])
        ]

        if plate_items:
            qty = sum(item["qty"] for item in plate_items)
            sales = sum(item["sales"] for item in plate_items)

            plate_text = f"접시보쌈&무김치: {qty}개 / {fmt(sales)}원"

    report_lines.append(f"""
[{store_name}]
총매출: {data['total_sales']}원
영수건수(회전수): {data['receipt_count']}건 ({rotation}회전)
테이블단가: {data['table_price']}원
월누적매출: {data['month_sales']}원
{hansang_text}
{plate_text}

{review_text}
""")

report = "\n".join(report_lines)

print(report)

telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

MAX_LEN = 3500

for chat_id in CHAT_IDS:
    for i in range(0, len(report), MAX_LEN):
        chunk = report[i:i + MAX_LEN]

        payload = {
            "chat_id": chat_id,
            "text": chunk
        }

        res = requests.post(telegram_url, data=payload)
        print("텔레그램 응답:", res.status_code, res.text)

print("텔레그램 전송 완료")
