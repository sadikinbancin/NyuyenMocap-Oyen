import bpy

from . import cgt_dependencies
from ..cgt_core.cgt_interface import cgt_core_panel


class CGT_PT_MP_Detection(cgt_core_panel.DefaultPanel, bpy.types.Panel):
    bl_label = "Mediapipe"
    bl_parent_id = "UI_PT_CGT_Panel"
    bl_idname="UI_PT_CGT_Detection"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'POSE'} and all(cgt_dependencies.dependencies_installed)

    def movie_panel(self, user):
        layout = self.layout
        layout.row().prop(user, "mov_data_path")
        layout.row().prop(user, "key_frame_step")
        layout.row().prop(user, "enum_detection_type")
        if user.modal_active:
            layout.row().operator("wm.cgt_feature_detection_operator", text="Stop Detection", icon='CANCEL')
        else:
            layout.row().operator("wm.cgt_feature_detection_operator", text="Detect Clip", icon='IMPORT')

    def webcam_panel(self, user):
        layout = self.layout
        layout.row().prop(user, "webcam_input_device")
        layout.row().prop(user, "key_frame_step")
        layout.row().prop(user, "enum_detection_type")
        if user.modal_active:
            layout.row().operator("wm.cgt_feature_detection_operator", text="Stop Detection", icon='RADIOBUT_ON')
        else:
            layout.row().operator("wm.cgt_feature_detection_operator", text="Start Detection", icon='RADIOBUT_OFF')

    def draw(self, context):
        user = context.scene.cgtinker_mediapipe  # noqa
        layout = self.layout
        layout.label(text='Detect')
        layout.row().prop(user, "detection_input_type")

        if user.detection_input_type == "movie":
            self.movie_panel(user)
        else:
            self.webcam_panel(user)


class CGT_PT_MP_DetectorProperties(cgt_core_panel.DefaultPanel, bpy.types.Panel):
    bl_label = "Advanced"
    bl_parent_id = "UI_PT_CGT_Detection"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        user = context.scene.cgtinker_mediapipe # noqa
        layout = self.layout

        if user.enum_detection_type == 'HAND':
            layout.row().prop(user, "hand_model_complexity")
        elif user.enum_detection_type == 'FACE':
            # layout.row().prop(user, "refine_face_landmarks")
            pass
        elif user.enum_detection_type == 'POSE':
            layout.row().prop(user, "pose_model_complexity")
        elif user.enum_detection_type == 'HOLISTIC':
            layout.row().prop(user, "holistic_model_complexity")

        layout.row().prop(user, "min_detection_confidence", slider=True)


<<<<<<< HEAD
class CGT_PT_MP_Leveling(cgt_core_panel.DefaultPanel, bpy.types.Panel):
    bl_label = "Nivelado de cámara"
    bl_parent_id = "UI_PT_CGT_Detection"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        user = context.scene.cgtinker_mediapipe  # noqa
        return user.enum_detection_type in ('POSE', 'HOLISTIC') and all(cgt_dependencies.dependencies_installed)

    def draw(self, context):
        user = context.scene.cgtinker_mediapipe  # noqa
        layout = self.layout

        layout.row().label(
            text="Corrige la inclinación de la cámara respecto a la gravedad.")
        layout.row().prop(user, "debug_leveling", text="Imprimir ángulo en consola")

        row = layout.row()
        row.enabled = not user.modal_active
        row.operator("wm.cgt_leveling_diagnostic_operator",
                      text="Diagnóstico de nivelado", icon='CON_ROTLIMIT')

        layout.separator()
        layout.row().label(text="Si aún queda inclinación, ajusta a mano:")
        layout.row().prop(user, "manual_leveling_offset")


class CGT_PT_MP_Smoothing(cgt_core_panel.DefaultPanel, bpy.types.Panel):
    bl_label = "Suavizado (jitter)"
    bl_parent_id = "UI_PT_CGT_Detection"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        user = context.scene.cgtinker_mediapipe  # noqa
        return user.enum_detection_type in ('POSE', 'HOLISTIC') and all(cgt_dependencies.dependencies_installed)

    def draw(self, context):
        user = context.scene.cgtinker_mediapipe  # noqa
        layout = self.layout

        layout.row().prop(user, "smoothing_enabled")

        col = layout.column()
        col.enabled = user.smoothing_enabled
        col.row().prop(user, "smoothing_amount", slider=True)
        col.row().prop(user, "foot_smoothing_amount", slider=True)
        col.row().label(text="Más alto = menos jitter, pero más lag.", icon='INFO')


=======
>>>>>>> 3cd40c352ef1d842c922acb72229314f99bffddc
class CGT_PT_MP_Warning(cgt_core_panel.DefaultPanel, bpy.types.Panel):
    bl_label = "Mediapipe"
    bl_parent_id = "UI_PT_CGT_Panel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_idname="UI_PT_CGT_Detection_Warning"

    @classmethod
    def poll(cls, context):
        return not all(cgt_dependencies.dependencies_installed)

    def draw(self, context):
        layout = self.layout

        lines = [f"Please install the missing dependencies for BlendArMocap.",
                 f"1. Open the preferences (Edit > Preferences > Add-ons).",
                 f"2. Search for the BlendArMocap add-on.",
                 f"3. Open the details section of the add-on.",
                 f"4. Click on the 'install dependencies' button."]

        for line in lines:
            layout.label(text=line)


classes = [
    CGT_PT_MP_Warning,
    CGT_PT_MP_Detection,
<<<<<<< HEAD
    CGT_PT_MP_DetectorProperties,
    CGT_PT_MP_Leveling,
    CGT_PT_MP_Smoothing,
=======
    CGT_PT_MP_DetectorProperties
>>>>>>> 3cd40c352ef1d842c922acb72229314f99bffddc
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
