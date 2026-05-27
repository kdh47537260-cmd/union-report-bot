import os
import requests
import pandas as pd

MASTER_FILE = "유월의보리_product_master.xlsx"
ERP_FILE = "erp_sales.xlsx"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TELEGRAM_CHAT_IDS = [
    "1490548765",   # 도현
]

def to_number(value):
    if pd.isna(value):
        return 0
    return float(str(value).replace(",", "").strip())


def run_monthly_logistics_report():

    master = pd.read_excel(
        MASTER_FILE,
        sheet_name="PRODUCT_MASTER"
    )

    erp = pd.read_excel(
        ERP_FILE,
        sheet_name="판매현황",
        header=1
    )

    erp.columns = erp.columns.str.strip()
    master.columns = master.columns.str.strip()

    erp = erp[
        erp["품목코드"].notna()
    ]

    erp["거래처명"] = erp["거래처명"].replace({
        "유월의 보리(신내점)": "유월의 보리 신내점"
    })

    master["품목코드"] = master["품목코드"].astype(str).str.strip()
    erp["품목코드"] = erp["품목코드"].astype(str).str.strip()

    master = master[
        master["사용여부"].astype(str).str.upper() == "Y"
    ]

    cost_map = dict(
        zip(
            master["품목코드"],
            master["제조원가(입력)"]
        )
    )

    erp["수량"] = erp["수량"].apply(to_number)
    erp["공급가액"] = erp["공급가액"].apply(to_number)

    erp["제조원가_단가"] = erp["품목코드"].map(cost_map)
    missing = erp[erp["제조원가_단가"].isna()][["품목코드", "품목명(규격)"]].drop_duplicates()

    erp["총제조원가"] = erp["수량"] * erp["제조원가_단가"].fillna(0)
    erp["물류이익"] = erp["공급가액"] - erp["총제조원가"]

    store_report = (
        erp.groupby("거래처명")
        .agg(
            본사공급액=("공급가액", "sum"),
            총제조원가=("총제조원가", "sum"),
            물류이익=("물류이익", "sum"),
        )
        .reset_index()
    )

    store_report["물류이익률"] = store_report["물류이익"] / store_report["본사공급액"].replace(0, pd.NA)

    sku_report = (
        erp.groupby(["거래처명", "품목코드", "품목명(규격)"])
        .agg(
            수량=("수량", "sum"),
            공급가액=("공급가액", "sum"),
            총제조원가=("총제조원가", "sum"),
            물류이익=("물류이익", "sum"),
        )
        .reset_index()
    )

    sku_report["물류이익률"] = sku_report["물류이익"] / sku_report["공급가액"].replace(0, pd.NA)

    lines = []

    total_supply = store_report["본사공급액"].sum()
    total_cost = store_report["총제조원가"].sum()
    total_profit = store_report["물류이익"].sum()
    total_margin = total_profit / total_supply if total_supply != 0 else 0

    lines.append(f"""
[월말 물류이익 리포트]

전체 본사공급액: {total_supply:,.0f}원
전체 제조원가: {total_cost:,.0f}원
전체 물류이익: {total_profit:,.0f}원
전체 물류이익률: {total_margin:.1%}
""")

    for _, row in store_report.iterrows():

        lines.append(f"""
━━━━━━━━━━
[{row['거래처명']}]
본사공급액: {row['본사공급액']:,.0f}원
총제조원가: {row['총제조원가']:,.0f}원
물류이익: {row['물류이익']:,.0f}원
물류이익률: {row['물류이익률']:.1%}

SKU 사용량 전체
""")

        store_sku = sku_report[
            sku_report["거래처명"] == row["거래처명"]
        ].copy()

        store_sku["공급비중"] = (
            store_sku["공급가액"] /
            row["본사공급액"]
        )

        store_sku = store_sku.sort_values(
            "공급비중",
            ascending=False
        )
        
        for _, sku in store_sku.iterrows():

            supply_ratio = (
                sku["공급가액"] / row["본사공급액"]
                if row["본사공급액"] != 0
                else 0
            )

            profit_ratio = (
                sku["물류이익"] / row["물류이익"]
                if row["물류이익"] != 0
                else 0
            )

            item_name = (
                sku['품목명(규격)']
                .replace("유월의보리 ", "")
                .replace("유월의보리", "")
            )

            lines.append(
                f"- {item_name} / "
                f"{sku['수량']:,.0f}개 / "
                f"공급비중 {supply_ratio:.1%} / "
                f"이익 {sku['물류이익']:,.0f}원 ({profit_ratio:.1%})"
            )

    if len(missing) > 0:
        lines.append("\n⚠ 원가 미등록 SKU")
        for _, row in missing.iterrows():
            lines.append(f"- {row['품목코드']} / {row['품목명(규격)']}")

    # 엑셀 저장용 컬럼 추가
    sku_report["공급비중"] = (
        sku_report["공급가액"] /
        sku_report["거래처명"].map(
            store_report.set_index("거래처명")["본사공급액"]
        )
    )

    sku_report["이익비중"] = (
        sku_report["물류이익"] /
        sku_report["거래처명"].map(
            store_report.set_index("거래처명")["물류이익"]
        ).replace(0, pd.NA)
    )

    with pd.ExcelWriter(
        "월말_물류리포트.xlsx",
        engine="openpyxl"
    ) as writer:

        store_report.to_excel(
            writer,
            sheet_name="STORE_REPORT",
            index=False
        )

        sku_report.to_excel(
            writer,
            sheet_name="SKU_REPORT",
            index=False
        )

    return "\n".join(lines)

if __name__ == "__main__":

    report = run_monthly_logistics_report()

    print(report)

    if not TELEGRAM_BOT_TOKEN:
        raise Exception("TELEGRAM_BOT_TOKEN 환경변수 없음")

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    MAX_LEN = 3500

    for chat_id in TELEGRAM_CHAT_IDS:

        chunks = []
        sections = report.split("━━━━━━━━━━")
        current = ""

        for section in sections:

            section = section.strip()

            if not section:
                continue

            section = "━━━━━━━━━━\n" + section

            if len(current) + len(section) > MAX_LEN:

                if current:
                    chunks.append(current)

                current = section

            else:

                current += "\n" + section

        if current:
            chunks.append(current)

        for chunk in chunks:

            payload = {
                "chat_id": chat_id,
                "text": chunk
            }

            res = requests.post(
                telegram_url,
                data=payload,
                timeout=15
            )

            print(
                "텔레그램 응답:",
                chat_id,
                res.status_code,
                res.text
            )

    for chat_id in TELEGRAM_CHAT_IDS:

        with open(
            "월말_물류리포트.xlsx",
            "rb"
        ) as file:

            res = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
                data={
                    "chat_id": chat_id
                },
                files={
                    "document": file
                }
            )

            print(
                "엑셀 전송:",
                chat_id,
                res.status_code,
                res.text
            )

    print("텔레그램 전송 완료")
