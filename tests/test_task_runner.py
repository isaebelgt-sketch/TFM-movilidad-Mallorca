import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_task import TASKS  # noqa: E402


def test_task_runner_loads_every_published_entrypoint_without_execution():
    result = subprocess.run(
        [sys.executable, "scripts/run_task.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    expected = f"Comprobadas {len(TASKS)}/{len(TASKS)} tareas sin ejecutarlas."
    assert expected in result.stdout
