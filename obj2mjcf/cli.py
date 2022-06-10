import argparse
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from distutils.spawn import find_executable
from pathlib import Path
from typing import List, Optional

import trimesh
from dm_control import mjcf

# Find the V-HACD executable.
# Trimesh hasn't yet updated their code for the new V-HACD executable (v 4.0) so we
# are not going to use their `convex_decomposition` function for now.
_search_path = os.environ["PATH"]
_VHACD_EXECUTABLE = None
for _name in ["vhacd", "testVHACD"]:
    _VHACD_EXECUTABLE = find_executable(_name, path=_search_path)
    if _VHACD_EXECUTABLE is not None:
        break


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--obj_dir",
        type=str,
        required=True,
        help="Path to a directory containing obj files.",
    )
    parser.add_argument(
        "--use_vhacd",
        default=False,
        action="store_true",
        help="Whether to create a convex decomposition for the collision geom.",
    )
    parser.add_argument(
        "--save_mtl",
        default=False,
        action="store_true",
        help="Whether to save the mtl files.",
    )
    parser.add_argument(
        "--save_mjcf",
        default=False,
        action="store_true",
        help="Whether to save an example MJCF file.",
    )
    parser.add_argument(
        "--verbose",
        default=False,
        action="store_true",
        help="Whether to print verbose output.",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    # Get all obj files in the directory.
    obj_files = list(Path(args.obj_dir).glob("*.obj"))
    logging.info(f"Found {len(obj_files)} obj files.")

    for obj_file in obj_files:
        process_obj(obj_file, args.save_mtl, args.save_mjcf, args.use_vhacd)


def decompose_convex(filename: Path, work_dir: Path) -> bool:
    ret = subprocess.run(
        [f"{_VHACD_EXECUTABLE}", str(filename.absolute().resolve())], check=True
    )
    if ret.returncode != 0:
        logging.error(f"V-HACD failed on {filename}.")
        return False

    mesh = trimesh.load("./decomp.obj", split_object=True, process=False)

    if isinstance(mesh, trimesh.base.Trimesh):
        savename = str(work_dir / f"{filename.stem}_collision.obj")
        mesh.export(savename, include_texture=False, header=None)
    else:
        for i, geom in enumerate(mesh.geometry.values()):
            savename = str(work_dir / f"{filename.stem}_collision_{i}.obj")
            geom.export(savename, include_texture=True, header=None)

    # Delete the decomp.obj and decomp.stl files.
    os.remove("decomp.obj")
    os.remove("decomp.stl")

    return True


def process_obj(
    filename: Path, save_mtl: bool, save_mjcf: bool, use_vhacd: bool
) -> None:
    # Create a directory with the same name as the OBJ file. The processed submeshes
    # and materials will be stored in this directory.
    work_dir = filename.parent / filename.stem
    work_dir.mkdir(exist_ok=True)
    logging.info(f"Saving processed meshes to {work_dir}")

    # Decompose the mesh into convex pieces if V-HACD is available.
    decomp_success = False
    if use_vhacd:
        if _VHACD_EXECUTABLE is None:
            logging.info("V-HACD is not available. Skipping convex decomposition.")
        else:
            decomp_success = decompose_convex(filename, work_dir)
    else:
        logging.info("Skipping convex decomposition.")

    # Read the MTL file from the OBJ file.
    with open(filename, "r") as f:
        for line in f.readlines():
            if line.startswith("mtllib"):
                name = line.split()[1]
                break
    mtl_filename = filename.parent / name
    logging.info(f"Found MTL file: {mtl_filename}")

    # Read the material file and parse each submaterial into a struct that will be used
    # to create material assets in the MJCF file.
    with open(mtl_filename, "r") as f:
        lines = f.readlines()
    split_ids = []
    for i, line in enumerate(lines):
        if line.startswith("newmtl"):
            split_ids.append(i)
    sub_mtls = []
    for i in range(len(split_ids) - 1):
        sub_mtls.append(lines[split_ids[i] : split_ids[i + 1]])
    sub_mtls.append(lines[split_ids[-1] :])

    @dataclass
    class Material:
        name: str
        diffuse: str
        texture: Optional[str]

    mtls: List[Material] = []
    for mtl in sub_mtls:
        name = mtl[0].split(" ")[1].strip()
        texture = None
        for line in mtl:
            if "map_Kd" in line:
                texture = line.split(" ")[1].strip()
                shutil.copy(
                    filename.parent / texture,
                    work_dir / texture,
                )
            if "Kd" in line:
                diffuse = " ".join(line.split(" ")[1:]).strip()
        mtls.append(Material(name, diffuse, texture))
    logging.info("Done processing MTL file.")

    logging.info("Processing OBJ file with trimesh...")
    mesh = trimesh.load(
        filename,
        split_object=True,
        group_material=True,
        process=False,
        maintain_order=True,
    )

    if isinstance(mesh, trimesh.base.Trimesh):
        # No submeshes, just save the mesh.
        savename = str(work_dir / f"{filename.stem}.obj")
        mesh.export(savename, include_texture=True, header=None)
        return

    logging.info("Grouping and saving submeshes by material...")
    for i, geom in enumerate(mesh.geometry.values()):
        savename = str(work_dir / f"{filename.stem}_{i}.obj")
        logging.info(f"\tSaving submesh {savename}")
        geom.export(savename, include_texture=True, header=None)

    # Delete any MTL files that were created during trimesh processing, if any.
    for file in [
        x for x in work_dir.glob("**/*") if x.is_file() and "material_0" in x.name
    ]:
        file.unlink()

    # Save an MTL file for each submesh if desired.
    if save_mtl:
        for i, mtl in enumerate(sub_mtls):
            mtl_name = mtl[0].split(" ")[1].strip()
            for line in mtl:
                if "newmtl" in line:
                    material_name = line.split(" ")[1].strip()
                    break
            # Save the MTL file.
            with open(work_dir / f"{mtl_name}.mtl", "w") as f:
                f.write("".join(mtl))
            # Edit the mtllib line to point to the new MTL file.
            savename = str(work_dir / f"{filename.stem}_{i}.obj")
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

    # Save an MJCF example file.
    if save_mjcf:
        model = mjcf.RootElement()
        model.compiler.angle = "radian"
        # Add assets.
        for material in mtls:
            if material.texture is not None:
                model.asset.add(
                    "texture",
                    type="2d",
                    name=str(Path(material.texture).stem),
                    file=str(work_dir / material.texture),
                )
                model.asset.add(
                    "material",
                    name=material.name,
                    texture=str(Path(material.texture).stem),
                    specular="1",
                    shininess="1",
                )
            else:
                model.asset.add(
                    "material",
                    name=material.name,
                    rgba=material.diffuse + " 1.0",
                )
        # Add bodies.
        obj_body = model.worldbody.add("body", name=filename.stem)
        if isinstance(mesh, trimesh.base.Trimesh):
            meshname = work_dir / f"{filename.stem}.obj"
            model.asset.add(
                "mesh",
                name=str(meshname.stem),
                file=str(meshname),
            )
            obj_body.add(
                "geom",
                type="mesh",
                file=str(work_dir / f"{filename.stem}.obj"),
                material=filename.stem,
            )
        else:
            for i, (name, geom) in enumerate(mesh.geometry.items()):
                meshname = work_dir / f"{filename.stem}_{i}.obj"
                model.asset.add(
                    "mesh",
                    name=str(meshname.stem),
                    file=str(meshname),
                )
                obj_body.add(
                    "geom",
                    type="mesh",
                    mesh=str(meshname.stem),
                    material=name,
                    contype="0",
                    conaffinity="0",
                    group="2",
                )
        if decomp_success:
            # Find collision files from the decomposed convex hulls.
            collisions = [
                x
                for x in work_dir.glob("**/*")
                if x.is_file() and "collision" in x.name
            ]
            for collision in collisions:
                model.asset.add(
                    "mesh",
                    name=str(collision.stem),
                    file=str(collision),
                )
                obj_body.add(
                    "geom",
                    type="mesh",
                    mesh=str(collision.stem),
                    group="3",
                )
        else:
            # If no decomposed convex hulls were created, use the original mesh as
            # the collision mesh.
            # This isn't ideal as the convex hull will be a very bad approximation for
            # some meshes.
            if isinstance(mesh, trimesh.base.Trimesh):
                obj_body.add(
                    "geom",
                    type="mesh",
                    mesh=str(meshname.stem),
                    group="3",
                )
            else:
                for i, (name, geom) in enumerate(mesh.geometry.items()):
                    obj_body.add(
                        "geom",
                        type="mesh",
                        mesh=str(meshname.stem),
                        group="3",
                    )

        # Dump.
        mjcf_dir = work_dir / "mjcf"
        mjcf_dir.mkdir(exist_ok=True)
        mjcf.export_with_assets(
            model,
            mjcf_dir,
            f"{filename.stem}.xml",
        )


if __name__ == "__main__":
    main()
