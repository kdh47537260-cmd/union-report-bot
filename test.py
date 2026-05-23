import requests
from datetime import datetime, timedelta

today = datetime.now() + timedelta(hours=9)
yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

TARGET_ITEMS = [
    "한상보쌈+바지락칼국수",
    "접시보쌈&보쌈무김치",
]

def fetch_okpos_menu_sales_api():
    url = "https://nicepay.okpos.co.kr/sale/sale/ddd.htmlSheetAction"

    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "IBUserAgent": "IBSheet7",
        "Origin": "https://nicepay.okpos.co.kr",
        "Referer": "https://nicepay.okpos.co.kr/sale/sale/prod011.jsp",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0",
        "Cookie": "JSESSIONID=95BA9E6E752016C718811CD647923926; cooMenuHV=H; date1_1=2026-05-23; date1_2=2026-05-23",
    }

    payload = {
        "S_CONTROLLER": "sale.sale.prod011",
        "S_METHOD": "search",
        "SHEETSEQ": "1",
        "S_SAVENAME": "sSeq|LCLS_NM|MCLS_NM|SCLS_NM|SALE_DATE|PROD_CD|BAR_CD|MAP_PROD_CD|PROD_NM|VENDORS_NM|COLOR_CD|SIZE_STR_CD|SALE_QTY|PROD_WEIGHT|TOT_SALE_AMT|TOT_DC_AMT|DCM_SALE_AMT|DC_AMT_GEN|DC_AMT_SVC|DC_AMT_JCD|DC_AMT_CPN|DC_AMT_CST|DC_AMT_FOD|DC_AMT_PACK|DC_AMT_YAP|SHOP_CD",
        "S_ORDERBY": "",
        "ss_PROD_FG": "N",
        "date1_1": yesterday,
        "date1_2": yesterday,
        "date_period1": "366",
        "ss_PROD_CD": "",
        "ss_PROD_NM": "",
        "ss_LCLS_CD": "",
        "ss_MCLS_CD": "",
        "ss_SCLS_CD": "",
        "ss_SIZE_CLS_CD": "",
        "ss_CLS_TEXT": "전체",
        "ss_BAR_CD": "",
        "ss_VENDOR_CD": "",
        "ss_VENDOR_NM": "전체",
        "ss_VENDOR_INFO": "[]",
        "ss_PAGE_SIZE": "100",
        "ss_PAGE_NO1": "1",
    }

    res = requests.post(url, headers=headers, data=payload, timeout=20)

    print("STATUS:", res.status_code)
    print("TEXT_LEN:", len(res.text))
    print("TEXT_HEAD:", repr(res.text[:1000]))

    data = res.json()

    print("DATA_KEYS:", data.keys())
    print("DATA_COUNT:", len(data.get("Data", [])))

    result = {}

    for row in data.get("Data", []):
        print(row.get("PROD_NM"), row.get("SALE_QTY"), row.get("TOT_SALE_AMT"))

        name = row.get("PROD_NM")

        if name in TARGET_ITEMS:
            result[name] = {
                "qty": row.get("SALE_QTY", "0"),
                "sales": f'{int(row.get("TOT_SALE_AMT", 0)):,}',
            }

    return result


print(fetch_okpos_menu_sales_api())
