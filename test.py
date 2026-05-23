from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from datetime import datetime, timedelta

import time


today = datetime.now() + timedelta(hours=9)
yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")


def get_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")

    driver = webdriver.Chrome(options=options)

    return driver


def switch_to_frame_containing_element(driver, element_id):
    driver.switch_to.default_content()

    # 현재 페이지 확인
    if driver.find_elements(By.ID, element_id):
        return True

    # iframe 전체 탐색
    frames = driver.find_elements(By.TAG_NAME, "iframe")

    print("FRAME_COUNT:", len(frames))

    for idx, frame in enumerate(frames):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)

            print(f"FRAME_CHECK: {idx}")

            if driver.find_elements(By.ID, element_id):
                print(f"FOUND_FRAME: {idx}")
                return True

        except Exception as e:
            print("FRAME_ERROR:", e)

    driver.switch_to.default_content()

    return False


def fetch_okpos_menu_sales():
    driver = get_driver()

    try:
        driver.get("https://nicepay.okpos.co.kr/")

        time.sleep(2)

        print("OKPOS 접속 완료")

        # 로그인
        driver.find_element(By.ID, "user_id").send_keys("n46083")
        driver.find_element(By.ID, "user_pwd").send_keys("02504")

        driver.execute_script("doSubmit();")

        time.sleep(5)

        print("로그인 완료")

        # 매출관리 메뉴 오픈
        driver.execute_script("""
        cswmButtonSelect('cswmMenuButtonGroup_15', 'Group_15');
        cswmButtonDown('cswmMenuButtonGroup_15', 'Group_15');
        """)

        time.sleep(2)

        print("매출관리 메뉴 오픈")

        # 매출현황 hover
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

        print("매출현황 hover 완료")

        # 상품별매출 클릭
        product_menu = driver.find_element(By.ID, "cswmItem10_56")

        driver.execute_script("""
        arguments[0].dispatchEvent(
            new MouseEvent('click', {
                bubbles:true,
                cancelable:true,
                view:window
            })
        );
        """, product_menu)

        print("상품별매출 클릭 완료")

        # iframe 생성 대기
        found = False

        for i in range(20):
            time.sleep(1)

            driver.switch_to.default_content()

            found = switch_to_frame_containing_element(driver, "date1_1")

            print(f"FRAME TRY: {i+1}")

            if found:
                break

        if not found:
            print("프레임 못찾음")

            print("현재 URL:", driver.current_url)
            print("현재 TITLE:", driver.title)

            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print("IFRAME_COUNT:", len(iframes))

            return {}

        print("프레임 진입 성공")

        # 날짜 입력
        driver.execute_script(f"""
        document.getElementById('date1_1').removeAttribute('readonly');
        document.getElementById('date1_1').value = '{yesterday}';

        document.getElementById('date1_2').removeAttribute('readonly');
        document.getElementById('date1_2').value = '{yesterday}';
        """)

        time.sleep(1)

        print("날짜 입력 완료")

        # 조회
        driver.execute_script("fnSearch();")

        time.sleep(8)

        print("조회 완료")

        rows = driver.find_elements(By.CSS_SELECTOR, "tr")

        print("ROW_COUNT:", len(rows))

        target_items = [
            "한상보쌈+바지락칼국수",
            "접시보쌈&보쌈무김치"
        ]

        result = {}

        for row in rows:
            cols = [
                c.text.strip()
                for c in row.find_elements(By.TAG_NAME, "td")
            ]

            if len(cols) < 7:
                continue

            try:
                print("COLS:", cols)

                item_name = cols[3]
                qty = cols[5]
                sales = cols[6]

                if item_name in target_items:
                    result[item_name] = {
                        "qty": qty,
                        "sales": sales
                    }

                    print("MATCH:", item_name, qty, sales)

            except Exception as e:
                print("PARSE_ERROR:", cols, e)

        return result

    except Exception as e:
        print("OKPOS 상품별매출 조회 실패:", e)
        return {}

    finally:
        driver.quit()


print(fetch_okpos_menu_sales())
