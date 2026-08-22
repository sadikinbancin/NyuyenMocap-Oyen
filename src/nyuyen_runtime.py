"""NyuyenMocap/Oyen runtime extensions.

This module keeps the upstream BlendArMocap detection and transfer pipeline intact
while adding a safe Blender-5.x bootstrap, an optional viewport skeleton preview,
and a one-click Rigify transfer helper.
"""
from __future__ import annotations

import logging
from pathlib import Path

import bpy
from mathutils import Vector
from .cgt_core.cgt_interface import cgt_core_panel

LOG = logging.getLogger("NyuyenMocap")

SKELETON_COLLECTION = "CGT_VISUAL_SKELETON"
SKELETON_OBJECT = "CGT_Visual_Skeleton"
RIGIFY_CONFIG = "Rigify_Humanoid_DefaultFace_v0.6.1"

POSE_PAIRS = (
    ("pelvis", "cgt_left_hip", "cgt_right_hip"),
    ("spine", "cgt_hip_center", "cgt_shoulder_center"),
    ("neck", "cgt_shoulder_center", "cgt_nose"),
    ("upper_arm.L", "cgt_left_shoulder", "cgt_left_elbow"),
    ("forearm.L", "cgt_left_elbow", "cgt_left_wrist"),
    ("hand.L", "cgt_left_wrist", "cgt_left_index"),
    ("upper_arm.R", "cgt_right_shoulder", "cgt_right_elbow"),
    ("forearm.R", "cgt_right_elbow", "cgt_right_wrist"),
    ("hand.R", "cgt_right_wrist", "cgt_right_index"),
    ("thigh.L", "cgt_left_hip", "cgt_left_knee"),
    ("shin.L", "cgt_left_knee", "cgt_left_ankle"),
    ("foot.L", "cgt_left_ankle", "cgt_left_foot_index"),
    ("thigh.R", "cgt_right_hip", "cgt_right_knee"),
    ("shin.R", "cgt_right_knee", "cgt_right_ankle"),
    ("foot.R", "cgt_right_ankle", "cgt_right_foot_index"),
)

HAND_CHAINS = (
    ("thumb", ("thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip")),
    ("index", ("index_mcp", "index_pip", "index_dip", "index_tip")),
    ("middle", ("middle_mcp", "middle_pip", "middle_dip", "middle_tip")),
    ("ring", ("ring_mcp", "ring_pip", "ring_dip", "ring_tip")),
    ("pinky", ("pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip")),
)

_REGISTERED = False
_ORIGINAL_CANCEL = None
_RUNTIME_CLASSES = []


def sanitize_source_tree() -> int:
    """Resolve accidental Git conflict markers by keeping the HEAD side."""
    root = Path(__file__).resolve().parent
    package_root = root.parent
    changed = 0

    for path in package_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".py", ".md", ".rst"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if "<<<<<<< HEAD" not in text:
            continue

        lines = text.splitlines(keepends=True)
        out = []
        in_conflict = False
        keep_head = True
        saw_end = False
        for line in lines:
            if line.startswith("<<<<<<< HEAD"):
                in_conflict = True
                keep_head = True
                saw_end = False
                continue
            if in_conflict and line.startswith("======="):
                keep_head = False
                continue
            if in_conflict and line.startswith(">>>>>>> "):
                in_conflict = False
                keep_head = True
                saw_end = True
                continue
            if not in_conflict or keep_head:
                out.append(line)

        if in_conflict or not saw_end:
            LOG.error("Skipped malformed conflict file: %s", path)
            continue

        new_text = "".join(out)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8", newline="")
            changed += 1
            LOG.warning("Resolved stale Git merge markers in %s", path.relative_to(package_root))

    return changed


def _driver(name: str):
    return bpy.data.objects.get(name)


def _world_pos(name: str):
    obj = _driver(name)
    return obj.matrix_world.translation.copy() if obj else None


