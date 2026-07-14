import subprocess
import sys


def run_report(script_name, label):
    print(f"[{label}] 실행 시작", flush=True)
    subprocess.run([sys.executable, script_name], check=True)
    print(f"[{label}] 실행 및 텔레그램 발송 완료", flush=True)


if __name__ == "__main__":
    run_report("test.py", "매출리포트")
    run_report("review_test.py", "리뷰리포트")
