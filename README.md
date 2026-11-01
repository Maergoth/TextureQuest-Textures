# TextureQuest Textures

Generated texture channels for [TextureQuest](https://github.com/Maergoth/TextureQuest).
The installer combines them with the player's own EQ2 files into a local cache.
Game PAKs stay unchanged. No manual texture mapping is needed.

## Downloads

[Generated channels 1.3.0](https://github.com/Maergoth/TextureQuest-Textures/releases/tag/v1.3.0)
requires TextureQuest **1.9.0 or newer**. Older installers cannot use this format.

- **channel-source.json**: download URLs, sizes and SHA-256 checksums.
- **channel-index.json**: source identities, reconstruction recipes, categories and aliases.
- **channels-*.zip**: our generated/corrected RGB channels, stored once per distinct payload.
- **SHA256SUMS.txt**: checksums for the release.

About **17.7 GB** downloads; about **27.8 GB** of local reconstructed textures.
The release retains **24,694 named replacements**, including recovered Maj'Dul
textures and the accepted body/stone corrections. The larger unfinished generation
batch is not included.

Payloads contain no original alpha planes, original DDS headers, opaque tails,
whole DDS files or game archives. The installer obtains those parts from the
player's exact installed originals and builds the graphics lookup automatically.
It verifies cached work and rebuilds only what is needed. Reconstruction happens
during setup, not every frame. Keep the app's data folder in place.

The local full-pack test passed reconstruction checks and the user's in-game
Original/Upscaled switching check. That is not an exhaustive visual audit.
46 legacy alpha results now explicitly use source-derived alpha with new output
hashes; prior hashes remain as history. No old alpha is downloaded as a fallback.

## Categories and shared textures

Bindings retain Characters & monsters, Armor & weapons, Terrain & nature,
Buildings & props, Effects, Interface and Unclassified groups, with separate map
types and saved classification evidence. These annotations prepare future
installer checkboxes. Shared assets may affect more than one category.

Identical originals share a selected upscale: known later corrections take
priority, otherwise the most-used version wins with a stable tie-break. All named
aliases and prior variant metadata remain. Changed or unknown game sources stay
original; the installer never downloads stock data to fill gaps.

## Format

The application verifies trusted release metadata, chunk/payload hashes, exact
ZIP membership, current local source identity and reconstructed DDS hashes.
See [the channel format](docs/CHANNEL-FORMAT.md). Historical full-DDS tools and
older releases describe the previous format; do not use them to publish new
channel-only data. Older public assets are being retired with installer migration.
