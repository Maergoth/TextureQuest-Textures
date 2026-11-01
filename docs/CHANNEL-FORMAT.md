# Generated channels v1

Descriptor: texturequest-generated-channels-source-v1. Index:
texturequest-generated-channels-index-v1. UTF-8 JSON, SHA-256 and byte length pins.
URLs use immutable versioned assets in this repository. Trust the release before
using its pins.

ZIP members are channels/<sha256>.tqc. A TQC starts with the 24-byte little-endian
<8s4I record: TQCH0001, width, height, mip count, family. The body contains generated
RGB in original mip order:

| Family | Body | Restored locally |
| --- | --- | --- |
| 1 / BC1 | 8-byte colour blocks, transparent selectors cleared | Transparency |
| 2 / BC2 | Colour half of each 16-byte block | Alpha half |
| 3 / BC3 | Colour half of each 16-byte block | Alpha half |
| 4 / BGRA8 | Three BGR bytes per pixel | Alpha byte |

No DDS header or exporter tail is included. Layout metadata is not source media.
Alpha is decoded/resized/encoded from local source using the indexed CPU recipe:
padded float32 Lanczos4, per-axis wraps, BOX mips and pinned DirectXTex. Wraps
describe reconstruction, not the actual game UV or sampler configuration.

Recipes pin original full DDS SHA/layout/mip fingerprint, generated payload and
channel profile, target DDS/layout/mip/tail hashes and wraps. The result must
match before use. EXACT_LEGACY_V1 reproduces prior DDS.
SOURCE_REFERENCE_LANCZOS4_BOX_V1 is an explicit new output where old alpha could
not be reproduced; the prior hash remains a reference. BC1 may requantize generated
colour indices if local transparency requires a different block mode.

Named bindings retain complete prior release records and selected recipe/target.
Correction priority precedes most-used/stable ties. The current release admits
RGB only. Future alpha-only, scalar, joint and signed outputs need explicit
channel ownership profiles; never reuse RGB routing for them.

The local reconstructed DDS cache is mixed-origin and must never be uploaded.
