# obj2mjcf

[![PyPI Python Version][pypi-versions-badge]][pypi]
[![PyPI version][pypi-badge]][pypi]

[pypi-versions-badge]: https://img.shields.io/pypi/pyversions/obj2mjcf
[pypi-badge]: https://badge.fury.io/py/obj2mjcf.svg
[pypi]: https://pypi.org/project/obj2mjcf/

`obj2mjcf` is a CLI for proccessing composite Wavefront [OBJ] files for use in [MuJoCo]. It automatically:

* Splits an OBJ file into sub-meshes that are grouped by the materials referenced in the OBJ's MTL file
* Generates an MJCF XML file that is pre-filled with materials, meshes and geom elements referencing these OBJ files
* Optionally generates a collision mesh by performing a convex decomposition of the OBJ using [V-HACD]

`obj2mjcf` was used to process model meshes for [MuJoCo Menagerie]:

<p float="left">
  <img src="https://raw.githubusercontent.com/deepmind/mujoco_menagerie/main/anybotics_anymal_c/anymal_c.png" height="200">
  <img src="https://raw.githubusercontent.com/deepmind/mujoco_menagerie/main/franka_emika_panda/panda.png" height="200">
</p>

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

Type the following at the command line for a detailed description of available options:

```bash
obj2mjcf --help
```

[OBJ]: https://en.wikipedia.org/wiki/Wavefront_.obj_file
[MuJoCo]: https://github.com/deepmind/mujoco
[V-HACD]: https://github.com/kmammou/v-hacd
[MuJoCo Menagerie]: https://github.com/deepmind/mujoco_menagerie
