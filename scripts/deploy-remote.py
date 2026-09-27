"""Deploy us-stock-analyzer to the VPS. Requires DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASS."""
from __future__ import annotations

import io
import os
import tarfile
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "data", "scripts"}
SKIP_SUFFIX = {".pyc", ".pyo", ".log", ".tsbuildinfo"}

REMOTE_SETUP = r"""
set -e
mkdir -p /opt/us-stock-analyzer
tar -xzf /tmp/us-stock-analyzer.tgz -C /opt/us-stock-analyzer
cd /opt/us-stock-analyzer
if [ ! -f .env ]; then cp .env.example .env; fi
python3.11 -m venv backend/.venv
backend/.venv/bin/pip install -q --upgrade pip
backend/.venv/bin/pip install -q -r backend/requirements.txt
cat >/etc/systemd/system/us-stock-analyzer.service <<'UNIT'
[Unit]
Description=US Stock Analyzer
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/us-stock-analyzer/backend
Environment=PYTHONUNBUFFERED=1
Environment=HOME=/root
EnvironmentFile=-/opt/us-stock-analyzer/.env
ExecStart=/opt/us-stock-analyzer/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable us-stock-analyzer
systemctl restart us-stock-analyzer
sleep 2
systemctl --no-pager --full status us-stock-analyzer || true
ss -lntp | grep ':80' || true
curl -sS -m 8 -o /dev/null -w 'health %{http_code}\n' http://127.0.0.1/api/health || true
curl -sS -m 8 -o /dev/null -w 'home %{http_code}\n' http://127.0.0.1/ || true
curl -sS -m 8 http://127.0.0.1/api/access/status || true
echo
"""


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    if path.suffix in SKIP_SUFFIX:
        return True
    if path.name == ".env":
        return True
    return False


def make_tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in ROOT.rglob("*"):
            if not path.is_file() or should_skip(path.relative_to(ROOT)):
                continue
            tar.add(path, arcname=path.relative_to(ROOT).as_posix())
    return buf.getvalue()


def main() -> None:
    dist = ROOT / "frontend" / "dist" / "index.html"
    if not dist.is_file():
        raise SystemExit("缺少 frontend/dist，请先 npm run build")

    print("packing...")
    blob = make_tarball()
    print("tarball bytes", len(blob))

    host = os.environ["DEPLOY_HOST"]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host,
        username=os.environ.get("DEPLOY_USER", "root"),
        password=os.environ["DEPLOY_PASS"],
        timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
    sftp = client.open_sftp()
    with sftp.file("/tmp/us-stock-analyzer.tgz", "wb") as fh:
        fh.write(blob)
    sftp.close()
    print("uploaded, installing...")
    stdin, stdout, stderr = client.exec_command(REMOTE_SETUP, timeout=360)
    out = (stdout.read() + stderr.read()).decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    print(out)
    print("exit", code)
    client.close()
    if code != 0:
        raise SystemExit(code)


if __name__ == "__main__":
    main()
