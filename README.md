# BlendArMocap NX

*[Leer esto en español](README_es.md)*

**Fork / port of [BlendArMocap](https://github.com/cgtinker/BlendArMocap) (by cgtinker) updated for the modern MediaPipe Tasks API and Blender 4.2+.**

The original BlendArMocap architecture is preserved: MediaPipe detection, `cgt_*` driver objects, smoothing/leveling, and the existing JSON-based transfer system remain the source of truth.

> The original design, retargeting system, and the majority of the codebase belong to cgtinker. This fork is intended to keep the project usable with modern Blender/Python/MediaPipe versions. GPLv3, same as the original.

## What's included

### MediaPipe Tasks API

The Pose, Hand, Face, and Holistic paths use the modern MediaPipe Tasks API while retaining the original CGT node architecture. Video mode uses increasing timestamps so tracking can remain temporally consistent.

### Safe visual skeleton adapter

After MediaPipe creates the normal `cgt_*` landmarks, the add-on can automatically create a separate `CGT_Visual_Skeleton` armature preview.

The pipeline is:

```text
Video / Webcam
    -> MediaPipe
    -> original cgt_* landmarks
    -> safe visual adapter
    -> CGT_Visual_Skeleton
    -> existing BlendArMocap transfer
    -> target Rigify/Oyen rig
```

The adapter is deliberately isolated from the detection and transfer code. It does not rename, delete, re-key, or replace the original `cgt_*` objects. The preview bones follow those original objects through Blender constraints, so the raw CGT data remains available to the existing transfer system.

Raw `cgt_*` landmarks are hidden from the viewport automatically when the preview is created, while remaining available to drivers and transfer. A debug helper can restore their visibility when needed.

The preview supports body pose and hand chains, with a small set of face orientation/jaw/eye relationships for readability. It is a visual/diagnostic adapter, not a replacement for the existing transfer configuration.

### Generic transfer type

`Generic_MetaRig_Basic.json` provides a basic humanoid mapping for rigs using conventional bone names such as `upper_arm.L`, `forearm.L`, `thigh.L`, and `shin.L`. The original Rigify transfer configuration remains available for generated Rigify rigs.

## Installation

1. In Blender, open `Preferences > Add-ons > Install from Disk` and select the ZIP of this repository.
2. Enable the add-on.
3. Open the add-on's dependency controls and install the required MediaPipe dependencies if they are not already available.
4. In `3D View > Tool > BlendArMocap > MediaPipe`, choose Webcam or Video and the desired detection type.
5. Start detection. The normal `cgt_*` data is generated first; the visual skeleton is then created automatically when the required landmarks exist.
6. Use the existing Transfer panel to load the appropriate transfer configuration and transfer the animation to the target armature.

Requires Blender 4.2+ and the Python version bundled with Blender. Development/testing has primarily targeted Windows and recent Blender LTS releases.

## Validation

The repository includes GitHub Actions validation for Python syntax, JSON data files, and unresolved Git merge markers. The validation is intentionally independent of MediaPipe runtime detection so source-level regressions are caught before release.

## Credits

- Original author and design: cgtinker — [BlendArMocap](https://github.com/cgtinker/BlendArMocap).
- Modern MediaPipe Tasks API port and stability work: this fork.
- License: GPLv3.
