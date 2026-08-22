"""Safe adapter layer for NyuyenMocap-Oyen.

This module intentionally does not modify MediaPipe detection or cgt_* drivers.
It discovers the actual driver objects/collections at runtime, builds an optional
preview skeleton from the drivers that are really present, and exposes helpers
for handing the original drivers to the existing BlendArMocap transfer system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

try:
    import bpy
    from mathutils import Vector
except ImportError:  # Allows static validation outside Blender.
    bpy = None
    Vector = None


DRIVER_PREFIXES = ("cgt_", "cgt")
DRIVER_COLLECTION_NAMES = (
    "cgt_DRIVERS",
    "CGT_DRIVERS",
    "cgt_POSE",
    "cgt_HANDS",
    "cgt_FACE",
)


@dataclass(frozen=True)
class DriverSet:
    objects: tuple
    collections: tuple


def _require_blender():
    if bpy is None:
        raise RuntimeError("nyuyen_adapter requires Blender's bpy module at runtime")


def _is_driver_object(obj) -> bool:
    name = getattr(obj, "name", "")
    return name.startswith(DRIVER_PREFIXES)


def _walk_collection(collection):
    for obj in collection.objects:
        yield obj
    for child in collection.children:
        yield from _walk_collection(child)


def discover_drivers() -> DriverSet:
    """Discover existing cgt_* drivers without changing them."""
    _require_blender()
    objects = []
    seen = set()

    for obj in bpy.data.objects:
        if _is_driver_object(obj) and obj.name not in seen:
            objects.append(obj)
            seen.add(obj.name)

    collections = []
    for collection in bpy.data.collections:
        if collection.name in DRIVER_COLLECTION_NAMES:
            collections.append(collection)
            for obj in _walk_collection(collection):
                if _is_driver_object(obj) and obj.name not in seen:
                    objects.append(obj)
                    seen.add(obj.name)

    return DriverSet(tuple(objects), tuple(collections))


def hide_driver_viewport(hide: bool = True) -> int:
    """Hide/show cgt_* drivers in the viewport without deleting animation data."""
    drivers = discover_drivers()
    for obj in drivers.objects:
        obj.hide_viewport = hide
        obj.hide_set(hide)
    return len(drivers.objects)


def _find_named_driver(name_candidates: Iterable[str]):
    for name in name_candidates:
        obj = bpy.data.objects.get(name)
        if obj is not None and _is_driver_object(obj):
            return obj
    return None


def _create_bone_between(armature, bone_name: str, head_obj, tail_obj):
    if head_obj is None or tail_obj is None:
        return None
    if armature.data.edit_bones.get(bone_name):
        return armature.data.edit_bones.get(bone_name)

    head = Vector(head_obj.matrix_world.translation)
    tail = Vector(tail_obj.matrix_world.translation)
    if (tail - head).length < 1e-5:
        tail = head + Vector((0.0, 0.05, 0.0))

    bone = armature.data.edit_bones.new(bone_name)
    bone.head = head
    bone.tail = tail
    return bone


def build_preview_skeleton(name: str = "NYUYEN_MOCAP_PREVIEW"):
    """Build a display-only armature from whatever standard pose landmarks exist.

    It is deliberately independent of exact object names beyond a small set of
    aliases. Missing landmarks are skipped; no fake points are invented.
    """
    _require_blender()
    drivers = discover_drivers()
    if not drivers.objects:
        return None

    aliases = {
        "pelvis": ("cgt_hip", "cgt_pelvis", "cgt_mid_hip", "cgt_hips"),
        "neck": ("cgt_neck", "cgt_mid_shoulder", "cgt_shoulder_center"),
        "left_shoulder": ("cgt_left_shoulder", "cgt_shoulder_l", "cgt_l_shoulder"),
        "left_elbow": ("cgt_left_elbow", "cgt_elbow_l", "cgt_l_elbow"),
        "left_wrist": ("cgt_left_wrist", "cgt_wrist_l", "cgt_l_wrist"),
        "right_shoulder": ("cgt_right_shoulder", "cgt_shoulder_r", "cgt_r_shoulder"),
        "right_elbow": ("cgt_right_elbow", "cgt_elbow_r", "cgt_r_elbow"),
        "right_wrist": ("cgt_right_wrist", "cgt_wrist_r", "cgt_r_wrist"),
        "left_hip": ("cgt_left_hip", "cgt_hip_l", "cgt_l_hip"),
        "left_knee": ("cgt_left_knee", "cgt_knee_l", "cgt_l_knee"),
        "left_ankle": ("cgt_left_ankle", "cgt_ankle_l", "cgt_l_ankle"),
        "right_hip": ("cgt_right_hip", "cgt_hip_r", "cgt_r_hip"),
        "right_knee": ("cgt_right_knee", "cgt_knee_r", "cgt_r_knee"),
        "right_ankle": ("cgt_right_ankle", "cgt_ankle_r", "cgt_r_ankle"),
    }
    found = {key: _find_named_driver(names) for key, names in aliases.items()}

    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    arm_data = bpy.data.armatures.new(name + "_DATA")
    arm_obj = bpy.data.objects.new(name, arm_data)
    bpy.context.collection.objects.link(arm_obj)
    arm_obj.show_in_front = True
    arm_obj.display_type = 'WIRE'

    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    chains = (
        ("spine", "pelvis", "neck"),
        ("upper_arm.L", "left_shoulder", "left_elbow"),
        ("forearm.L", "left_elbow", "left_wrist"),
        ("upper_arm.R", "right_shoulder", "right_elbow"),
        ("forearm.R", "right_elbow", "right_wrist"),
        ("thigh.L", "left_hip", "left_knee"),
        ("shin.L", "left_knee", "left_ankle"),
        ("thigh.R", "right_hip", "right_knee"),
        ("shin.R", "right_knee", "right_ankle"),
    )
    created = 0
    for bone_name, head_key, tail_key in chains:
        if _create_bone_between(arm_obj, bone_name, found.get(head_key), found.get(tail_key)):
            created += 1

    bpy.ops.object.mode_set(mode='OBJECT')
    arm_obj.select_set(False)
    return arm_obj if created else None


def get_transfer_source_collection():
    """Return the best existing CGT collection without creating a replacement."""
    _require_blender()
    for name in DRIVER_COLLECTION_NAMES:
        collection = bpy.data.collections.get(name)
        if collection is not None:
            return collection
    return None


def prepare_for_transfer():
    """Discover drivers and hide their viewport representation, preserving data."""
    drivers = discover_drivers()
    if not drivers.objects:
        raise RuntimeError("No cgt_* drivers found. Run MediaPipe detection first.")
    hide_driver_viewport(True)
    return get_transfer_source_collection(), drivers
