# union-report-bot monthly-test

This branch is dedicated to monthly logistics and cost reconciliation.

## Expected input files

Upload these files to the branch root before running:

- `erp_sales.xlsx`
  - ERP transaction ledger export
  - Required sheet: `판매현황`
- `유월의보리_product_master.xlsx`
  - SKU master and theoretical cost base
  - Required sheet: `PRODUCT_MASTER`

## Run

```bash
python monthly_logistics_report.py
```

## Output

The script creates:

- `월말_물류리포트.xlsx`

## Notes

- `main` is not used by this cleanup.
- Daily sales, review crawling, Selenium, and browser dependencies were removed from this branch.
- Telegram credentials must be configured with environment variables, not hardcoded in source.
