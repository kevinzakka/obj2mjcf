import subprocess


def test_runs_without_error() -> None:
    retcode = subprocess.call(
        [
            "obj2mjcf",
            "--obj-dir",
            ".",
            "--obj-filter",
            "groups",
        ]
    )
    assert retcode == 0
