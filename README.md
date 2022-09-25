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

```bash
usage: obj2mjcf [-h] --obj-dir STR [--obj-filter STR] [--save-mtl] [--save-mjcf] [--compile-model] [--verbose] [--vhacd-args.enable] [--vhacd-args.max-output-convex-hulls INT] [--vhacd-args.voxel-resolution INT]
                [--vhacd-args.volume-error-percent FLOAT] [--vhacd-args.max-recursion-depth INT] [--vhacd-args.disable-shrink-wrap] [--vhacd-args.fill-mode {FLOOD,SURFACE,RAYCAST}] [--vhacd-args.max-hull-vert-count INT]
                [--vhacd-args.disable-async] [--vhacd-args.min-edge-length INT] [--vhacd-args.split-hull] [--texture-resize-percent FLOAT] [--overwrite] [--add-free-joint]

A CLI for processing composite Wavefront OBJ files into a MuJoCo-conducive format.

required arguments:
  --obj-dir STR         path to a directory containing obj files. All obj files in the directory will be
                        converted

optional arguments:
  -h, --help            show this help message and exit
  --obj-filter STR      only convert obj files matching this regex (default: None)
  --save-mtl            save the mtl files
  --save-mjcf           save an example XML (MJCF) file
  --compile-model       compile the MJCF file to check for errors
  --verbose             print verbose output
  --texture-resize-percent FLOAT
                        resize the texture to this percentage of the original size (default: 1.0)
  --overwrite           overwrite previous run output
  --add-free-joint      add a free joint to the root body

optional vhacd_args arguments:
  arguments to pass to V-HACD

  --vhacd-args.enable   enable convex decomposition using V-HACD
  --vhacd-args.max-output-convex-hulls INT
                        maximum number of output convex hulls (default: 32)
  --vhacd-args.voxel-resolution INT
                        total number of voxels to use (default: 100000)
  --vhacd-args.volume-error-percent FLOAT
                        volume error allowed as a percentage (default: 1.0)
  --vhacd-args.max-recursion-depth INT
                        maximum recursion depth (default: 14)
  --vhacd-args.disable-shrink-wrap
                        do not shrink wrap output to source mesh
  --vhacd-args.fill-mode {FLOOD,SURFACE,RAYCAST}
                        fill mode (default: FLOOD)
  --vhacd-args.max-hull-vert-count INT
                        maximum number of vertices in the output convex hull (default: 64)
  --vhacd-args.disable-async
                        do not run asynchronously
  --vhacd-args.min-edge-length INT
                        minimum size of a voxel edge (default: 2)
  --vhacd-args.split-hull
                        try to find optimal split plane location
```

[OBJ]: https://en.wikipedia.org/wiki/Wavefront_.obj_file
[MuJoCo]: https://github.com/deepmind/mujoco
[V-HACD]: https://github.com/kmammou/v-hacd
