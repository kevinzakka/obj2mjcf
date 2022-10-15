# obj2mjcf

[![PyPI Python Version][pypi-versions-badge]][pypi]
[![PyPI version][pypi-badge]][pypi]

[pypi-versions-badge]: https://img.shields.io/pypi/pyversions/obj2mjcf
[pypi-badge]: https://badge.fury.io/py/obj2mjcf.svg
[pypi]: https://pypi.org/project/obj2mjcf/

`obj2mjcf` is a CLI for processing composite Wavefront [OBJ] files into a [MuJoCo]-conducive format. It automatically:

* Splits an OBJ file into sub-meshes that are grouped by the materials referenced in the OBJ's MTL file
* Creates a collision mesh by performing a convex decomposition of the OBJ with [V-HACD]
* Generates an MJCF XML file that is pre-filled with materials, meshes and geom elements referencing these OBJ files

The generated meshes can then be used as a drop-in replacement for the original OBJ file. The result is vastly enhanced visuals for your model:

| Before | After |
|--------|-------|
|<img src="https://raw.githubusercontent.com/kevinzakka/obj2mjcf/main/assets/anymal_base_before.png" width="400"/>|<img src="https://raw.githubusercontent.com/kevinzakka/obj2mjcf/main/assets/anymal_base_after.png" width="400"/>|
|<img src="https://raw.githubusercontent.com/kevinzakka/obj2mjcf/main/assets/panda_link7_before.png" width="400"/>|<img src="https://raw.githubusercontent.com/kevinzakka/obj2mjcf/main/assets/panda_link7_after.png" width="400"/>|

## Motivation

As of June 2022, MuJoCo does not support composite OBJ files consisting of groups or objects (`o` or `g` OBJ tags) and only 1 material can be assigned per mesh. This means that you have to manually split your OBJ file into sub-meshes, a process that is tedious and error-prone. This tool is meant to automate this process.

## Installation

The recommended way to install this package is via [PyPI](https://pypi.org/project/obj2mjcf/):

```bash
pip install --upgrade obj2mjcf
```

### Extra: V-HACD 4.0

We recommend installing [V-HACD v4.0](https://github.com/kmammou/v-hacd). If available, `obj2mjcf` will leverage it to create better collision geometry for your OBJ file.

```bash
# For macOS and Linux.
bash install_vhacd.sh
```

## Usage

Type the following at the command line for a detailed description of the CLI:

```bash
obj2mjcf --help
```

[OBJ]: https://en.wikipedia.org/wiki/Wavefront_.obj_file
[MuJoCo]: https://github.com/deepmind/mujoco
[V-HACD]: https://github.com/kmammou/v-hacd
