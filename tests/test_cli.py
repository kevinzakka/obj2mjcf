import pathlib
import subprocess

# Path to the directory containing this file.
_THIS_DIR = pathlib.Path(__file__).parent.absolute()


def test_runs_without_error() -> None:
    retcode = subprocess.call(
        [
            "obj2mjcf",
            "--obj-dir",
            f"{str(_THIS_DIR)}",
            "--overwrite",
            "--save-mjcf",
            "--compile-model",
            "--verbose",
        ]
    )
    assert retcode == 0