def _ensure_collection():
    collection = bpy.data.collections.get(SKELETON_COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(SKELETON_COLLECTION)
        bpy.context.scene.collection.children.link(collection)
    return collection


def _remove_skeleton():
    collection = bpy.data.collections.get(SKELETON_COLLECTION)
    if collection:
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for child in list(collection.children):
            collection.children.unlink(child)
            bpy.data.collections.remove(child)
        bpy.data.collections.remove(collection)
    arm_data = bpy.data.armatures.get(SKELETON_OBJECT)
    if arm_data and arm_data.users == 0:
        bpy.data.armatures.remove(arm_data)


def _pairs():
    result = []
    for bone_name, head_name, tail_name in POSE_PAIRS:
        if _world_pos(head_name) is not None and _world_pos(tail_name) is not None:
            result.append((bone_name, head_name, tail_name))
    for side in ("L", "R"):
        for label, chain in HAND_CHAINS:
            for idx in range(len(chain) - 1):
                head = f"cgt_{chain[idx]}.{side}"
                tail = f"cgt_{chain[idx + 1]}.{side}"
                if _world_pos(head) is not None and _world_pos(tail) is not None:
                    result.append((f"{label}.{side}.{idx + 1}", head, tail))
    return result


def rebuild_visual_skeleton():
    pairs = _pairs()
    if not pairs:
        return None
    _remove_skeleton()
    collection = _ensure_collection()
    arm_data = bpy.data.armatures.new(SKELETON_OBJECT)
    arm_data.display_type = 'OCTAHEDRAL'
    arm_obj = bpy.data.objects.new(SKELETON_OBJECT, arm_data)
    arm_obj.show_in_front = True
    arm_obj.display_type = 'WIRE'
    collection.objects.link(arm_obj)

    old_active = bpy.context.view_layer.objects.active
    old_selected = list(bpy.context.selected_objects)
    try:
        bpy.ops.object.select_all(action='DESELECT')
        arm_obj.select_set(True)
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='EDIT')
        created = []
        for bone_name, head_name, tail_name in pairs:
            head = _world_pos(head_name)
            tail = _world_pos(tail_name)
            if head is None or tail is None:
                continue
            if (tail - head).length < 1e-5:
                tail = head + Vector((0.0, 0.05, 0.0))
            bone = arm_data.edit_bones.new(bone_name)
            bone.head = head
            bone.tail = tail
            bone.use_deform = False
            created.append((bone.name, head_name, tail_name))
        bpy.ops.object.mode_set(mode='POSE')
        for bone_name, head_name, tail_name in created:
            pose_bone = arm_obj.pose.bones.get(bone_name)
            head_driver = _driver(head_name)
            tail_driver = _driver(tail_name)
            if not pose_bone or not head_driver or not tail_driver:
                continue
            copy = pose_bone.constraints.new('COPY_LOCATION')
            copy.name = 'CGT Head Follow'
            copy.target = head_driver
            copy.target_space = 'WORLD'
            copy.owner_space = 'WORLD'
            stretch = pose_bone.constraints.new('STRETCH_TO')
            stretch.name = 'CGT Tail Follow'
            stretch.target = tail_driver
            stretch.head_tail = 0.0
            stretch.influence = 1.0
        bpy.ops.object.mode_set(mode='OBJECT')
        return arm_obj
    except Exception:
        LOG.exception("Unable to build visual skeleton")
        try:
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        _remove_skeleton()
        return None
    finally:
        try:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in old_selected:
                if obj and obj.name in bpy.data.objects:
                    obj.select_set(True)
            if old_active and old_active.name in bpy.data.objects:
                bpy.context.view_layer.objects.active = old_active
        except Exception:
            pass


def set_driver_landmarks_hidden(hidden=True):
    root = bpy.data.collections.get("cgt_DRIVERS")
    if not root:
        return
    for obj in root.all_objects:
        if obj.name == SKELETON_OBJECT:
            continue
        try:
            obj.hide_set(hidden)
        except RuntimeError:
            obj.hide_viewport = hidden


def _post_detection(context):
    try:
        rebuild_visual_skeleton()
        set_driver_landmarks_hidden(True)
    except Exception:
        LOG.exception("Post-detection visual cleanup failed; preserving cgt_* drivers")


def _wrap_detection_cancel():
    global _ORIGINAL_CANCEL
    if _ORIGINAL_CANCEL is not None:
        return
    try:
        from .cgt_mediapipe import cgt_mp_detection_operator as det
    except Exception:
        LOG.exception("Could not import detection operator for runtime hook")
        return
    cls = det.WM_CGT_MP_modal_detection_operator
    _ORIGINAL_CANCEL = cls.cancel

    def wrapped_cancel(self, context):
        result = _ORIGINAL_CANCEL(self, context)
        if result == {'FINISHED'}:
            _post_detection(context)
            _prepare_transfer_defaults(context)
        return result

    cls.cancel = wrapped_cancel


def _prepare_transfer_defaults(context):
    user = getattr(context.scene, 'cgtinker_transfer', None)
    if user is None:
        return
    drivers = bpy.data.collections.get('cgt_DRIVERS')
    if drivers is not None:
        try:
            user.selected_driver_collection = drivers
        except Exception:
            pass
    try:
        user.transfer_types = RIGIFY_CONFIG
    except Exception:
        pass


