# TextureQuest Textures

Standalone upscaled DDS files for [TextureQuest](https://github.com/Maergoth/TextureQuest).
This is a separate data source for the next installer format. The current installer
still uses the existing PAK releases.

## Downloads

[Texture source 1.2.3](https://github.com/Maergoth/TextureQuest-Textures/releases/tag/v1.2.3)
contains only the **24,693 released replacement textures**, including the recovered
Maj'Dul textures. It excludes unfinished generation.

- **texture-source.json**: download URLs, sizes and SHA-256 checksums.
- **texture-index.json**: original asset names, DDS objects, graphics fingerprints and categories.
- **dds-*.zip**: individual DDS files, grouped into download chunks.
- **SHA256SUMS.txt**: checksums for the complete release.

Stable manifest for future integration:
https://github.com/Maergoth/TextureQuest-Textures/releases/download/v1.2.3/texture-source.json

The DDS bytes are extracted unchanged from the published packs, including headers,
mips and tails. Each distinct DDS is stored once as dds/&lt;sha256&gt;.dds; the index
maps it to its original archive and member names. There are no stock texture pixels,
PAK files or PNG masters in these downloads.

**This does not switch the current app to DDS downloads.** That installer/runtime
integration comes next. Existing PAK downloads and Replace mode remain available.

## Categories

Each named texture has a content group and separate map types:

| Content checkbox | Includes |
| --- | --- |
| Characters & monsters | Bodies, faces, hair and creature surfaces |
| Armor & weapons | Wearable equipment, weapons, shields and cloaks |
| Terrain & nature | Ground, foliage, water and sky |
| Buildings & props | Architecture, interiors, furniture and world objects |
| Effects | Particle and other effect textures |
| Interface | UI assets |
| Unclassified | Assets without enough saved evidence |

Map types include color, normal, bump, specular, mask, emissive, alpha and
environment data. Content selection should include its associated map types by
default, rather than treating shader maps as unrelated artwork.

These annotations prepare future installer checkboxes; the checkboxes are not
implemented in the current installer. Categories use asset paths and saved
classifications. The index records that evidence and flags uncertain map types.
Shared assets can affect more than one object or category. A graphics fingerprint
that resolves to conflicting replacements must keep the original; categories
do not override that rule.

The generation batch has its own metadata-only category sidecar in the authoring
workspace. Categorization does not change the running queue, recipe or saved pixels.
Use tools/project_inventory.py to annotate future inventory snapshots.

## Verify a complete download

Requires Python 3.10+ on Windows; no game, GPU or third-party packages needed:

~~~powershell
python tools/verify_source.py D:\TextureQuest-Textures
~~~

Download texture-source.json, texture-index.json and every listed ZIP into that
folder first. The verifier checks complete file hashes, ZIP membership and every
DDS header, mip payload, tail and graphics fingerprint without extracting loose copies.
The manifest itself must come from the trusted release.

See [the format contract](docs/FORMAT.md) for integration details.
