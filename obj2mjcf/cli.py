"""A CLI for processing composite Wavefront OBJ files for use in MuJoCo."""

import enum
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import trimesh
import tyro
from PIL import Image
from termcolor import cprint

from obj2mjcf import constants
from obj2mjcf.material import Material
from obj2mjcf.mjcf_builder import MJCFBuilder

# Find the V-HACD v4.0 executable in the system path.
# Note trimesh has not updated their code to work with v4.0 which is why we do not use
# their `convex_decomposition` function.
# TODO(kevin): Is there a way to assert that the V-HACD version is 4.0?
_VHACD_EXECUTABLE = shutil.which("TestVHACD")

# Names of the V-HACD output files.
_VHACD_OUTPUTS = ["decomp.obj", "decomp.stl"]


class FillMode(enum.Enum):
    FLOOD = enum.auto()
    SURFACE = enum.auto()
    RAYCAST = enum.auto()


@dataclass(frozen=True)
class VhacdArgs:
    enable: bool = False
    """enable convex decomposition using V-HACD"""
    max_output_convex_hulls: int = 32
    """maximum number of output convex hulls"""
    voxel_resolution: int = 100_000
    """total number of voxels to use"""
    volume_error_percent: float = 1.0
    """volume error allowed as a percentage"""
    max_recursion_depth: int = 14
    """maximum recursion depth"""
    disable_shrink_wrap: bool = False
    """do not shrink wrap output to source mesh"""
    fill_mode: FillMode = FillMode.FLOOD
    """fill mode"""
    max_hull_vert_count: int = 64
    """maximum number of vertices in the output convex hull"""
    disable_async: bool = False
    """do not run asynchronously"""
    min_edge_length: int = 2
    """minimum size of a voxel edge"""
    split_hull: bool = False
    """try to find optimal split plane location"""


@dataclass(frozen=True)
class Args:
    obj_dir: str
    """path to a directory containing obj files. All obj files in the directory will be
    converted"""
    obj_filter: Optional[str] = None
    """only convert obj files matching this regex"""
    save_mtl: bool = False
    """save the mtl files"""
    save_mjcf: bool = False
    """save an example XML (MJCF) file"""
    compile_model: bool = False
    """compile the MJCF file to check for errors"""
    verbose: bool = False
    """print verbose output"""
    vhacd_args: VhacdArgs = field(default_factory=VhacdArgs)
    """arguments to pass to V-HACD"""
    texture_resize_percent: float = 1.0
    """resize the texture to this percentage of the original size"""
    overwrite: bool = False
    """overwrite previous run output"""
    add_free_joint: bool = False
    """add a free joint to the root body"""


def resize_texture(filename: Path, resize_percent) -> None:
    """Resize a texture to a percentage of its original size."""
    if resize_percent == 1.0:
        return
    image = Image.open(filename)
    new_width = int(image.size[0] * resize_percent)
    new_height = int(image.size[1] * resize_percent)
    logging.info(f"Resizing {filename} to {new_width}x{new_height}")
    image = image.resize((new_width, new_height), Image.LANCZOS)
    image.save(filename)