class NYU_OT_RebuildSkeleton(bpy.types.Operator):
    bl_idname = "nyu.rebuild_visual_skeleton"
    bl_label = "Rebuild Skeleton Preview"

    def execute(self, context):
        skeleton = rebuild_visual_skeleton()
        if skeleton is None:
            self.report({'WARNING'}, "No cgt_* body/hand drivers found. Run detection first.")
            return {'CANCELLED'}
        set_driver_landmarks_hidden(True)
        return {'FINISHED'}


class NYU_OT_ShowLandmarks(bpy.types.Operator):
    bl_idname = "nyu.show_landmarks"
    bl_label = "Show Mocap Points"

    def execute(self, context):
        set_driver_landmarks_hidden(False)
        return {'FINISHED'}


class NYU_OT_HideLandmarks(bpy.types.Operator):
    bl_idname = "nyu.hide_landmarks"
    bl_label = "Hide Mocap Points"

    def execute(self, context):
        set_driver_landmarks_hidden(True)
        return {'FINISHED'}


class NYU_OT_AutoTransfer(bpy.types.Operator):
    bl_idname = "nyu.auto_transfer_to_selected"
    bl_label = "Auto Transfer to Selected Rig"

    def execute(self, context):
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, "Switch to Object Mode first.")
            return {'CANCELLED'}
        rigs = [o for o in context.selected_objects if o.type == 'ARMATURE' and o.name != SKELETON_OBJECT]
        if len(rigs) != 1:
            self.report({'ERROR'}, "Select exactly one generated Rigify armature (Oyen).")
            return {'CANCELLED'}
        user = getattr(context.scene, 'cgtinker_transfer', None)
        drivers = bpy.data.collections.get('cgt_DRIVERS')
        if user is None or drivers is None:
            self.report({'ERROR'}, "Run MediaPipe detection first so cgt_DRIVERS exists.")
            return {'CANCELLED'}
        user.selected_rig = rigs[0]
        user.selected_driver_collection = drivers
        user.transfer_types = RIGIFY_CONFIG
        try:
            result = bpy.ops.button.cgt_object_apply_properties()
        except Exception as exc:
            LOG.exception("Rigify transfer failed")
            self.report({'ERROR'}, f"Transfer failed: {exc}")
            return {'CANCELLED'}
        if 'CANCELLED' in result:
            self.report({'ERROR'}, "Transfer was cancelled. Check the Blender Console for details.")
            return {'CANCELLED'}
        context.view_layer.update()
        self.report({'INFO'}, f"Mocap transferred to {rigs[0].name}.")
        return {'FINISHED'}


class NYU_PT_Runtime(cgt_core_panel.DefaultPanel, bpy.types.Panel):
    bl_label = "NyuyenMocap"
    bl_parent_id = "UI_PT_CGT_Panel"
    bl_idname = "NYU_PT_Runtime"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator(NYU_OT_RebuildSkeleton.bl_idname, icon='ARMATURE_DATA')
        row.operator(NYU_OT_AutoTransfer.bl_idname, icon='DRIVER')
        row = layout.row()
        row.operator(NYU_OT_HideLandmarks.bl_idname, icon='HIDE_OFF')
        row.operator(NYU_OT_ShowLandmarks.bl_idname, icon='HIDE_ON')
        layout.label(text="cgt_* drivers remain the real transfer source.")
        layout.label(text="White skeleton is viewport-only.")


def register_runtime_features():
    global _REGISTERED
    if _REGISTERED:
        return
    _wrap_detection_cancel()
    classes = [NYU_OT_RebuildSkeleton, NYU_OT_ShowLandmarks, NYU_OT_HideLandmarks, NYU_OT_AutoTransfer, NYU_PT_Runtime]
    for cls in classes:
        bpy.utils.register_class(cls)
        _RUNTIME_CLASSES.append(cls)
    _REGISTERED = True


def unregister_runtime_features():
    global _REGISTERED, _ORIGINAL_CANCEL
    if not _REGISTERED:
        return
    for cls in reversed(_RUNTIME_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    _RUNTIME_CLASSES.clear()
    try:
        from .cgt_mediapipe import cgt_mp_detection_operator as det
        if _ORIGINAL_CANCEL is not None:
            det.WM_CGT_MP_modal_detection_operator.cancel = _ORIGINAL_CANCEL
    except Exception:
        LOG.exception("Could not restore detection operator")
    _ORIGINAL_CANCEL = None
    _REGISTERED = False
