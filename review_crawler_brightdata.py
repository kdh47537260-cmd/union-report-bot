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

# 매장명이 다르면 이름만 수정하세요. 네이버 플레이스 ID는 어제 사용한 값입니다.
PLACE_IDS = {
    "유월의보리 본점": "1265080366",
    "유월의보리 양재점": "1889387567",
    "유월의보리 신내점": "2021210260",
    "유월의보리 성남점": "2032544088",
    "유월의보리 방배점": "2063717777",
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


def kst_now():
    return datetime.now(timezone(timedelta(hours=9)))


def require_settings():
    if not BRIGHTDATA_API_KEY:
        raise RuntimeError(
            "BRIGHTDATA_API_KEY 환경변수가 없습니다. "
            "새 API 키를 환경변수로 설정한 뒤 다시 실행하세요."
        )


def decode_unlocker_response(response):
    response_text = response if isinstance(response, str) else str(response)
    try:
        data = json.loads(response_text)
    except ValueError as exc:
        preview = response_text[:500].replace("\n", " ")
        raise RuntimeError(f"Bright Data 응답이 JSON이 아닙니다: {preview}") from exc

    # 일부 설정에서는 원본 응답이 body 안에 들어옵니다.
    if isinstance(data, dict) and "body" in data:
        body = data["body"]
        if isinstance(body, str):
            try:
                return json.loads(body)
            except ValueError as exc:
                preview = body[:500].replace("\n", " ")
                raise RuntimeError(f"대상 응답이 JSON이 아닙니다: {preview}") from exc
        return body

    return data


def fetch_reviews(store_name, place_id, size=30):
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
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),
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
            status = response.status
            response_text = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        status = exc.code
        response_text = exc.read().decode("utf-8", errors="replace")
    except error.URLError as exc:
        raise RuntimeError(f"Bright Data 연결 실패: {exc}") from exc

    if status != 200:
        preview = response_text[:500].replace("\n", " ")
        raise RuntimeError(f"Bright Data 요청 실패: status={status}, response={preview}")

    data = decode_unlocker_response(response_text)

    try:
        result = data[0]
        if result.get("errors"):
            messages = [error.get("message", str(error)) for error in result["errors"]]
            raise RuntimeError("GraphQL 오류: " + " / ".join(messages))
        visitor_reviews = result["data"]["visitorReviews"]
        items = visitor_reviews.get("items") or []
        total = visitor_reviews.get("total")
    except (KeyError, IndexError, TypeError) as exc:
        preview = json.dumps(data, ensure_ascii=False)[:1000]
        raise RuntimeError(f"리뷰 응답 구조가 예상과 다릅니다: {preview}") from exc

    reviews = []
    for item in items:
        body = re.sub(r"\s+", " ", item.get("body") or "").strip()
        if not body:
            continue

        author = item.get("author") or {}
        menu_item = item.get("item") or {}
        reviews.append(
            {
                "created": item.get("created") or "",
                "body": body,
                "author": author.get("nickname") or "",
                "menu": menu_item.get("name") or "",
                "business_name": item.get("businessName") or store_name,
            }
        )

    print(f"[{store_name}] 최근 리뷰 {len(reviews)}건 수집 / 전체 {total}")
    return reviews


def is_target_date(created, target_date):
    if not created:
        return False

    candidates = {
        target_date.strftime("%Y-%m-%d"),
        target_date.strftime("%Y.%m.%d"),
        f"{target_date.month}.{target_date.day}",
    }
    return any(value in created for value in candidates)


def build_report(target_date=None, review_size=30):
    now = kst_now()
    if target_date is None:
        target_date = (now - timedelta(days=1)).date()

    lines = [
        "[네이버 플레이스 리뷰 보고]",
        f"실행시각: {now.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"대상일자: {target_date.isoformat()}",
        "",
    ]

    for store_name, place_id in PLACE_IDS.items():
        lines.append(f"[{store_name}]")
        try:
            reviews = fetch_reviews(store_name, place_id, size=review_size)
            daily_reviews = [
                review for review in reviews
                if is_target_date(review["created"], target_date)
            ]

            lines.append(f"최근 리뷰 조회: 성공 ({len(reviews)}건)")
            lines.append(f"전일 신규 리뷰: {len(daily_reviews)}건")

            for index, review in enumerate(daily_reviews[:10], start=1):
                author = f" / {review['author']}" if review["author"] else ""
                lines.append(
                    f"{index}. {review['body']} ({review['created']}{author})"
                )
        except Exception as exc:
            lines.append("최근 리뷰 조회: 실패")
            lines.append(f"사유: {exc}")

        lines.append("")

    return "\n".join(lines).strip()


def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("텔레그램 설정이 없어 전송은 생략합니다.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    for chat_id in TELEGRAM_CHAT_IDS:
        for start in range(0, len(text), 3500):
            payload = parse.urlencode(
                {"chat_id": chat_id, "text": text[start:start + 3500]}
            ).encode("utf-8")
            telegram_request = request.Request(
                url,
                data=payload,
                method="POST",
            )
            try:
                with request.urlopen(telegram_request, timeout=30) as response:
                    response.read()
            except error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:300]
                raise RuntimeError(
                    f"텔레그램 전송 실패: status={exc.code}, response={body}"
                ) from exc


def main():
    parser = argparse.ArgumentParser(
        description="Bright Data를 이용한 네이버 플레이스 일일 리뷰 수집"
    )
    parser.add_argument(
        "--date",
        help="기준일자(YYYY-MM-DD). 생략하면 전일을 사용합니다.",
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="수집 결과를 텔레그램으로 전송합니다.",
    )
    args = parser.parse_args()
    require_settings()

    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise SystemExit("--date는 YYYY-MM-DD 형식이어야 합니다.") from exc
    else:
        target_date = (kst_now() - timedelta(days=1)).date()

    # 매장별 최신 30건만 요청한 뒤 기준일자와 일치하는 리뷰만 보고합니다.
    report = build_report(target_date=target_date, review_size=30)
    print("\n" + report)

    if args.telegram:
        send_telegram(report)


if __name__ == "__main__":
    main()


