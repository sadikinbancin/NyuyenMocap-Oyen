# PORTING_NOTES.md — Technical breakdown of the modern MediaPipe port

*[Leer esto en español](PORTING_NOTES_es.md)*

This document records the important architectural changes in the fork so future maintenance can be done without accidentally breaking the original BlendArMocap pipeline.

## MediaPipe Tasks API

The original BlendArMocap detector layer used the deprecated `mediapipe.solutions` API. The fork uses the modern MediaPipe Tasks API with separate Pose, Hand, Face, and combined Holistic-compatible detector paths.

The detector wrappers keep the existing CGT node-chain interface, so the rest of the add-on continues to receive the same landmark-array shape expected by the original output nodes.

For video/live tracking, the detector path uses video timestamps rather than treating every frame as an unrelated still image. This preserves temporal continuity and reduces visible jitter.

## Dependency hardening

`mediapipe` is pinned to the tested version in `requirements.txt`. OpenCV is not installed as a second competing package by the add-on because multiple OpenCV distributions sharing the `cv2` import can conflict on Windows.

Dependency metadata checks are guarded so incomplete package metadata does not abort registration of the entire add-on.

## Generic transfer configuration

`src/cgt_transfer/data/Generic_MetaRig_Basic.json` provides a basic mapping for conventional humanoid bone names such as `upper_arm.L`, `forearm.L`, `thigh.L`, `shin.L`, `head`, and `spine.003`.

The original `Rigify_Humanoid_DefaultFace_v0.6.1.json` remains available for generated Rigify rigs. The two configurations are intentionally kept separate because generated Rigify control bones are not the same as raw metarig deform bones.

## Safe visual skeleton adapter

The new `src/cgt_mediapipe/cgt_skeleton_preview.py` module is an isolated visualization layer. It does not replace the original CGT landmark objects and does not change the existing transfer implementation.

The runtime flow is:

```text
MediaPipe
  -> original cgt_* landmark objects
  -> safe visual adapter
  -> CGT_Visual_Skeleton armature
  -> existing BlendArMocap transfer system
  -> target armature
```

The adapter creates a separate non-deforming armature. Each preview bone follows the corresponding source and target `cgt_*` landmarks through Blender constraints. Because the source objects remain intact, the existing driver and transfer system continues to operate on the original data.

When the preview is created, raw `cgt_*` landmark objects are hidden from the viewport but remain present and usable by drivers. This prevents the viewport from being filled with the small black landmark dots while preserving the underlying animation data.

The preview is idempotent: starting another detection run reuses `CGT_Visual_Skeleton` instead of creating a new skeleton for every clip.

## What was deliberately left untouched

The following areas remain the original transfer/detection architecture unless a change was strictly required for Blender/MediaPipe compatibility:

- CGT node chains and output nodes.
- `cgt_*` naming and collection conventions.
- The existing driver/constraint transfer implementation.
- Existing transfer JSON formats.
- MediaPipe landmark data as the source of truth.

The visual adapter is therefore a presentation layer between detection and the existing transfer workflow, not a rewrite of either subsystem.

## Future work

- Add richer hand/head orientation solving to the visual preview.
- Extend the generic transfer configuration to more hand and face controls.
- Add Blender-runtime integration tests in addition to source/JSON validation.
- Benchmark tracking quality and performance on the target Windows/Blender environment.
