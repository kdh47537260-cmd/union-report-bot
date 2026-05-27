import pandas as pd

def run_monthly_logistics_report():

    master = pd.read_excel(
        "유월의보리_product_master.xlsx"
    )

    result = f"""
MASTER 정상로드

SKU 개수:
{len(master)}
"""

    return result


if __name__ == "__main__":
    print(
        run_monthly_logistics_report()
    )
