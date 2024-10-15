from itertools import product
import pathlib
import subprocess

from obj2mjcf import cli

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


def test_parse_mtl_line() -> None:
    file_names = [
        "A B.mtl",
        "A_B.mtl",
        "AbCd.mtl",
        "a.mtl",
        "a b.mtl",
        "a-b.mtl",
        "a_b.mtl",
    ]
    comments = [
        "",
        "# comment",
        " # comment",
        " # comment #",
    ]
    for file_name, comment in product(file_names, comments):
        line = f"mtllib {file_name}{comment}\n"
        result = cli.parse_mtl_name(iter([line]))
        assert result == file_name, result

    for line in (
            "a",
            "a # b",
            "mtllib a.what",
            "a.mtl",
    ):
        result = cli.parse_mtl_name(iter([line]))
        assert result is None, result
