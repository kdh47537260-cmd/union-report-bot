import pandas as pd

MASTER_FILE = "유월의보리_product_master.xlsx"
ERP_FILE = "erp_sales.xlsx"


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
        ].sort_values(
            "수량",
            ascending=False
        )

        for _, sku in store_sku.iterrows():

            lines.append(
                f"- {sku['품목명(규격)']} / "
                f"{sku['수량']:,.0f}개 / "
                f"공급 {sku['공급가액']:,.0f}원 / "
                f"이익 {sku['물류이익']:,.0f}원"
            )

    if len(missing) > 0:
        lines.append("\n⚠ 원가 미등록 SKU")
        for _, row in missing.iterrows():
            lines.append(f"- {row['품목코드']} / {row['품목명(규격)']}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(run_monthly_logistics_report())
