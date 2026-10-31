"""Non-destructive content and signal annotations; never changes processing."""
from collections import Counter
import re

VERSION = "texturequest-categories-v1"
CONTENT = {
    "characters_monsters": "Characters & monsters",
    "armor_weapons": "Armor & weapons",
    "terrain": "Terrain & nature",
    "buildings_props": "Buildings & props",
    "effects": "Effects",
    "ui": "Interface",
    "unclassified": "Unclassified",
}
MAPS = {
    "color": "Color", "normal": "Normal", "bump": "Bump / surface detail",
    "specular": "Specular", "mask": "Mask", "emissive": "Emissive / glow",
    "alpha": "Alpha / cutout", "environment": "Environment / reflection",
    "effect": "Effect signal", "unknown": "Unknown",
}
ROLES = dict(color="color", normal="normal", bump="bump", spec="specular",
             mask="mask", emissive="emissive", cutout="alpha", env="environment",
             fx="effect")

def taxonomy():
    return dict(
        schema=VERSION, content_groups=CONTENT, map_types=MAPS,
        selection_rule="Select content groups; include all their related map types by default.",
        identity_rule="Annotations belong to owner + literal member, not deduplicated DDS bytes.",
        unknown_rule="Unclassified entries remain visible and are never silently excluded.",
        qualification="Path and filename rules are inferences, not model/material bindings. Saved roles retain their historical/current scope. Alpha may carry data other than opacity. QWVU storage does not imply normal-vector semantics.",
    )

def classify(member, *, role=None, material=None, scope="unavailable",
             role_present=False, route=None, format_name=None):
    p = "/" + member.replace("\\", "/").lower().lstrip("/")
    words = set(x for x in re.split(r"[/_.\-\d]+", p) if x)
    # Effects must precede UI; equipment must precede generic characters.
    if "/ui_fx/fx/" in p or "/effects/" in p or "/fx/" in p:
        group, evidence = "effects", "path:effects"
    elif any(x in p for x in ("/wieldable_items/", "/wearable_items/", "/wearable_items_textures/", "/weapons/", "/armor/", "/shields/")):
        group, evidence = "armor_weapons", "path:equipment"
    elif "/characters/" in p or "/soga_characters/" in p or "/creatures/" in p:
        group, evidence = "characters_monsters", "path:characters"
    elif "/ui/" in p or "/interface/" in p or "/icons/" in p:
        group, evidence = "ui", "path:interface"
    elif any(x in p for x in ("/terrain/", "/ground/", "/flora/", "/foliage/", "/skydome/")) or material in ("terrain", "foliage", "water", "sky"):
        group, evidence = "terrain", "path:nature" if words & {"terrain", "ground", "flora", "foliage", "skydome"} else "saved-material:" + material
    elif material == "fx":
        group, evidence = "effects", "saved-material:fx"
    elif any(x in p for x in ("/interiors/", "/zones/", "/housing/", "/buildings/", "/playerstudio/environments/")):
        group, evidence = "buildings_props", "path:world-environment"
    elif material in ("skin", "creature", "hair"):
        group, evidence = "characters_monsters", "saved-material:" + material
    else:
        group, evidence = "unclassified", "insufficient-saved-evidence"
    kind = route.get("kind") if isinstance(route, dict) else None
    if role in ROLES:
        maps, map_evidence = [ROLES[role]], "saved-role:" + scope
    else:
        stem = p.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        suffix = stem.rsplit("_", 1)[-1]
        inferred = {"c": "color", "n": "normal", "s": "specular", "g": "emissive",
                    "bump": "bump", "mask": "mask"}.get(suffix)
        maps, map_evidence = [inferred or "unknown"], "filename-inference" if inferred else "insufficient-saved-evidence"
    if kind == "QWEN_ALPHA_SELECTED_CHANNEL":
        maps = sorted(set(maps + ["alpha"]))
        map_evidence += ";explicit-route:A"
    result = dict(
        schema=VERSION, content_group=group, content_evidence=evidence,
        map_types=maps, map_evidence=map_evidence,
        saved_classification=dict(scope=scope, role_present=role_present, role=role, material=material),
        processing_route_kind=kind,
        review_required=group == "unclassified" or "unknown" in maps or map_evidence.startswith("filename"),
    )
    if format_name == "QWVU":
        result["storage_qualification"] = "Four stored signed components; no inferred vector or alpha meaning."
    return result

def summary(rows):
    counts = Counter(r["category"]["content_group"] for r in rows)
    maps = Counter(m for r in rows for m in r["category"]["map_types"])
    return dict(content_groups={k: counts[k] for k in CONTENT},
                map_types={k: maps[k] for k in MAPS},
                review_required=sum(r["category"]["review_required"] for r in rows))

def validate(value):
    if value.get("schema") != VERSION or value.get("content_group") not in CONTENT:
        raise ValueError("Category schema/content group")
    maps = value.get("map_types")
    if not isinstance(maps, list) or not maps or len(set(maps)) != len(maps) or any(x not in MAPS for x in maps):
        raise ValueError("Category map types")
    saved = value.get("saved_classification", {})
    if type(saved.get("role_present")) is not bool or not isinstance(saved.get("scope"), str):
        raise ValueError("Category classification scope")
    if type(value.get("review_required")) is not bool:
        raise ValueError("Category review flag")
