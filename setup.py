import re
from pathlib import Path

from setuptools import find_packages, setup

_here = Path(__file__).resolve().parent

name = "obj2mjcf"

# Reference: https://github.com/patrick-kidger/equinox/blob/main/setup.py
with open(_here / name / "__init__.py") as f:
    meta_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    if meta_match:
        version = meta_match.group(1)
    else:
        raise RuntimeError("Unable to find __version__ string.")


with open(_here / "README.md", "r") as f:
    readme = f.read()

core_requirements = [
    "trimesh>=3.15.5",
    "Pillow>=9.2.0",
    "mujoco>=2.2.0",
    "tyro>=0.3.22",
    "numpy",
    "termcolor>=2.0.1",
    "lxml>=4.9.1",
    "coacd>=1.0.0",
]

testing_requirements = [
    "pytest",
] + core_requirements

dev_requirements = [
    "black",
    "mypy",
    "ruff",
] + testing_requirements

classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Natural Language :: English",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

author = "Kevin Zakka"

author_email = "kevinarmandzakka@gmail.com"

description = "A CLI for processing composite Wavefront OBJ files for use in MuJoCo"


setup(
    name=name,
    version=version,
    author=author,
    author_email=author_email,
    maintainer=author,
    maintainer_email=author_email,
    description=description,
    long_description=readme,
    long_description_content_type="text/markdown",
    url=f"https://github.com/kevinzakka/{name}",
    license="MIT",
    license_files=("LICENSE",),
    packages=find_packages(),
    package_data={f"{name}": ["py.typed"]},
    python_requires=">=3.8",
    install_requires=core_requirements,
    extras_require={
        "testing": testing_requirements,
        "test": testing_requirements,
        "dev": dev_requirements,
    },
    classifiers=classifiers,
    entry_points={"console_scripts": [f"{name}={name}.cli:main"]},
)
