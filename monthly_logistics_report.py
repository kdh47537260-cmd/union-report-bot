import pandas as pd

MASTER_FILE = "유월의보리_product_master.xlsx"
ERP_FILE = "erp_sales.xlsx"


def to_number(value):
    if pd.isna(value):
        return 0
    return float(str(value).replace(",", "").strip())


def run_monthly_logistics_report():
    master = pd.read_excel(MASTER_FILE)
    erp = pd.read_excel(ERP_FILE)
    
    # 컬럼명 공백 제거
    erp.columns = erp.columns.str.strip()
    master.columns = master.columns.str.strip()

    print("ERP 컬럼:")
    print(erp.columns.tolist())

    master["품목코드"] = master["품목코드"].astype(str).str.strip()
    erp["품목코드"] = erp["품목코드"].astype(str).str.strip()

    master = master[master["사용"].astype(str).str.upper() == "Y"]

    cost_map = dict(zip(master["품목코드"], master["제조원가"]))

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

    store_report["물류이익률"] = store_report["물류이익"] / store_report["본사공급액"]

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

    sku_report["물류이익률"] = sku_report["물류이익"] / sku_report["공급가액"]

    lines = []
    lines.append("[월말 물류이익 테스트 리포트]\n")

    for _, row in store_report.iterrows():
        lines.append(f"""
[{row['거래처명']}]
본사공급액: {row['본사공급액']:,.0f}원
총제조원가: {row['총제조원가']:,.0f}원
물류이익: {row['물류이익']:,.0f}원
물류이익률: {row['물류이익률']:.1%}
""")

    if len(missing) > 0:
        lines.append("\n⚠ 원가 미등록 SKU")
        for _, row in missing.iterrows():
            lines.append(f"- {row['품목코드']} / {row['품목명(규격)']}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(run_monthly_logistics_report())
