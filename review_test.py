from datetime import datetime, timedelta
import http.cookiejar
import json
import os
import random
import time
from urllib import parse, request
from urllib.error import HTTPError, URLError


BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "8886052539:AAGrUs30DNxPsyRtL7RlDHOdeQGSDwV7cUk",
)

CHAT_IDS = [
    "1490548765",   # 도현
]

PLACE_IDS = {
    "유월의보리 양재점": "1889387567",
    "유월의보리 본점": "1265080366",
    "유월의보리 신내점": "2021210260",
    "유월의보리 성남신흥점": "2032544088",
}

QUERY = """
query getVisitorReviews($input: VisitorReviewsInput) {
  visitorReviews(input: $input) {
    items {
      body
      created
    }
  }
}
"""


def kst_now():
    return datetime.utcnow() + timedelta(hours=9)


def fetch_reviews(store_name, place_id, size=20):
    url = "https://pcmap-api.place.naver.com/graphql"
    place_url = f"https://pcmap.place.naver.com/restaurant/{place_id}/review/visitor?reviewSort=recent"
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
    )

    headers = {
        "accept": "*/*",
        "accept-language": "ko",
        "content-type": "application/json",
        "origin": "https://pcmap.place.naver.com",
        "referer": place_url,
        "user-agent": user_agent,
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
                "size": size,
                "sort": "recent",
            }
        },
        "query": QUERY,
    }]

    last_error = None
    cookie_jar = http.cookiejar.CookieJar()
    opener = request.build_opener(request.HTTPCookieProcessor(cookie_jar))

    for attempt in range(1, 3):
        if attempt > 1:
            delay = random.uniform(20, 45)
            print("리뷰 재시도 대기:", store_name, attempt, f"{delay:.1f}초")
            time.sleep(delay)

        try:
            page_req = request.Request(
                place_url,
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                    "referer": "https://pcmap.place.naver.com/",
                    "user-agent": user_agent,
                },
            )
            opener.open(page_req, timeout=20).read()
        except Exception as e:
            print("리뷰 페이지 선방문 실패:", store_name, e)

        try:
            body = json.dumps(payload).encode("utf-8")
            api_req = request.Request(url, data=body, headers=headers, method="POST")
            with opener.open(api_req, timeout=20) as response:
                status = response.status
                content_type = response.headers.get("content-type", "")
                response_text = response.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            status = e.code
            content_type = e.headers.get("content-type", "")
            response_text = e.read().decode("utf-8", errors="replace")
        except (URLError, TimeoutError, OSError) as e:
            last_error = e
            print("리뷰 API 요청 실패:", store_name, e)
            continue

        preview = response_text[:200].replace("\n", " ").strip()

        if (
            status != 200
            or not response_text.strip()
            or not response_text.lstrip().startswith(("[", "{"))
        ):
            if "captcha" in response_text.lower() or "wtm_captcha" in response_text.lower():
                reason = "네이버 캡차/봇 차단"
            elif not response_text.strip():
                reason = "빈 응답"
            else:
                reason = "JSON이 아닌 응답"

            last_error = ValueError(
                f"{reason} attempt={attempt} status={status} "
                f"content_type={content_type} preview={preview}"
            )
            print("리뷰 응답 비정상:", store_name, last_error)
            continue

        try:
            data = json.loads(response_text)
        except ValueError:
            last_error = ValueError(
                f"JSON 파싱 실패 attempt={attempt} status={status} "
                f"content_type={content_type} preview={preview}"
            )
            print("리뷰 JSON 파싱 실패:", store_name, last_error)
            continue

        items = data[0]["data"]["visitorReviews"]["items"]
        return [
            {
                "created": item.get("created") or "",
                "body": (item.get("body") or "").replace("\n", " ").strip(),
            }
            for item in items
            if (item.get("body") or "").strip()
        ]

    raise last_error or ValueError("리뷰 조회 실패")


def build_report():
    today = kst_now()
    yesterday = today - timedelta(days=1)
    target_date = f"{yesterday.month}.{yesterday.day}"

    lines = [
        "[네이버 플레이스 리뷰 테스트]",
        f"실행시각: {today.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"전일 기준: {yesterday.strftime('%Y-%m-%d')}",
        "",
    ]

    for store_name, place_id in PLACE_IDS.items():
        try:
            reviews = fetch_reviews(store_name, place_id)
            yesterday_reviews = [
                review["body"]
                for review in reviews
                if target_date in review["created"]
            ]

            lines.append(f"[{store_name}]")
            lines.append(f"최근 리뷰 조회: 성공 ({len(reviews)}건)")
            lines.append(f"전일 신규리뷰: {len(yesterday_reviews)}건")

            for idx, review in enumerate(yesterday_reviews[:10], start=1):
                lines.append(f"{idx}. {review}")

        except Exception as e:
            lines.append(f"[{store_name}]")
            lines.append("최근 리뷰 조회: 실패")
            lines.append(f"사유: {e}")

        lines.append("")

    return "\n".join(lines).strip()


def send_telegram(text):
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    max_len = 3500

    for chat_id in CHAT_IDS:
        for i in range(0, len(text), max_len):
            chunk = text[i:i + max_len]
            payload = parse.urlencode({
                "chat_id": chat_id,
                "text": chunk,
            }).encode("utf-8")
            telegram_req = request.Request(telegram_url, data=payload, method="POST")

            with request.urlopen(telegram_req, timeout=20) as response:
                response_text = response.read().decode("utf-8", errors="replace")
                print("텔레그램 응답:", response.status, response_text)


if __name__ == "__main__":
    report = build_report()
    print(report)
    send_telegram(report)
