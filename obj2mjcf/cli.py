"""A CLI for processing composite Wavefront OBJ files for use in MuJoCo."""

from collections.abc import Iterable
import logging
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

import trimesh
import tyro
from PIL import Image
from termcolor import cprint

from obj2mjcf import constants
from obj2mjcf.material import Material
from obj2mjcf.mjcf_builder import MJCFBuilder


@dataclass(frozen=True)
class CoacdArgs:
    """Arguments to pass to CoACD.

    Defaults and descriptions are copied from: https://github.com/SarahWeiii/CoACD
    """

    preprocess_resolution: int = 50
    """resolution for manifold preprocess (20~100), default = 50"""
    threshold: float = 0.05
    """concavity threshold for terminating the decomposition (0.01~1), default = 0.05"""
    max_convex_hull: int = -1
    """max # convex hulls in the result, -1 for no maximum limitation"""
    mcts_iterations: int = 100
    """number of search iterations in MCTS (60~2000), default = 100"""
    mcts_max_depth: int = 3
    """max search depth in MCTS (2~7), default = 3"""
    mcts_nodes: int = 20
    """max number of child nodes in MCTS (10~40), default = 20"""
    resolution: int = 2000
    """sampling resolution for Hausdorff distance calculation (1e3~1e4), default = 2000"""
    pca: bool = False
    """enable PCA pre-processing, default = false"""
    seed: int = 0
    """random seed used for sampling, default = 0"""


@dataclass(frozen=True)
class Args:
    obj_dir: str
    """path to a directory containing obj files. All obj files in the directory will be
    converted"""
    obj_filter: Optional[str] = None
    """only convert obj files matching this regex"""
    save_mjcf: bool = False
    """save an example XML (MJCF) file"""
    compile_model: bool = False
    """compile the MJCF file to check for errors"""
    verbose: bool = False
    """print verbose output"""
    decompose: bool = False
    """approximate mesh decomposition using CoACD"""
    coacd_args: CoacdArgs = field(default_factory=CoacdArgs)
    """arguments to pass to CoACD"""
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


def decompose_convex(filename: Path, work_dir: Path, coacd_args: CoacdArgs) -> bool:
    cprint(f"Decomposing {filename}", "yellow")

    import coacd  # noqa: F401

    obj_file = filename.resolve()
    logging.info(f"Decomposing {obj_file}")

    mesh = trimesh.load(obj_file, force="mesh")
    mesh = coacd.Mesh(mesh.vertices, mesh.faces)  # type: ignore

    parts = coacd.run_coacd(
        mesh=mesh,
        **asdict(coacd_args),
    )

    mesh_parts = []
    for vs, fs in parts:
        mesh_parts.append(trimesh.Trimesh(vs, fs))

    # Save the decomposed parts as separate OBJ files.
    for i, p in enumerate(mesh_parts):
        submesh_name = work_dir / f"{obj_file.stem}_collision_{i}.obj"
        p.export(submesh_name.as_posix())

    return True


def parse_mtl_name(lines: Iterable[str]) -> Optional[str]:
    mtl_regex = re.compile(r"^mtllib\s+(.+?\.mtl)(?:\s*#.*)?\s*\n?$")
    for line in lines:
        match = mtl_regex.match(line)
        if match is not None:
            name = match.group(1)
            return name
    return None

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

    # Decompose the mesh into convex pieces if desired.
    decomp_success = False
    if args.decompose:
        decomp_success = decompose_convex(filename, work_dir, args.coacd_args)

    # Check if the OBJ files references an MTL file.
    # TODO(kevin): Should we support multiple MTL files?
    with filename.open("r") as f:
        name = parse_mtl_name(f.readlines())

    process_mtl = name is not None


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
        savename = work_dir / f"{filename.stem}.obj"
        logging.info(f"Saving mesh {savename}")
        mesh.export(savename.as_posix(), include_texture=True, header=None)
    else:
        logging.info("Grouping and saving submeshes by material")
        for i, geom in enumerate(mesh.geometry.values()):  # type: ignore
            savename = work_dir / f"{filename.stem}_{i}.obj"
            logging.info(f"Saving submesh {savename}")
            geom.export(savename.as_posix(), include_texture=True, header=None)

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

    mtls = list({obj.name: obj for obj in mtls}.values())

    # Delete any MTL files that were created during trimesh processing, if any.
    for file in [
        x
        for x in work_dir.glob("**/*")
        if x.is_file() and "material_0" in x.name and not x.name.endswith(".png")
    ]:
        file.unlink()

    # Build an MJCF.
    builder = MJCFBuilder(filename, mesh, mtls, decomp_success=decomp_success)
    builder.build(add_free_joint=args.add_free_joint)

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
