# obj2mjcf

A tool for converting Wavefront OBJ files into MuJoCo sub-meshes grouped by material.

## Usage

```bash
usage: obj2mjcf [-h] --obj_dir OBJ_DIR [--save_mtl] [--save_mjcf] [--verbose]

optional arguments:
  -h, --help         show this help message and exit
  --obj_dir OBJ_DIR  Path to a directory containing obj files.
  --save_mtl         Whether to save the mtl files.
  --save_mjcf        Whether to save an example MJCF file.
  --verbose          Whether to print verbose output.
```
