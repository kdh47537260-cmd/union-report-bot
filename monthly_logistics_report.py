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


STORE_ORDER = {
    "양재": 0,
    "신흥": 1,
    "본점": 2,
    "신내": 3,
}


def normalize_store_name(value):
    if pd.isna(value):
        return value

    name = str(value).strip()

    if "양재" in name:
        return "양재"
    if "신흥" in name:
        return "신흥"
    if "본점" in name:
        return "본점"
    if "신내" in name:
        return "신내"

    return name


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

    erp["거래처명"] = erp["거래처명"].apply(normalize_store_name)

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
    erp["부가세"] = erp["부가세"].apply(to_number)
    erp["합계"] = erp["합계"].apply(to_number)

    erp["제조원가_단가"] = erp["품목코드"].map(cost_map)
    missing = erp[erp["제조원가_단가"].isna()][["품목코드", "품목명(규격)"]].drop_duplicates()

    erp["총제조원가"] = erp["수량"] * erp["제조원가_단가"].fillna(0)
    erp["물류이익"] = erp["공급가액"] - erp["총제조원가"]

    store_report = (
        erp.groupby("거래처명")
        .agg(
            공급가액=("공급가액","sum"),
            부가세=("부가세","sum"),
            청구합계=("합계","sum"),
            총제조원가=("총제조원가","sum"),
            물류이익=("물류이익","sum"),
        )
        .reset_index()
    )

    store_report["_sort"] = store_report["거래처명"].map(STORE_ORDER).fillna(99)
    store_report = (
        store_report
        .sort_values(["_sort", "거래처명"])
        .drop(columns=["_sort"])
        .reset_index(drop=True)
    )
    
    store_report["물류이익률"] = (
    store_report["물류이익"] /
    store_report["공급가액"].replace(0, pd.NA)
)
    
    sku_report = (
        erp.groupby(["품목코드", "품목명(규격)"])
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

    total_supply = store_report["공급가액"].sum()
    total_vat = store_report["부가세"].sum()
    total_invoice = store_report["청구합계"].sum()
    total_cost = store_report["총제조원가"].sum()
    total_profit = store_report["물류이익"].sum()
    total_margin = total_profit / total_supply if total_supply != 0 else 0

    lines.append(f"""
[월말 물류이익 리포트]

TOTAL
공급가액: {total_supply:,.0f}원
부가세: {total_vat:,.0f}원
공급가+부가세: {total_invoice:,.0f}원

제조원가: {total_cost:,.0f}원
물류이익: {total_profit:,.0f}원
물류 이익률: {total_margin:.1%}
""")

    for _, row in store_report.iterrows():

        lines.append(f"""
━━━━━━━━━━
[{row['거래처명']}]

공급가액: {row['공급가액']:,.0f}원
부가세: {row['부가세']:,.0f}원
청구합계: {row['청구합계']:,.0f}원

총제조원가: {row['총제조원가']:,.0f}원
물류이익: {row['물류이익']:,.0f}원
물류이익률: {row['물류이익률']:.1%}
""")

    if len(missing) > 0:
        lines.append("\n⚠ 원가 미등록 SKU")
        for _, row in missing.iterrows():
            lines.append(f"- {row['품목코드']} / {row['품목명(규격)']}")

    sku_report["공급비중"] = (
        sku_report["공급가액"] /
        (total_supply if total_supply != 0 else 1)
    )

    sku_report["이익비중"] = (
        sku_report["물류이익"] /
        (total_profit if total_profit != 0 else 1)
    )
    
    sku_report = sku_report.sort_values(
    "공급가액",
    ascending=False
)
    store_sku_report = (
        erp.groupby(["거래처명", "품목코드", "품목명(규격)"])
        .agg(
            수량=("수량", "sum"),
            공급가액=("공급가액", "sum"),
            총제조원가=("총제조원가", "sum"),
            물류이익=("물류이익", "sum"),
        )
        .reset_index()
    )

    store_sku_report["물류이익률"] = (
        store_sku_report["물류이익"] /
        store_sku_report["공급가액"].replace(0, pd.NA)
    )

    store_sku_report = store_sku_report.sort_values(
        ["거래처명", "공급가액"],
        ascending=[True, False]
    )

    store_sku_report["_sort"] = store_sku_report["거래처명"].map(STORE_ORDER).fillna(99)
    store_sku_report = (
        store_sku_report
        .sort_values(["_sort", "거래처명", "공급가액"], ascending=[True, True, False])
        .drop(columns=["_sort"])
        .reset_index(drop=True)
    )
    
    with pd.ExcelWriter(
        "월말_물류리포트.xlsx",
        engine="openpyxl"
    ) as writer:

        # 1) SUMMARY 시트
        summary_df = pd.DataFrame({
            "구분": [
                "전체 공급가액",
                "전체 부가세",
                "전체 청구합계",
                "전체 제조원가",
                "전체 물류이익",
                "전체 물류이익률",
            ],
            "값": [
                total_supply,
                total_vat,
                total_invoice,
                total_cost,
                total_profit,
                total_margin,
            ]
        })

        summary_df.to_excel(
            writer,
            sheet_name="SUMMARY",
            index=False,
            startrow=2
        )

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
        
        store_sku_report.to_excel(
            writer,
            sheet_name="STORE_SKU_REPORT",
            index=False
        )

        workbook = writer.book

        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        navy_fill = PatternFill("solid", fgColor="1F4E78")
        light_fill = PatternFill("solid", fgColor="D9EAF7")
        gray_fill = PatternFill("solid", fgColor="F2F2F2")
        red_font = Font(color="C00000", bold=True)
        white_bold = Font(color="FFFFFF", bold=True)
        black_bold = Font(color="000000", bold=True)
        thin_border = Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9"),
        )

        def style_sheet(ws):
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for row in ws.iter_rows():
                for cell in row:
                    cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center"
                    )
                    cell.border = thin_border

            for cell in ws[1]:
                cell.fill = navy_fill
                cell.font = white_bold

            for col in ws.columns:
                max_length = 0
                col_letter = get_column_letter(col[0].column)

                for cell in col:
                    value = str(cell.value) if cell.value is not None else ""
                    max_length = max(max_length, len(value))

                    if isinstance(cell.value, (int, float)):
                        if "율" in str(ws.cell(row=1, column=cell.column).value) or "비중" in str(ws.cell(row=1, column=cell.column).value):
                            cell.number_format = "0.0%"
                        else:
                            cell.number_format = '#,##0'

                ws.column_dimensions[col_letter].width = min(max_length + 4, 35)

        # SUMMARY 디자인
        ws = workbook["SUMMARY"]
        ws["A1"] = "월말 물류이익 리포트"
        ws["A1"].font = Font(size=18, bold=True, color="1F4E78")
        ws.merge_cells("A1:B1")

        for cell in ws[3]:
            cell.fill = navy_fill
            cell.font = white_bold
            cell.alignment = Alignment(horizontal="center")

        for row in ws.iter_rows(min_row=4, max_row=9):
            for cell in row:
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center")

        ws["B4"].number_format='#,##0"원"'
        ws["B5"].number_format='#,##0"원"'
        ws["B6"].number_format='#,##0"원"'
        ws["B7"].number_format='#,##0"원"'
        ws["B8"].number_format='#,##0"원"'
        ws["B9"].number_format='0.0%'

        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 22

        # STORE_REPORT 디자인
        ws = workbook["STORE_REPORT"]
        style_sheet(ws)

        for row in range(2, ws.max_row + 1):
            margin_cell = ws.cell(row=row, column=7)
            margin_cell.number_format = "0.0%"

            if margin_cell.value is not None and margin_cell.value >= 0.4:
                margin_cell.fill = light_fill
                margin_cell.font = black_bold

        # SKU_REPORT 디자인
        ws = workbook["SKU_REPORT"]
        style_sheet(ws)

        for row in range(2, ws.max_row + 1):
            profit_cell = ws.cell(row=row, column=6)
            margin_cell = ws.cell(row=row, column=7)
            supply_ratio_cell = ws.cell(row=row, column=8)
            profit_ratio_cell = ws.cell(row=row, column=9)

            margin_cell.number_format = "0.0%"
            supply_ratio_cell.number_format = "0.0%"
            profit_ratio_cell.number_format = "0.0%"
            ws.cell(row=row, column=3).number_format = '#,##0"개"'
            ws.cell(row=row, column=4).number_format = '#,##0"원"'
            ws.cell(row=row, column=5).number_format = '#,##0"원"'
            ws.cell(row=row, column=6).number_format = '#,##0"원"'
            
            if profit_cell.value is not None and profit_cell.value < 0:
                profit_cell.font = red_font

        # STORE_SKU_REPORT 디자인
        ws = workbook["STORE_SKU_REPORT"]
        style_sheet(ws)

        for row in range(2, ws.max_row + 1):

            profit_cell = ws.cell(row=row, column=7)
            margin_cell = ws.cell(row=row, column=8)

            margin_cell.number_format = "0.0%"

            ws.cell(row=row, column=4).number_format = '#,##0"개"'
            ws.cell(row=row, column=5).number_format = '#,##0"원"'
            ws.cell(row=row, column=6).number_format = '#,##0"원"'
            ws.cell(row=row, column=7).number_format = '#,##0"원"'

            if profit_cell.value is not None and profit_cell.value < 0:
                profit_cell.font = red_font

        # 보기 편하게 시트 순서
        workbook._sheets = [
            workbook["SUMMARY"],
            workbook["STORE_REPORT"],
            workbook["SKU_REPORT"],
            workbook["STORE_SKU_REPORT"],
        ]

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

                if current:
                    current += "\n" + section
                else:
                    current = section

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
    
