"""按需补号:查 sub2api 活跃账号数，低于阈值才触发注册工作流。

逻辑:GET /api/v1/admin/accounts?status=active 取 total；< 阈值(默认 100)就
`gh workflow run register.yml`(用 workflow 默认 inputs：count_per_job=2 + 26 域名)。
够了就跳过，避免无脑过量注册。

凭据走环境变量(公开仓库不含密钥)：SUB2API_URL / SUB2API_EMAIL / SUB2API_PASSWORD。
当前目录有 .env(已 gitignore)时自动加载，方便本地跑。

用法:
    python topup.py                      # 活号<100 则触发一轮
    python topup.py --threshold 200      # 维持 200
    python topup.py --count 2            # 每 job 注册数
    python topup.py --dry-run            # 只看数量不触发
可配 Windows 任务计划/cron 周期跑，做成"维持 N 个活号"的自动补给。
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = "jiayi-1994/rg-gpt"
WORKFLOW = "register.yml"


def _load_dotenv():
    p = Path(os.getcwd()) / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def active_count(client) -> int:
    r = client.list_accounts(platform="openai", status="active", page=1, page_size=1)
    d = r.get("data") if isinstance(r, dict) else r
    if isinstance(d, dict):
        return int(d.get("total") or d.get("total_count")
                   or (d.get("pagination") or {}).get("total") or 0)
    return 0


def trigger(count: int) -> tuple[bool, str]:
    p = subprocess.run(
        ["gh", "workflow", "run", WORKFLOW, "-R", REPO, "-f", f"count_per_job={count}"],
        capture_output=True, text=True,
    )
    return p.returncode == 0, (p.stdout or "") + (p.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=100, help="维持的活号下限(默认 100)")
    ap.add_argument("--count", type=int, default=2, help="触发时 count_per_job(默认 2)")
    ap.add_argument("--dry-run", action="store_true", help="只查数量，不触发")
    args = ap.parse_args()

    _load_dotenv()
    from backend.integrations.sub2api import Sub2ApiClient

    client = Sub2ApiClient()
    client.ensure_configured()
    n = active_count(client)
    print(f"active={n} threshold={args.threshold}")

    if n >= args.threshold:
        print("活号充足，跳过触发。")
        return

    if args.dry_run:
        print(f"活号 {n} < {args.threshold}，dry-run 不触发。")
        return

    ok, out = trigger(args.count)
    if ok:
        print(f"活号 {n} < {args.threshold}，已触发注册工作流(count_per_job={args.count})。")
    else:
        print(f"触发失败: {out.strip()[:200]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
