# DDS source v1

This is a new data contract, not a drop-in replacement for the current PAK manifest.
All checksums are SHA-256. Version 1.2.4 identifies the texture content, independently
of the installer app version.

texture-source.json binds the exact index and all ZIP chunks. The index binds every
named asset to a content-addressed full DDS. Each object appears in exactly one chunk.
A named identity is SHA-256 of UTF-8 lowercase(owner) + NUL + literal member.
Member spelling is preserved; do not silently normalize member aliases.

The source layout and graphics fingerprint describe the frozen stock representation
used in the tested release index. They are metadata, not included stock pixels or
proof of compatibility with every future game patch. The target layout, fingerprint,
mip hash and tail hash describe the released replacement bytes verified during export.

Layout fields are width, height, mip count, format family and representation.
Fingerprint domain TQABUP01 includes layout and all literal mip payload bytes.
Keep format/representation distinctions, including BC1/2/3 and ordinary BGRA/BGRX.
Do not reinterpret a shader data channel as color or opacity.

graphics_match is AMBIGUOUS_KEEP_ORIGINAL when the same source layout/fingerprint
has multiple replacement layout/fingerprint outcomes. Preserve those assets by name
in the dataset, but do not choose arbitrarily at graphics-bind time. A matching
fingerprint is not an excuse to bypass current resource layout and lifecycle checks.

## Category contract

Categories attach to **named assets**, not deduplicated byte objects. This permits
the same DDS to be referenced by more than one content group without losing identity.
The index embeds the versioned taxonomy and complete group/map counts.

- content_group: stable checkbox identifier.
- content_evidence: path or saved-material rule; these are inferences.
- map_types: one or more signal annotations.
- map_evidence: saved role with historical/current scope, filename inference, or unknown.
- saved_classification: original role/material, explicit field-presence bit and scope.
- processing_route_kind: known queue route, otherwise null.
- review_required: unresolved content, unknown signal or filename-only signal inference.

Unknown, absent and explicit null remain distinct in saved classification evidence.
A skipped/unknown classification is not a permanent exclusion. QWVU is a storage
profile with four signed components; it does not establish normal-vector semantics.
Alpha may contain customization or shader data rather than opacity.

Future selection should keep a content group's associated color and shader maps
together. Cross-category shared resources and material dependencies may require
shared inclusion; path rules alone do not prove a complete material dependency graph.
Keep unknowns visible. Do not silently drop conflicts or use category tags as a new
appearance-approval gate.

tools/project_inventory.py reads a metadata snapshot and produces a sidecar keyed by
original ID and owner/member. It never edits the input or imports generator code.
Rerun for appended inventories or changed classifications, then bind the resulting
categories into the next export. Completion status is intentionally not duplicated.

## Reproducibility and scope

tools/build_source.py uses a private pinned inventory of published PAK downloads,
the complete released member roster, the frozen tested graphics index, and a pinned
category projection. It verifies each full archive before reading selected members,
then verifies exact full DDS bytes and decoded mip fingerprints. It streams only
selected replacements into ZIP chunks; it never regenerates or re-encodes textures.
Private build bindings and evidence paths are not public assets.

This source does not provide a new runtime loader, modernize unsupported producers,
prove in-game material use or guarantee universal mapping. Future installer work
must download/verify these files, select categories, and adapt the runtime payload
without rebuilding private PAKs. The current application remains unchanged.
