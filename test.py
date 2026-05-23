from datetime import datetime, timedelta
import requests

today = datetime.now() + timedelta(hours=9)
review_target_date = f"{(today - timedelta(days=1)).month}.{(today - timedelta(days=1)).day}"

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
      item {
        name
      }
      author {
        nickname
      }
    }
    total
  }
}
"""

def fetch_reviews():

    review_data = {}

    for store_name, place_id in PLACE_IDS.items():

        print("\n==============================")
        print("리뷰 조회 시작:", store_name)

        url = "https://pcmap-api.place.naver.com/graphql"

        headers = {
            "accept": "*/*",
            "accept-language": "ko",
            "content-type": "application/json",
            "origin": "https://pcmap.place.naver.com",
            "referer": f"https://pcmap.place.naver.com/restaurant/{place_id}/review/visitor?reviewSort=recent",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
        }

        payload = [
            {
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
            }
        ]

        try:
            res = requests.post(url, headers=headers, json=payload)

            print("STATUS:", res.status_code)

            data = res.json()

            items = data[0]["data"]["visitorReviews"]["items"]

            review_texts = []

            for item in items:

                created = item.get("created") or ""
                body = (item.get("body") or "").replace("\n", " ").strip()

                if review_target_date not in created:
                    continue

                if not body:
                    continue

                print("REVIEW:", body)

                review_texts.append(body)

            review_data[store_name] = list(dict.fromkeys(review_texts))

            print(
                "수집 완료:",
                store_name,
                len(review_data[store_name]),
                "건"
            )

        except Exception as e:
            print("리뷰 조회 실패:", store_name, e)
            review_data[store_name] = []

    return review_data
    
review_data = fetch_reviews()
print(review_data)
