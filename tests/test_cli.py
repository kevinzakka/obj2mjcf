import pathlib
import subprocess
import shutil

# Path to the directory containing this file.
_THIS_DIR = pathlib.Path(__file__).parent.absolute()

# Remove groups dir if it exists.
_OUT_DIR = _THIS_DIR / "groups"
if _OUT_DIR.exists():
    shutil.rmtree(_OUT_DIR)


def test_runs_without_error() -> None:
    retcode = subprocess.call(
        [
            "obj2mjcf",
            "--obj-dir",
            f"{str(_THIS_DIR)}",
            "--save-mtl",
            "--save-mjcf",
            "--compile-model",
            "--verbose",
        ]
    )
    assert retcode == 0
