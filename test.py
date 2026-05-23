from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
import time

today = datetime.now() + timedelta(hours=9)
review_target_date = f"{(today - timedelta(days=1)).month}.{(today - timedelta(days=1)).day}"

REVIEW_URLS = {
    "유월의보리 본점": "https://pcmap.place.naver.com/restaurant/1265080366/review/visitor?reviewSort=recent",
    "유월의보리 양재점": "https://pcmap.place.naver.com/restaurant/1889387567/review/visitor?reviewSort=recent",
    "유월의보리 신내점": "https://pcmap.place.naver.com/restaurant/2021210260/review/visitor?reviewSort=recent",
    "유월의보리 성남신흥점": "https://pcmap.place.naver.com/restaurant/2032544088/review/visitor?reviewSort=recent",
}

def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,1000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    return webdriver.Chrome(options=options)

def fetch_reviews():
    driver = get_driver()
    review_data = {}

    try:
        for store_name, url in REVIEW_URLS.items():
            print("\n==============================")
            print("리뷰 조회 시작:", store_name)
            print("리뷰 대상 날짜:", review_target_date)

            driver.get(url)
            time.sleep(7)

            print("현재 URL:", driver.current_url)
            print("페이지 제목:", driver.title)

            try:
                latest_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), '최신순')]")
                print("최신순 버튼 수:", len(latest_buttons))

                for btn in latest_buttons:
                    try:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click();", btn)
                            print("최신순 클릭 완료")
                            time.sleep(4)
                            break
                    except Exception:
                        pass

            except Exception as e:
                print("최신순 클릭 실패:", e)

            for i in range(10):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                cards = driver.find_elements(By.XPATH, "//li[.//time]")
                print(f"스크롤 {i + 1}회 / 카드 수:", len(cards))

                try:
                    more_buttons = driver.find_elements(
                        By.XPATH,
                        "//*[contains(text(), '펼쳐서 더보기') or contains(text(), '더보기')]"
                    )

                    print("더보기 버튼 수:", len(more_buttons))

                    for btn in more_buttons:
                        try:
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                time.sleep(0.5)
                        except Exception:
                            pass

                except Exception:
                    pass

            cards = driver.find_elements(By.XPATH, "//li[.//time]")
            print("최종 카드 수:", len(cards))

            review_texts = []

            for card in cards:
                try:
                    date_text = card.find_element(By.TAG_NAME, "time").text.strip()
                    print("DATE_TEXT:", date_text)

                    if review_target_date not in date_text:
                        continue

                    text = card.text.strip()
                    lines = [line.strip() for line in text.split("\n") if line.strip()]

                    print("CARD_LINES:", lines[:8])

                    for line in lines:
                        if len(line) < 10:
                            continue
                        if review_target_date in line:
                            continue
                        if "리뷰" in line and "사진" in line:
                            continue
                        if "팔로우" in line:
                            continue
                        if "개의 리뷰" in line:
                            continue
                        if "반응 남기기" in line:
                            continue
                        if "방문예약" in line:
                            continue
                        if "대기 시간" in line:
                            continue
                        if line.startswith("+"):
                            continue

                        print("REVIEW:", line)
                        review_texts.append(line)
                        break

                except Exception as e:
                    print("카드 파싱 실패:", e)

            review_data[store_name] = list(dict.fromkeys(review_texts))
            print("수집 완료:", store_name, len(review_data[store_name]), "건")

        return review_data

    finally:
        driver.quit()

review_data = fetch_reviews()

print("\n\n최종 결과")
print(review_data)
