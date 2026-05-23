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
            time.sleep(8)

            print("현재 URL:", driver.current_url)
            print("페이지 제목:", driver.title)
            print("BODY 일부:", driver.find_element(By.TAG_NAME, "body").text[:500])

            try:
                driver.find_element(
                    By.XPATH,
                    "//a[contains(text(), '최신순')]"
                ).click()

                print("최신순 클릭 완료")
                time.sleep(3)

            except Exception as e:
                print("최신순 클릭 실패:", e)

            last_count = 0
            same_count = 0

            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                more_buttons = driver.find_elements(By.CSS_SELECTOR, "span.TeItc")
                print("더보기 후보 수:", len(more_buttons))

                for btn in more_buttons:
                    try:
                        if "펼쳐서 더보기" in btn.text:
                            driver.execute_script("arguments[0].click();", btn)
                            print("펼쳐서 더보기 클릭")
                            time.sleep(1)
                    except Exception:
                        pass

                cards = driver.find_elements(By.XPATH, "//li[.//time]")
                print("현재 카드 수:", len(cards))

                current_count = 0

                for card in cards:
                    try:
                        date_text = card.find_element(By.TAG_NAME, "time").text.strip()
                        print("DATE_TEXT:", date_text)

                        if review_target_date in date_text:
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

            print("최종 카드 수:", len(cards))

            for card in cards:
                try:
                    date_text = card.find_element(By.TAG_NAME, "time").text.strip()

                    if review_target_date not in date_text:
                        continue

                    review_candidates = card.find_elements(
                        By.CSS_SELECTOR,
                        "a[data-pui-click-code='rvshowless'], a[data-pui-click-code='rvshowmore']"
                    )

                    print("본문 후보 수:", len(review_candidates))

                    for review_el in review_candidates:
                        review_text = review_el.get_attribute("innerText").strip()
                        review_text = review_text.replace("\n", " ").strip()

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

                        print("REVIEW:", review_text)

                        review_texts.append(review_text)
                        break

                except Exception as e:
                    print("카드 파싱 실패:", e)

            review_data[store_name] = list(dict.fromkeys(review_texts))
            print("수집 완료:", store_name, len(review_data[store_name]), "건")

        return review_data

    except Exception as e:
        print("리뷰 조회 실패:", e)
        return review_data

    finally:
        driver.quit()
        
review_data = fetch_reviews()

print("\n\n최종 결과")
print(review_data)
