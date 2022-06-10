# obj2mjcf

[![PyPI Python Version][pypi-versions-badge]][pypi]
[![PyPI version][pypi-badge]][pypi]

[pypi-versions-badge]: https://img.shields.io/pypi/pyversions/obj2mjcf
[pypi-badge]: https://badge.fury.io/py/obj2mjcf.svg
[pypi]: https://pypi.org/project/obj2mjcf/

A tool for converting Wavefront OBJ files to multiple MuJoCo meshes grouped by material.

Currently, MuJoCo does not support OBJ files with groups or objects (i.e., `o` or `g`). Furthermore, only 1 material can be assigned per mesh. This tool is designed to split such OBJ files into sub-meshes grouped by material. The resulting sub-meshes can then be used as a drop-in replacement for the original OBJ file. The result is vastly enhanced visuals for your model:

| Before | After |
|--------|-------|
|<img src="https://raw.githubusercontent.com/kevinzakka/obj2mjcf/main/assets/before.png" height="200"/>|<img src="https://raw.githubusercontent.com/kevinzakka/obj2mjcf/main/assets/after.png" height="200"/>|

## Installation

The recommended way to install this package is via [PyPI](https://pypi.org/project/obj2mjcf/):

```bash
pip install obj2mjcf
```

If you additionally install [V-HACD 4.0](https://github.com/kmammou/v-hacd), this tool will create a convex decomposition of the mesh to use as the collision geometry.

<img src="https://raw.githubusercontent.com/kevinzakka/obj2mjcf/main/assets/convex_collision.png" height="200"/>

## Usage

```bash
usage: obj2mjcf [-h] --obj-dir STR [--use-vhacd] [--save-mtl] [--save-mjcf] [--verbose] [--vhacd-args.max-output-convex-hulls INT]
                [--vhacd-args.voxel-resolution INT] [--vhacd-args.volume-error-percent FLOAT] [--vhacd-args.max-recursion-depth INT]
                [--vhacd-args.no-shrink-wrap] [--vhacd-args.fill-mode {FLOOD,SURFACE,RAYCAST}] [--vhacd-args.max-hull-vert-count INT]
                [--vhacd-args.no-run-async] [--vhacd-args.min-edge-length INT] [--vhacd-args.split-hull]

obj2mjcf arguments.

required arguments:
  --obj-dir STR         Path to a directory containing obj files.

optional arguments:
  -h, --help            show this help message and exit
  --use-vhacd           Whether to create a convex decomposition for the collision geom.
  --save-mtl            Whether to save the mtl files.
  --save-mjcf           Whether to save an example MJCF file.
  --verbose             Whether to print verbose output.

optional vhacd args arguments:
  Arguments to pass to VHACD.

  --vhacd-args.max-output-convex-hulls INT
                        Maximum number of output convex hulls. (default: 32)
  --vhacd-args.voxel-resolution INT
                        Total number of voxels to use. (default: 100000)
  --vhacd-args.volume-error-percent FLOAT
                        Volume error allowed as a percentage. (default: 1.0)
  --vhacd-args.max-recursion-depth INT
                        Maximum recursion depth. (default: 12)
  --vhacd-args.no-shrink-wrap
                        Whether or not to shrinkwrap output to source mesh.
  --vhacd-args.fill-mode {FLOOD,SURFACE,RAYCAST}
                        Fill mode. (default: FLOOD)
  --vhacd-args.max-hull-vert-count INT
                        Maximum number of vertices in the output convex hull. (default: 64)
  --vhacd-args.no-run-async
                        Whether or not to run asynchronously.
  --vhacd-args.min-edge-length INT
                        Minimum size of a voxel edge. (default: 2)
  --vhacd-args.split-hull
                        If false, splits hulls in the middle. If true, tries to find optimal split plane
                        location.
```
