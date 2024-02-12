# Indentation level for the generated XML.
XML_INDENTATION = "  "

# Character used to denote a comment in an MTL file.
MTL_COMMENT_CHAR = "#"

# MTL fields relevant to MuJoCo.
MTL_FIELDS = (
    # Ambient, diffuse and specular colors.
    "Ka",
    "Kd",
    "Ks",
    # d or Tr are used for the rgba transparency.
    "d",
    "Tr",
    # Shininess.
    "Ns",
    # References a texture file.
    "map_Kd",
)
