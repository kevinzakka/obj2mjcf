import argparse
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import trimesh
from dm_control import mjcf


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--obj_dir",
        type=str,
        required=True,
        help="Path to a directory containing obj files.",
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
        process_obj(obj_file, args.save_mtl, args.save_mjcf)


def process_obj(filename: Path, save_mtl: bool, save_mjcf: bool) -> None:
    # Create a directory with the same name as the OBJ file. The processed submeshes
    # and materials will be stored in this directory.
    work_dir = filename.parent / filename.stem
    work_dir.mkdir(exist_ok=True)
    logging.info(f"Saving processed meshes to {work_dir}")

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
        # geom.apply_transform(_ROTM)
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
