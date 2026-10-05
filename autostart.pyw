"""Windows autostart: runs the bot without a console window and restarts it if it stops
(for example when there is no internet right after the computer boots)."""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
LOG = ROOT / "alphamaster.log"
MAX_LOG_SIZE = 5 * 1024 * 1024

env = {**os.environ, "PYTHONUTF8": "1"}

while True:
    if LOG.exists() and LOG.stat().st_size > MAX_LOG_SIZE:
        LOG.replace(LOG.with_suffix(".old.log"))
    with open(LOG, "a", encoding="utf-8") as log:
        subprocess.run([sys.executable, "-m", "alphamaster"], cwd=ROOT, env=env,
                       stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(30)
