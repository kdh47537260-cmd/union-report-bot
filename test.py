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

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    print("ROW_COUNT:", len(rows))

    for row in rows:

        cells = row.find_elements(By.TAG_NAME, "td")
        values = [cell.text.strip() for cell in cells]

        print("ROW:", values)

        if len(values) < 10:
            continue

        try:
            item_name = values[8]
            qty = to_int(values[12])
            sales = to_int(values[16])

            if "한상보쌈" in item_name:
                print("한상보쌈:", qty, sales)

            if "접시보쌈" in item_name:
                print("접시보쌈:", qty, sales)

        except Exception as e:
            print("PARSE_ERROR:", e)

except Exception as e:
    print("에러:", e)

finally:
    driver.quit()