def decompose_convex(filename: Path, work_dir: Path, vhacd_args: VhacdArgs) -> bool:
    if not vhacd_args.enable:
        return False

    if _VHACD_EXECUTABLE is None:
        logging.info(
            "V-HACD was enabled but not found in the system path. Either install it "
            "manually or run `bash install_vhacd.sh`. Skipping decomposition"
        )
        return False

    obj_file = filename.resolve()
    logging.info(f"Decomposing {obj_file}")

    with tempfile.TemporaryDirectory() as tmpdirname:
        prev_dir = os.getcwd()
        os.chdir(tmpdirname)

        # Copy the obj file to the temporary directory.
        shutil.copy(obj_file, tmpdirname)

        # Call V-HACD, suppressing output.
        ret = subprocess.run(
            [
                f"{_VHACD_EXECUTABLE}",
                obj_file.name,
                "-o",
                "obj",
                "-h",
                f"{vhacd_args.max_output_convex_hulls}",
                "-r",
                f"{vhacd_args.voxel_resolution}",
                "-e",
                f"{vhacd_args.volume_error_percent}",
                "-d",
                f"{vhacd_args.max_recursion_depth}",
                "-s",
                f"{int(not vhacd_args.disable_shrink_wrap)}",
                "-f",
                f"{vhacd_args.fill_mode.name.lower()}",
                "-v",
                f"{vhacd_args.max_hull_vert_count}",
                "-a",
                f"{int(not vhacd_args.disable_async)}",
                "-l",
                f"{vhacd_args.min_edge_length}",
                "-p",
                f"{int(vhacd_args.split_hull)}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=True,
        )
        if ret.returncode != 0:
            logging.error(f"V-HACD failed on {filename}")
            return False

        # Remove the original obj file and the V-HACD output files.
        for name in _VHACD_OUTPUTS + [obj_file.name]:
            file_to_delete = Path(tmpdirname) / name
            if file_to_delete.exists():
                file_to_delete.unlink()

        os.chdir(prev_dir)

        # Get list of sorted collisions.
        collisions = list(Path(tmpdirname).glob("*.obj"))
        collisions.sort(key=lambda x: x.stem)

        for i, filename in enumerate(collisions):
            savename = str(work_dir / f"{obj_file.stem}_collision_{i}.obj")
            shutil.move(str(filename), savename)

    return True


def process_obj(filename: Path, args: Args) -> None:
    # Create a directory with the same name as the OBJ file. The processed submeshes
    # and materials will be stored there.
    work_dir = filename.parent / filename.stem
    if work_dir.exists():
        if not args.overwrite:
            proceed = input(
                f"{work_dir.resolve()} already exists, maybe from a previous run? "
                "Proceeding will overwrite it.\nDo you wish to continue [y/n]: "
            )
            if proceed.lower() != "y":
                return
        shutil.rmtree(work_dir)
    work_dir.mkdir(exist_ok=True)
    logging.info(f"Saving processed meshes to {work_dir}")

    # Decompose the mesh into convex pieces if V-HACD is available.
    decomp_success = decompose_convex(filename, work_dir, args.vhacd_args)

    # Check if the OBJ files references an MTL file.
    # TODO(kevin): Should we support multiple MTL files?
    process_mtl = False
    with open(filename, "r") as f:
        for line in f.readlines():
            if line.startswith("mtllib"):  # Deals with commented out lines.
                process_mtl = True
                name = line.split()[1]
                break

    sub_mtls: List[List[str]] = []
    mtls: List[Material] = []
    if process_mtl:
        # Make sure the MTL file exists. The MTL filepath is relative to the OBJ's.
        mtl_filename = filename.parent / name
        if not mtl_filename.exists():
            raise RuntimeError(
                f"The MTL file {mtl_filename.resolve()} referenced in the OBJ file "
                f"{filename} does not exist"
            )
        logging.info(f"Found MTL file: {mtl_filename}")

        # Parse the MTL file into separate materials.
        with open(mtl_filename, "r") as f:
            lines = f.readlines()
        # Remove comments.
        lines = [
            line for line in lines if not line.startswith(constants.MTL_COMMENT_CHAR)
        ]
        # Remove empty lines.
        lines = [line for line in lines if line.strip()]
        # Remove trailing whitespace.
        lines = [line.strip() for line in lines]
        # Split at each new material definition.
        for line in lines:
            if line.startswith("newmtl"):
                sub_mtls.append([])
            sub_mtls[-1].append(line)
        for sub_mtl in sub_mtls:
            mtls.append(Material.from_string(sub_mtl))

        # Process each material.
        for mtl in mtls:
            logging.info(f"Found material: {mtl.name}")
            if mtl.map_Kd is not None:
                texture_path = Path(mtl.map_Kd)
                texture_name = texture_path.name
                src_filename = filename.parent / texture_path
                if not src_filename.exists():
                    raise RuntimeError(
                        f"The texture file {src_filename} referenced in the MTL file "
                        f"{mtl.name} does not exist"
                    )
                # We want a flat directory structure in work_dir.
                dst_filename = work_dir / texture_name
                shutil.copy(src_filename, dst_filename)
                # MuJoCo only supports PNG textures ¯\_(ツ)_/¯.
                if texture_path.suffix.lower() in [".jpg", ".jpeg"]:
                    image = Image.open(dst_filename)
                    os.remove(dst_filename)
                    dst_filename = (work_dir / texture_path.stem).with_suffix(".png")
                    image.save(dst_filename)
                    texture_name = dst_filename.name
                    mtl.map_Kd = texture_name
                resize_texture(dst_filename, args.texture_resize_percent)
        logging.info("Done processing MTL file")

    logging.info("Processing OBJ file with trimesh")
    mesh = trimesh.load(
        filename,
        split_object=True,
        group_material=True,
        process=False,
        # Note setting this to False is important. Without it, there are a lot of weird
        # visual artifacts in the texture.
        maintain_order=False,
    )

    if isinstance(mesh, trimesh.base.Trimesh):
        # No submeshes, just save the mesh.
        savename = str(work_dir / f"{filename.stem}.obj")
        logging.info(f"Saving mesh {savename}")
        mesh.export(savename, include_texture=True, header=None)
    else:
        logging.info("Grouping and saving submeshes by material")
        for i, geom in enumerate(mesh.geometry.values()):
            savename = str(work_dir / f"{filename.stem}_{i}.obj")
            logging.info(f"Saving submesh {savename}")
            geom.export(savename, include_texture=True, header=None)

    # Edge case handling where the material file can have many materials but the OBJ
    # itself only references one. In that case, we trim out the extra materials and
    # only keep the one that is referenced.
    if isinstance(mesh, trimesh.base.Trimesh) and len(mtls) > 1:
        # Find the material that is referenced.
        with open(filename, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith("usemtl"):
                break
        mat_name = line.split()[1]
        # Trim out the extra materials.
        for smtl in sub_mtls:
            if smtl[0].split()[1] == mat_name:
                break
        sub_mtls = [smtl]
        mtls = [Material.from_string(smtl)]

    # Delete any MTL files that were created during trimesh processing, if any.
    for file in [
        x for x in work_dir.glob("**/*") if x.is_file() and "material_0" in x.name
    ]:
        file.unlink()

    # Save an MTL file for each submesh if desired.
    if args.save_mtl:
        for i, smtl in enumerate(sub_mtls):
            mtl_name = smtl[0].split(" ")[1].strip()
            for line in smtl:
                if "newmtl" in line:
                    material_name = line.split(" ")[1].strip()
                    break
            # Save the MTL file.
            with open(work_dir / f"{mtl_name}.mtl", "w") as f:
                f.write("\n".join(smtl))
            # Edit the mtllib line to point to the new MTL file.
            if len(sub_mtls) > 1:
                savename = str(work_dir / f"{filename.stem}_{i}.obj")
            else:
                savename = str(work_dir / f"{filename.stem}.obj")
            with open(savename, "r") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if line.startswith("mtllib"):
                    lines[i] = f"mtllib {mtl_name}.mtl\n"
                    break
            for i, line in enumerate(lines):
                if line.startswith("usemtl"):
                    lines[i] = f"usemtl {material_name}\n"
                    break
            with open(savename, "w") as f:
                f.write("".join(lines))

    # Build an MJCF.
    builder = MJCFBuilder(filename, mesh, mtls, decomp_success=decomp_success)
    builder.build()

    # Compile and step the physics to check for any errors.
    if args.compile_model:
        builder.compile_model()

    # Dump.
    if args.save_mjcf:
        builder.save_mjcf()


def main() -> None:
    args = tyro.cli(Args, description=__doc__)

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    # Get all obj files in the directory.
    obj_files = list(Path(args.obj_dir).glob("*.obj"))

    # Filter out the ones that don't match the regex filter.
    if args.obj_filter is not None:
        obj_files = [
            x for x in obj_files if re.search(args.obj_filter, x.name) is not None
        ]

    for obj_file in obj_files:
        cprint(f"Processing {obj_file}", "yellow")
        process_obj(obj_file, args)
