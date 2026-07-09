from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import calendar
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
days_elapsed = (today - timedelta(days=1)).day
days_in_month = calendar.monthrange(today.year, today.month)[1]
last_week_same_day = (
    today - timedelta(days=8)
).strftime("%Y-%m-%d")

union_accounts = [
    {"id": "sz77971", "pw": "04(1)"},
    {"id": "sz83661", "pw": "02506"},
    {"id": "sz86521", "pw": "03816"},
]

store_order = [
    "유월의보리 본점",
    "유월의보리 양재점",
    "유월의보리 신내점",
    "유월의보리 성남신흥점",
    "유월의보리 방배점",
]

TABLE_COUNTS = {
    "유월의보리 본점": 14,
    "유월의보리 양재점": 18,
    "유월의보리 신내점": 10,
    "유월의보리 성남신흥점": 14,
    "유월의보리 방배점": 16,
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

    if "방배" in name:
        return "유월의보리 방배점"

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
            time.sleep(10)

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
        last_week_data = search_period(last_week_same_day, last_week_same_day, mode="day")
        month_data = search_period(month_start, yesterday, mode="month")

        for store_name, day in day_data.items():
            result[store_name] = {
                "total_sales": day["total_sales"],
                "receipt_count": day["receipt_count"],
                "table_price": day["table_price"],
                "month_sales": month_data.get(store_name, {}).get("total_sales", "0"),
                "last_week_sales": last_week_data.get(store_name, {}).get("total_sales", "0"),
            }

        return result

    except Exception as e:
        print("UnionPOS 조회 실패:", e)
        return result

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

            total_sales = driver.find_elements(By.CSS_SELECTOR, "td.HideCol0C5")[-1].text.strip()
            receipt_count = driver.find_elements(By.CSS_SELECTOR, "td.HideCol0C10")[-1].text.strip()
            table_price = driver.find_elements(By.CSS_SELECTOR, "td.HideCol0C11")[-1].text.strip()

            return {
                "total_sales": total_sales,
                "receipt_count": receipt_count,
                "table_price": table_price,
            }

        day_data = search_period(yesterday, yesterday)

        time.sleep(6)

        last_week_data = search_period(last_week_same_day, last_week_same_day)

        time.sleep(6)

        month_data = search_period(month_start, yesterday)

        return {
            "유월의보리 본점": {
                "total_sales": day_data["total_sales"],
                "receipt_count": day_data["receipt_count"],
                "table_price": fmt(round(to_int(day_data["total_sales"]) / to_int(day_data["receipt_count"]))),
                "month_sales": month_data["total_sales"],
                "last_week_sales": last_week_data["total_sales"],
            }
        }

    except Exception as e:
        print("OKPOS 조회 실패:", e)
        return {}

    finally:
        driver.quit()

all_store_data = {}

all_store_data.update(fetch_okpos())

for acc in union_accounts:
    all_store_data.update(fetch_unionpos_account(acc))

report_lines = [
    "[유월의보리 일매출 리포트]",
    f"조회일자: {yesterday}",
    ""
]

for store_name in store_order:
    data = all_store_data.get(store_name)

    if not data:
        report_lines.append(f"""
[{store_name}]
조회 실패 또는 데이터 없음
""")
        continue

    receipt_count_int = int(data["receipt_count"].replace(",", ""))
    table_count = TABLE_COUNTS.get(store_name, 1)
    rotation = round(receipt_count_int / table_count, 1)

    yesterday_sales_int = to_int(data["total_sales"])
    last_week_sales_int = to_int(data.get("last_week_sales", "0"))

    if last_week_sales_int > 0:
        wow_rate = round(
            (yesterday_sales_int - last_week_sales_int)
            / last_week_sales_int * 100,
            1
        )
        wow_text = f"{wow_rate:+}%"
    else:
        wow_text = "비교불가"

    month_sales_int = to_int(data["month_sales"])

    avg_daily_sales_int = round(month_sales_int / days_elapsed)
    expected_month_sales_int = avg_daily_sales_int * days_in_month

    avg_daily_sales = fmt(avg_daily_sales_int)
    expected_month_sales = fmt(expected_month_sales_int)

    report_lines.append(f"""
[{store_name}]
총매출: {data['total_sales']}원
영수건수(회전수): {data['receipt_count']}건 ({rotation}회전)
테이블단가: {data['table_price']}원
증감률(-1W): {wow_text}

월누적매출: {data['month_sales']}원
일평균매출: {avg_daily_sales}원
월예상매출: {expected_month_sales}원
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
