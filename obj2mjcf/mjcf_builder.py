import logging
from pathlib import Path
from typing import Any, List, Union

import mujoco
import numpy as np
import trimesh
from lxml import etree
from termcolor import cprint

from obj2mjcf import constants
from obj2mjcf.material import Material


class MJCFBuilder:
    """Builds a MuJoCo XML model from a mesh and materials."""

    def __init__(
        self,
        filename: Path,
        mesh: Union[trimesh.base.Trimesh, Any],
        materials: List[Material],
        work_dir: Path = Path(),
        decomp_success: bool = False,
    ):
        self.filename = filename
        self.mesh = mesh
        self.materials = materials
        self.decomp_success = decomp_success

        self.work_dir = work_dir
        if self.work_dir == Path():
            self.work_dir = filename.parent / filename.stem

        self.tree = None

    def add_visual_and_collision_default_classes(
        self,
        root: etree.Element,
    ):
        # Define the default element.
        default_elem = etree.SubElement(root, "default")

        # Define visual defaults.
        visual_default_elem = etree.SubElement(default_elem, "default")
        visual_default_elem.attrib["class"] = "visual"
        etree.SubElement(
            visual_default_elem,
            "geom",
            group="2",
            type="mesh",
            contype="0",
            conaffinity="0",
        )

        # Define collision defaults.
        collision_default_elem = etree.SubElement(default_elem, "default")
        collision_default_elem.attrib["class"] = "collision"
        etree.SubElement(collision_default_elem, "geom", group="3", type="mesh")

    def add_assets(self, root: etree.Element, mtls: List[Material]) -> etree.Element:
        # Define the assets element.
        asset_elem = etree.SubElement(root, "asset")

        for material in mtls:
            if material.map_Kd is not None:
                # Create the texture asset.
                texture = Path(material.map_Kd)
                etree.SubElement(
                    asset_elem,
                    "texture",
                    type="2d",
                    name=texture.stem,
                    file=texture.name,
                )
                # Reference the texture asset in a material asset.
                etree.SubElement(
                    asset_elem,
                    "material",
                    name=material.name,
                    texture=texture.stem,
                    specular=material.mjcf_specular(),
                    shininess=material.mjcf_shininess(),
                )
            else:
                etree.SubElement(
                    asset_elem,
                    "material",
                    name=material.name,
                    specular=material.mjcf_specular(),
                    shininess=material.mjcf_shininess(),
                    rgba=material.mjcf_rgba(),
                )

        return asset_elem

    def add_visual_geometries(
        self,
        obj_body: etree.Element,
        asset_elem: etree.Element,
    ):
        # Constants
        filename = self.filename
        mesh = self.mesh
        materials = self.materials

        process_mtl = len(materials) > 0

        # Add visual geometries to object body.
        if isinstance(mesh, trimesh.base.Trimesh):
            meshname = Path(f"{filename.stem}.obj")
            # Add the mesh to assets.
            etree.SubElement(asset_elem, "mesh", file=meshname.as_posix())
            # Add the geom to the worldbody.
            if process_mtl:
                e_ = etree.SubElement(
                    obj_body,
                    "geom",
                    material=materials[0].name,
                    mesh=meshname.stem,
                )
                e_.attrib["class"] = "visual"
            else:
                e_ = etree.SubElement(obj_body, "geom", mesh=meshname.stem)
                e_.attrib["class"] = "visual"
        else:
            for i, (name, geom) in enumerate(mesh.geometry.items()):
                meshname = Path(f"{filename.stem}_{i}.obj")
                # Add the mesh to assets.
                etree.SubElement(asset_elem, "mesh", file=meshname.as_posix())
                # Add the geom to the worldbody.
                if process_mtl:
                    e_ = etree.SubElement(
                        obj_body, "geom", mesh=meshname.stem, material=name
                    )
                    e_.attrib["class"] = "visual"
                else:
                    e_ = etree.SubElement(obj_body, "geom", mesh=meshname.stem)
                    e_.attrib["class"] = "visual"

    def add_collision_geometries(
        self,
        obj_body: etree.Element,
        asset_elem: etree.Element,
    ):
        # Constants.
        filename = self.filename
        mesh = self.mesh
        decomp_success = self.decomp_success

        work_dir = self.work_dir

        if decomp_success:
            # Find collision files from the decomposed convex hulls.
            collisions = [
                x
                for x in work_dir.glob("**/*")
                if x.is_file() and "collision" in x.name
            ]
            collisions.sort(key=lambda x: int(x.stem.split("_")[-1]))

            for collision in collisions:
                etree.SubElement(asset_elem, "mesh", file=collision.name)
                rgb = np.random.rand(3)  # Generate random color for collision meshes.
                e_ = etree.SubElement(
                    obj_body,
                    "geom",
                    mesh=collision.stem,
                    rgba=f"{rgb[0]} {rgb[1]} {rgb[2]} 1",
                )
                e_.attrib["class"] = "collision"
        else:
            # If no decomposed convex hulls were created, use the original mesh as the
            # collision mesh.
            if isinstance(mesh, trimesh.base.Trimesh):
                meshname = Path(f"{filename.stem}.obj")
                e_ = etree.SubElement(obj_body, "geom", mesh=meshname.stem)
                e_.attrib["class"] = "collision"
            else:
                for i, (name, geom) in enumerate(mesh.geometry.items()):
                    meshname = Path(f"{filename.stem}_{i}.obj")
                    e_ = etree.SubElement(obj_body, "geom", mesh=meshname.stem)
                    e_.attrib["class"] = "collision"

    def build(
        self,
        add_free_joint: bool = False,
    ) -> None:
        # Constants.
        filename = self.filename
        mtls = self.materials

        # Start assembling xml tree.
        root = etree.Element("mujoco", model=filename.stem)

        # Add defaults.
        self.add_visual_and_collision_default_classes(root)

        # Add assets.
        asset_elem = self.add_assets(root, mtls)

        # Add worldbody.
        worldbody_elem = etree.SubElement(root, "worldbody")
        obj_body = etree.SubElement(worldbody_elem, "body", name=filename.stem)
        if add_free_joint:
            etree.SubElement(obj_body, "freejoint")

        # Add visual and collision geometries to object body.
        self.add_visual_geometries(obj_body, asset_elem)
        self.add_collision_geometries(obj_body, asset_elem)

        # Create the tree.
        tree = etree.ElementTree(root)
        etree.indent(tree, space=constants.XML_INDENTATION, level=0)
        self.tree = tree

    def compile_model(self):
        # Constants.
        filename = self.filename
        work_dir = self.work_dir

        # Pull up tree if possible.
        tree = self.tree
        if tree is None:
            raise ValueError("Tree has not been defined yet.")

        # Create the work directory if it does not exist.
        try:
            tmp_path = work_dir / "tmp.xml"
            tree.write(tmp_path, encoding="utf-8")
            model = mujoco.MjModel.from_xml_path(tmp_path.as_posix())
            data = mujoco.MjData(model)
            mujoco.mj_step(model, data)
            cprint(f"{filename} compiled successfully!", "green")
        except Exception as e:
            cprint(f"Error compiling model: {e}", "red")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def save_mjcf(
        self,
    ):
        # Constants.
        filename = self.filename
        work_dir = self.work_dir

        # Pull up tree if possible.
        tree = self.tree
        if tree is None:
            raise ValueError("Tree has not been defined yet.")

        # Save the MJCF file.
        xml_path = work_dir / f"{filename.stem}.xml"
        tree.write(xml_path.as_posix(), encoding="utf-8")
        logging.info(f"Saved MJCF to {xml_path}")
