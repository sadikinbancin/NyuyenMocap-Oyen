import bpy


class MP_PG_Properties(bpy.types.PropertyGroup):
    enum_detection_type: bpy.props.EnumProperty(
        name="Target",
        description="Select detection type tracking.",
        items=(
            ("HAND", "Hands", ""),
            ("FACE", "Face", ""),
            ("POSE", "Pose", ""),
            ("HOLISTIC", "Holistic", ""),
        )
    )

    refine_face_landmarks: bpy.props.BoolProperty(
        name="Refine Face Landmarks", default=False,
        description="Whether to further refine the landmark coordinates around the eyes and lips, and output additional landmarks around the irises by applying the Attention Mesh Model. Default to false.")

    holistic_model_complexity: bpy.props.IntProperty(
        name="Model Complexity", default=1, min=0, max=1,
        description="Complexity of the pose landmark model: 0 or 1. Landmark accuracy and inference latency generally go up with model complexity. Default to 1.")

    pose_model_complexity: bpy.props.IntProperty(
        name="Model Complexity", default=1, min=0, max=1,
        description="Complexity of the pose landmark model: 0 or 1. Landmark accuracy and inference latency generally go up with model complexity. Default to 1.")

    hand_model_complexity: bpy.props.IntProperty(
        name="Model Complexity", default=1, min=0, max=1,
        description="Complexity of the hand landmark model: 0 or 1. Landmark accuracy and inference latency generally go up with model complexity. Default to 1.")

    min_detection_confidence: bpy.props.FloatProperty(
        name="Min Tracking Confidence", default=0.5, min=0.0, max=1.0,
        description="Minimum confidence value from the detection model for the detection to be considered successful. Default to 0.5.")

    mov_data_path: bpy.props.StringProperty(
        name="File Path",
        description="File path to .mov file.",
        default='*.mov;*mp4',
        options={'HIDDEN'},
        maxlen=1024,
        subtype='FILE_PATH'
    )

    enum_stream_type: bpy.props.EnumProperty(
        name="Stream Backend",
        description="Sets Stream backend.",
        items=(("0", "default", ""), ("1", "capdshow", ""))
    )

    enum_stream_dim: bpy.props.EnumProperty(
        name="Stream Dimensions",
        description="Video stream dimensions.",
        items=(
            ("sd", "720x480 - recommended", ""),
            ("hd", "1240x720 - experimental", ""),
            ("fhd", "1920x1080 - experimental", ""),
        )
    )

    detection_input_type: bpy.props.EnumProperty(
        name="Type",
        description="Select input type.",
        items=(("movie", "Movie", ""), ("stream", "Webcam", ""))
    )

    webcam_input_device: bpy.props.IntProperty(
        name="Webcam Device Slot", description="Select Webcam device.", min=0, max=4, default=0
    )

    key_frame_step: bpy.props.IntProperty(
        name="Key Step", description="Select keyframe step rate.", min=1, max=12, default=4
    )

    modal_active: bpy.props.BoolProperty(
        name="modal_active", description="Check if operator is running", default=False
    )

    debug_leveling: bpy.props.BoolProperty(
        name="Debug Leveling",
        description="Print camera leveling diagnostics in Blender's console.",
        default=False
    )

    manual_leveling_offset: bpy.props.FloatProperty(
        name="Ajuste manual (grados)",
        description="Additional camera-level correction in degrees.",
        default=0.0, min=-45.0, max=45.0
    )

    smoothing_enabled: bpy.props.BoolProperty(
        name="Suavizar Jitter",
        description="Apply smoothing to pose landmarks to reduce jitter.",
        default=True
    )

    smoothing_amount: bpy.props.FloatProperty(
        name="Suavizado general",
        description="General smoothing strength. Higher values reduce jitter but add lag.",
        default=0.55, min=0.0, max=1.0, subtype='FACTOR'
    )

    foot_smoothing_amount: bpy.props.FloatProperty(
        name="Suavizado de pies/raíz",
        description="Extra smoothing for feet, root, shoulders and hips.",
        default=0.85, min=0.0, max=1.0, subtype='FACTOR'
    )

    local_user: bpy.props.BoolProperty(
        name="Local user",
        description="Install to local user and not to Blender's Python site packages.",
        default=False,
    )


classes = [MP_PG_Properties]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cgtinker_mediapipe = bpy.props.PointerProperty(type=MP_PG_Properties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, "cgtinker_mediapipe"):
        del bpy.types.Scene.cgtinker_mediapipe
