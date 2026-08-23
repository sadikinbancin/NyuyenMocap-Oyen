"""Safe visual adapter for MediaPipe/CGT landmark output.

This module deliberately does not modify the CGT landmark objects or the existing
BlendArMocap transfer system.  It creates a separate armature used only as a
readable 3D skeleton preview.  The preview bones follow the original cgt_*
objects through Blender constraints, so the original MediaPipe data remains the
source of truth for transfer/retargeting.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

import bpy
from mathutils import Vector


PREVIEW_NAME = "CGT_Visual_Skeleton"
PREVIEW_ARMATURE_NAME = "CGT_Visual_Skeleton_Armature"

# MediaPipe Pose landmark graph.  These are intentionally named using the
# canonical CGT object names produced by cgt_naming.POSE.
POSE_SEGMENTS = (
    ("cgt_hip_center", "cgt_shoulder_center", "spine"),
    ("cgt_shoulder_center", "cgt_shoulder.L", "shoulder.L"),
    ("cgt_shoulder.L", "cgt_elbow.L", "upper_arm.L"),
    ("cgt_elbow.L", "cgt_pose_wrist.L", "forearm.L"),
    ("cgt_pose_wrist.L", "cgt_index.L", "hand.L"),
    ("cgt_shoulder_center", "cgt_shoulder.R", "shoulder.R"),
    ("cgt_shoulder.R", "cgt_elbow.R", "upper_arm.R"),
    ("cgt_elbow.R", "cgt_pose_wrist.R", "forearm.R"),
    ("cgt_pose_wrist.R", "cgt_index.R", "hand.R"),
    ("cgt_hip_center", "cgt_hip.L", "thigh.L"),
    ("cgt_hip.L", "cgt_knee.L", "shin.L"),
    ("cgt_knee.L", "cgt_ankle.L", "foot.L"),
    ("cgt_ankle.L", "cgt_foot_index.L", "toe.L"),
    ("cgt_hip_center", "cgt_hip.R", "thigh.R"),
    ("cgt_hip.R", "cgt_knee.R", "shin.R"),
    ("cgt_knee.R", "cgt_ankle.R", "foot.R"),
    ("cgt_ankle.R", "cgt_foot_index.R", "toe.R"),
    ("cgt_shoulder_center", "cgt_hip_center", "torso"),
)

HAND_SEGMENTS = (
    ("wrist", "thumb_cmc", "thumb.01"),
    ("thumb_cmc", "thumb_mcp", "thumb.02"),
    ("thumb_mcp", "thumb_ip", "thumb.03"),
    ("thumb_ip", "thumb_tip", "thumb.04"),
    ("wrist", "index_finger_mcp", "index.01"),
    ("index_finger_mcp", "index_finger_pip", "index.02"),
    ("index_finger_pip", "index_finger_dip", "index.03"),
    ("index_finger_dip", "index_finger_tip", "index.04"),
    ("wrist", "middle_finger_mcp", "middle.01"),
    ("middle_finger_mcp", "middle_finger_pip", "middle.02"),
    ("middle_finger_pip", "middle_finger_dip", "middle.03"),
    ("middle_finger_dip", "middle_finger_tip", "middle.04"),
    ("wrist", "ring_finger_mcp", "ring.01"),
    ("ring_finger_mcp", "ring_finger_pip", "ring.02"),
    ("ring_finger_pip", "ring_finger_dip", "ring.03"),
    ("ring_finger_dip", "ring_finger_tip", "ring.04"),
    ("wrist", "pinky_mcp", "pinky.01"),
    ("pinky_mcp", "pinky_pip", "pinky.02"),
    ("pinky_pip", "pinky_dip", "pinky.03"),
    ("pinky_dip", "pinky_tip", "pinky.04"),
)

FACE_SEGMENTS = (
    ("cgt_face_rotation", "cgt_chin_rotation", "face.head"),
    ("cgt_chin_rotation", "cgt_mouth_driver", "face.jaw"),
    ("cgt_mouth_driver", "cgt_mouth_corner_driver", "face.mouth"),
    ("cgt_eye_driver.L", "cgt_eyebrow_driver.L", "face.eye.L"),
    ("cgt_eye_driver.R", "cgt_eyebrow_driver.R", "face.eye.R"),
)


def _object(name: str) -> Optional[bpy.types.Object]:
    return bpy.data.objects.get(name)


def _hide_cgt_landmarks() -> None:
    """Hide raw landmark empties without disabling them as driver sources."""
    for obj in bpy.data.objects:
        if obj.name.startswith("cgt_") and obj.name != PREVIEW_NAME:
            try:
                obj.hide_set(True)
                obj.hide_render = True
            except (AttributeError, RuntimeError):
                pass


def _unhide_preview(armature: bpy.types.Object) -> None:
    armature.hide_set(False)
    armature.hide_viewport = False
    armature.hide_render = False
    armature.show_in_front = True
    armature.data.display_type = "OCTAHEDRAL"


def _ensure_armature() -> bpy.types.Object:
    existing = bpy.data.objects.get(PREVIEW_NAME)
    if existing and existing.type == "ARMATURE":
        _unhide_preview(existing)
        return existing

    arm_data = bpy.data.armatures.new(PREVIEW_ARMATURE_NAME)
    armature = bpy.data.objects.new(PREVIEW_NAME, arm_data)
    bpy.context.scene.collection.objects.link(armature)
    armature.show_in_front = True
    arm_data.display_type = "OCTAHEDRAL"
    armature["cgt_visual_adapter"] = "mediapipe_to_skeleton"
    return armature


def _clear_constraints(pbone: bpy.types.PoseBone) -> None:
    for constraint in list(pbone.constraints):
        if constraint.name.startswith("CGT Adapter"):
            pbone.constraints.remove(constraint)


def _make_bone(
    armature: bpy.types.Object,
    source_name: str,
    target_name: str,
    bone_name: str,
) -> Optional[str]:
    source = _object(source_name)
    target = _object(target_name)
    if source is None or target is None:
        return None

    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    if bpy.context.mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")

    ebones = armature.data.edit_bones
    name = f"CGT_{bone_name}"
    bone = ebones.get(name) or ebones.new(name)
    head = source.matrix_world.translation.copy()
    tail = target.matrix_world.translation.copy()
    if (tail - head).length < 1e-5:
        tail = head + Vector((0.0, 0.05, 0.0))
    bone.head = head
    bone.tail = tail
    bone.use_deform = False

    bpy.ops.object.mode_set(mode="POSE")
    pbone = armature.pose.bones.get(name)
    if pbone is None:
        bpy.ops.object.mode_set(mode="OBJECT")
        return None

    _clear_constraints(pbone)

    copy = pbone.constraints.new("COPY_LOCATION")
    copy.name = "CGT Adapter - source location"
    copy.target = source
    copy.owner_space = "WORLD"
    copy.target_space = "WORLD"
    copy.influence = 1.0

    stretch = pbone.constraints.new("STRETCH_TO")
    stretch.name = "CGT Adapter - target landmark"
    stretch.target = target
    stretch.owner_space = "WORLD"
    stretch.target_space = "WORLD"
    stretch.influence = 1.0
    stretch.head_tail = 0.0
    return name


def _hand_name(base: str, side: str) -> str:
    # mp_hand_out creates names as cgt_<landmark>.<side>.
    return f"cgt_{base}.{side}"


def _build_segments(armature: bpy.types.Object, segments: Iterable[tuple[str, str, str]]) -> int:
    made = 0
    for source, target, label in segments:
        if _make_bone(armature, source, target, label):
            made += 1
    return made


def _build_hands(armature: bpy.types.Object) -> int:
    made = 0
    for side in ("L", "R"):
        for source, target, label in HAND_SEGMENTS:
            if _make_bone(
                armature,
                _hand_name(source, side),
                _hand_name(target, side),
                f"hand.{side}.{label}",
            ):
                made += 1
    return made


def _build_face(armature: bpy.types.Object) -> int:
    return _build_segments(armature, FACE_SEGMENTS)


def ensure_preview(detection_type: str = "HOLISTIC") -> Optional[bpy.types.Object]:
    """Create/update the visual skeleton after CGT output objects exist.

    The function is intentionally idempotent: running detection again reuses the
    same armature and refreshes its source/target constraints.  No cgt_* object is
    renamed, deleted, re-keyed, or otherwise altered.
    """
    try:
        armature = _ensure_armature()
        made = 0

        if detection_type in {"POSE", "HOLISTIC"}:
            made += _build_segments(armature, POSE_SEGMENTS)
        if detection_type in {"HAND", "HOLISTIC"}:
            made += _build_hands(armature)
        if detection_type in {"FACE", "HOLISTIC"}:
            made += _build_face(armature)

        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        _unhide_preview(armature)
        _hide_cgt_landmarks()

        # Keep the preview clearly separate from the transfer source collection.
        armature["cgt_preview_bones"] = made
        armature["cgt_preview_detection_type"] = detection_type
        logging.info("[CGT adapter] Visual skeleton ready: %s bones (%s)", made, detection_type)
        return armature
    except Exception:
        logging.exception("[CGT adapter] Failed to create visual skeleton preview; detection is left untouched.")
        return None


def show_landmarks() -> None:
    """Optional debug helper: restore visibility of raw cgt_* landmarks."""
    for obj in bpy.data.objects:
        if obj.name.startswith("cgt_") and obj.name != PREVIEW_NAME:
            try:
                obj.hide_set(False)
                obj.hide_render = False
            except (AttributeError, RuntimeError):
                pass
