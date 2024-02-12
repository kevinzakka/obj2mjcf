from dataclasses import dataclass
from typing import Optional, Sequence

from obj2mjcf import constants


@dataclass
class Material:
    """A convenience class for constructing MuJoCo materials from MTL files."""

    name: str
    Ka: Optional[str] = None
    Kd: Optional[str] = None
    Ks: Optional[str] = None
    d: Optional[str] = None
    Tr: Optional[str] = None
    Ns: Optional[str] = None
    map_Kd: Optional[str] = None

    @staticmethod
    def from_string(lines: Sequence[str]) -> "Material":
        """Construct a Material object from a string."""
        attrs = {"name": lines[0].split(" ")[1].strip()}
        for line in lines[1:]:
            for attr in constants.MTL_FIELDS:
                if line.startswith(attr):
                    elems = line.split(" ")[1:]
                    elems = [elem for elem in elems if elem != ""]
                    attrs[attr] = " ".join(elems)
                    break
        return Material(**attrs)

    def mjcf_rgba(self) -> str:
        Kd = self.Kd or "1.0 1.0 1.0"
        if self.d is not None:  # alpha
            alpha = self.d
        elif self.Tr is not None:  # 1 - alpha
            alpha = str(1.0 - float(self.Tr))
        else:
            alpha = "1.0"
        # TODO(kevin): Figure out how to use Ka for computing rgba.
        return f"{Kd} {alpha}"

    def mjcf_shininess(self) -> str:
        if self.Ns is not None:
            # Normalize Ns value to [0, 1]. Ns values normally range from 0 to 1000.
            Ns = float(self.Ns) / 1_000
        else:
            Ns = 0.5
        return f"{Ns}"

    def mjcf_specular(self) -> str:
        if self.Ks is not None:
            # Take the average of the specular RGB values.
            Ks = sum(list(map(float, self.Ks.split(" ")))) / 3
        else:
            Ks = 0.5
        return f"{Ks}"
