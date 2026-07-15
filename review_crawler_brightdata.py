import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib import error, parse, request


BRIGHTDATA_API_URL = "https://api.brightdata.com/request"
BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY", "").strip()
BRIGHTDATA_ZONE = os.getenv("BRIGHTDATA_ZONE", "web_unlocker1").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_IDS = [
    value.strip()
    for value in os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
    if value.strip()
]

# 이 선언 순서가 수집 및 텔레그램 보고 순서입니다.
PLACE_IDS = {
    "유월의보리 방배점": "2063717777",
    "유월의보리 성남신흥점": "2032544088",
    "유월의보리 양재점": "1889387567",
    "유월의보리 본점": "1265080366",
    "유월의보리 신내점": "2021210260",
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
    return datetime.now(timezone(timedelta(hours=9)))


def require_settings():
    if not BRIGHTDATA_API_KEY:
        raise RuntimeError("BRIGHTDATA_API_KEY 환경변수가 없습니다.")


def decode_unlocker_response(response_text):
    try:
        data = json.loads(response_text)
    except ValueError as exc:
        raise RuntimeError("Bright Data 응답이 JSON이 아닙니다.") from exc

    if isinstance(data, dict) and "body" in data:
        body = data["body"]
        if isinstance(body, str):
            try:
                return json.loads(body)
            except ValueError as exc:
                raise RuntimeError("대상 사이트 응답이 JSON이 아닙니다.") from exc
        return body
    return data


def fetch_reviews(store_name, place_id):
    target_url = "https://pcmap-api.place.naver.com/graphql"
    place_url = (
        f"https://pcmap.place.naver.com/restaurant/{place_id}"
        "/review/visitor?reviewSort=recent"
    )
    graphql_payload = [
        {
            "operationName": "getVisitorReviews",
            "variables": {
                "input": {
                    "businessId": str(place_id),
                    "businessType": "restaurant",
                    "item": "0",
                    "bookingBusinessId": str(place_id),
                    "cidList": ["220036", "220037", "220053"],
                    "getReactions": False,
                    "getTrailer": False,
                    "getUserStats": False,
                    "includeContent": True,
                    "includeReceiptPhotos": False,
                    "isPhotoUsed": False,
                    "size": 30,
                    "sort": "recent",
                }
            },
            "query": QUERY,
        }
    ]
    unlocker_payload = {
        "zone": BRIGHTDATA_ZONE,
        "url": target_url,
        "format": "raw",
        "method": "POST",
        "country": "kr",
        "headers": {
            "accept": "*/*",
            "accept-language": "ko-KR,ko;q=0.9",
            "content-type": "application/json",
            "origin": "https://pcmap.place.naver.com",
            "referer": place_url,
            "user-agent": "Mozilla/5.0 Chrome/138.0.0.0 Safari/537.36",
        },
        "body": json.dumps(graphql_payload, ensure_ascii=False),
    }
    api_request = request.Request(
        BRIGHTDATA_API_URL,
        data=json.dumps(unlocker_payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(api_request, timeout=120) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        preview = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Bright Data 요청 실패({exc.code}): {preview}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Bright Data 연결 실패: {exc}") from exc

    data = decode_unlocker_response(response_text)
    try:
        result = data[0]
        if result.get("errors"):
            messages = [item.get("message", str(item)) for item in result["errors"]]
            raise RuntimeError("GraphQL 오류: " + " / ".join(messages))
        items = result["data"]["visitorReviews"].get("items") or []
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("리뷰 응답 구조가 예상과 다릅니다.") from exc

    reviews = []
    for item in items[:30]:
        body = re.sub(r"\s+", " ", item.get("body") or "").strip()
        created = str(item.get("created") or "").strip()
        if body and created:
            reviews.append({"body": body, "created": created})
    print(f"[{store_name}] 최신 {len(items[:30])}건 응답, 유효 {len(reviews)}건")
    return reviews


def is_target_date(created, target_date):
    candidates = {
        target_date.strftime("%Y-%m-%d"),
        target_date.strftime("%Y.%m.%d"),
        f"{target_date.month}.{target_date.day}",
    }
    return any(value in created for value in candidates)


def build_report(target_date=None):
    now = kst_now()
    target_date = target_date or (now - timedelta(days=1)).date()
    lines = [
        "[네이버 플레이스 리뷰 보고]",
        f"실행시각: {now.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"조회기준: {target_date.isoformat()}",
        "요청범위: 매장별 최신 30건",
        "",
    ]

    for store_name, place_id in PLACE_IDS.items():
        lines.append(f"[{store_name}]")
        try:
            reviews = fetch_reviews(store_name, place_id)
            daily_reviews = [
                review
                for review in reviews
                if is_target_date(review["created"], target_date)
            ]
            lines.append(f"조회기준일 리뷰: {len(daily_reviews)}건")
            for index, review in enumerate(daily_reviews, start=1):
                lines.append(f"{index}. {review['body']} ({review['created']})")
            if not daily_reviews:
                lines.append("해당 날짜에 작성된 리뷰 없음")
        except Exception as exc:
            lines.extend(["리뷰 조회 실패", f"사유: {exc}"])
        lines.append("")
    return "\n".join(lines).strip()


def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("텔레그램 설정이 없어 전송을 생략합니다.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        for start in range(0, len(text), 3500):
            payload = parse.urlencode(
                {"chat_id": chat_id, "text": text[start:start + 3500]}
            ).encode("utf-8")
            telegram_request = request.Request(url, data=payload, method="POST")
            try:
                with request.urlopen(telegram_request, timeout=30) as response:
                    response.read()
            except error.HTTPError as exc:
                raise RuntimeError(f"텔레그램 전송 실패: {exc.code}") from exc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="조회기준일(YYYY-MM-DD), 생략하면 전일")
    parser.add_argument("--telegram", action="store_true")
    args = parser.parse_args()
    require_settings()
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise SystemExit("--date는 YYYY-MM-DD 형식이어야 합니다.") from exc
    else:
        target_date = (kst_now() - timedelta(days=1)).date()
    report = build_report(target_date)
    print("\n" + report)
    if args.telegram:
        send_telegram(report)


if __name__ == "__main__":
    main()
