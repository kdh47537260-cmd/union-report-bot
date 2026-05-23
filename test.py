from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import requests
import time
from datetime import datetime, timedelta


today = datetime.now() + timedelta(hours=9)
yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")


def to_int(value):
    return int(str(value).replace(",", "").strip())


def get_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,1000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    return webdriver.Chrome(options=options)


driver = get_driver()

try:
    driver.get("https://nicepay.okpos.co.kr/")
    time.sleep(2)

    driver.find_element(By.ID, "user_id").send_keys("n46083")
    driver.find_element(By.ID, "user_pwd").send_keys("02504")

    driver.execute_script("doSubmit();")
    time.sleep(5)

    # 매출현황 메뉴
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

    # 상품별매출 클릭
    prod_menu = driver.find_element(By.ID, "cswmItem10_59")

    driver.execute_script("""
    arguments[0].dispatchEvent(
        new MouseEvent('click', {
            bubbles:true,
            cancelable:true,
            view:window
        })
    );
    """, prod_menu)

    time.sleep(8)

    print("상품별매출 페이지 진입 완료")

    cookies = driver.get_cookies()

    session = requests.Session()

    for cookie in cookies:
        session.cookies.set(cookie["name"], cookie["value"])

    url = "https://nicepay.okpos.co.kr/sale/sale/ddd.htmlSheetAction"

    headers = {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "ibuseragent": "IBSheet7",
        "origin": "https://nicepay.okpos.co.kr",
        "referer": "https://nicepay.okpos.co.kr/sale/sale/prod011.jsp",
        "x-requested-with": "XMLHttpRequest",
        "user-agent": "Mozilla/5.0",
    }

    payload = {
        "b86a5de7-e89f-4fef-aa28-1d5adae7272b": "dbeacef7-e073-4ca7-932f-62f247ecb476",
        "S_SAVENAME": "sSeq|LCLS_NM|MCLS_NM|SCLS_NM|SALE_DATE|PROD_CD|BAR_CD|MAP_PROD_CD|PROD_NM|VENDORS_NM|COLOR_CD|SIZE_STR_CD|SALE_QTY|PROD_WEIGHT|TOT_SALE_AMT|TOT_DC_AMT|DCM_SALE_AMT|DC_AMT_GEN|DC_AMT_SVC|DC_AMT_JCD|DC_AMT_CPN|DC_AMT_CST|DC_AMT_FOD|DC_AMT_PACK|DC_AMT_YAP|SHOP_CD",
        "ss_CLS_TEXT": "전체",
        "date_period1": "366",
        "S_CONTROLLER": "sale.sale.prod011",
        "S_METHOD": "search",
        "SHEETSEQ": "1",
        "ss_PROD_FG": "N",
        "date1_1": yesterday,
        "date1_2": yesterday,
        "ss_PAGE_SIZE": "100",
        "ss_PAGE_NO1": "1",
    }

    res = session.post(url, headers=headers, data=payload)

    print("STATUS:", res.status_code)
    print("TEXT:", res.text[:1000])

    data = res.json()

    rows = (
        data.get("Data")
        or data.get("data")
        or data.get("SearchData")
        or []
    )

    print("ROW_COUNT:", len(rows))

    for row in rows:

        item_name = row.get("PROD_NM", "")
        qty = to_int(row.get("SALE_QTY", "0"))
        sales = to_int(row.get("DCM_SALE_AMT", "0"))

        if "한상보쌈" in item_name:
            print("한상보쌈:", qty, sales)

        if "접시보쌈" in item_name:
            print("접시보쌈:", qty, sales)

except Exception as e:
    print("에러:", e)

finally:
    driver.quit()
