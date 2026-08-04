# BlendArMocap NX

<<<<<<< HEAD
**Fork / port de [BlendArMocap](https://github.com/cgtinker/BlendArMocap) (por [cgtinker](https://github.com/cgtinker)) actualizado para funcionar con la MediaPipe Tasks API moderna, en Blender 4.2+ (probado en 4.5 LTS).**

BlendArMocap original dejó de funcionar en instalaciones nuevas de Blender/Python porque dependía de `mediapipe.solutions` (Pose, Hands, Face Mesh, Holistic), una API que Google deprecó y removió de las versiones actuales de `mediapipe`. Este fork reemplaza esa capa de detección por la **Tasks API** (`PoseLandmarker`, `HandLandmarker`, `FaceLandmarker`) manteniendo intacta toda la arquitectura original: el sistema de nodos de captura, la colección de empties `cgt_*`, y el sistema de transferencia de animación a un rig vía archivos de configuración JSON.

> El diseño original, el sistema de retargeting y la gran mayoría del código base son de **cgtinker**. Este repositorio existe para mantener el addon funcionando en Blender/Python/MediaPipe actuales — no para reclamar autoría. Licencia GPLv3, igual que el original (ver `LICENSE`). El repo original está marcado como *discontinued* por su autor; este fork nace de esa nota.

---

## Qué cambia respecto al original

### 1. Detección: `mediapipe.solutions` → Tasks API
Los 4 detectores (`mp_pose_detector.py`, `mp_hand_detector.py`, `mp_face_detector.py`, `mp_holistic_detector.py`) fueron reescritos sobre `PoseLandmarker`, `HandLandmarker` y `FaceLandmarker` de `mediapipe.tasks.python.vision`, con clases `*Compat` que exponen la misma interfaz `.process(frame)` que el código original esperaba — el resto de la cadena de nodos no necesitó cambios.

- **`RunningMode.VIDEO`, no `IMAGE`.** La Tasks API ofrece modo `IMAGE` (cada frame aislado, sin memoria del anterior) y `VIDEO` (timestamps crecientes, continuidad de tracking entre frames). Usar `IMAGE` en captura en vivo produce temblor notable; este port usa `VIDEO` con un contador de timestamps monotónico por landmarker.
- **No existe un modelo "Holistic" único en la Tasks API.** `mp_holistic_detector.py` corre Pose + Face + Hand por separado sobre el mismo frame y combina los resultados con la misma forma que producía el `HolisticDetector` original.
- Los modelos `.task` se descargan automáticamente la primera vez que se necesitan (bucket público de Google) — a diferencia de la API vieja, que los traía embebidos.

### 2. Instalación de dependencias, más resiliente
- `mediapipe` fijado a `0.10.33` (versión probada, no "la última disponible") — evita que cada reinstalación traiga una cadena de dependencias distinta.
- **Ya no se instala `opencv-python` por separado.** `mediapipe` trae `opencv-contrib-python` como dependencia propia; instalar además otra variante de opencv corrompía el paquete `cv2` en Windows (ambas comparten el mismo nombre de import y pip no sabe que son mutuamente excluyentes) — este era el origen del error *"module 'cv2' has no attribute 'VideoCapture'"* incluso en instalaciones nuevas.
- El bloque de `cgt_dependencies.py` que verifica versiones instaladas corre **al importar el módulo** (o sea, al activar el addon). Antes, si la metadata de un paquete estaba incompleta (típico tras reinstalaciones manuales previas), una excepción ahí tumbaba el registro de **todo el addon** con un `RuntimeError` genérico. Ahora cada paso está blindado con try/except y valores de respaldo seguros.

### 3. Nuevo Transfer Type: `Generic_MetaRig_Basic`
El único config que traía el addon original (`Rigify_Humanoid_DefaultFace_v0.6.1.json`) apunta a huesos de control que **solo existen en un rig ya generado por Rigify** (`hand_ik.L`, `forearm_tweak.L`, `upper_arm_fk.L`, etc.). Usarlo sobre el metarig sin generar aborta en silencio hueso por hueso — sin ningún error visible, simplemente no se crea ningún constraint.

`Generic_MetaRig_Basic.json` es una alternativa pensada para animar directo un metarig sin generar (huesos `upper_arm.L`, `forearm.L`, `thigh.L`, `shin.L`, `head`...). Usa el mismo mecanismo de drivers del original pero con constraints `Damped Track` en vez de `Copy Location`/`Copy Rotation` sobre huesos IK: cada hueso apunta hacia la siguiente articulación de la cadena. Cubre brazos, piernas, cabeza y una aproximación simple de torso (10 landmarks; no incluye dedos ni cara todavía — ver *Limitaciones*).

---

## Instalación

1. `Preferences > Add-ons > Install from Disk` → selecciona el `.zip` de este repo.
2. Activa el addon. Ve a la pestaña de dependencias (dentro de las preferencias del addon) y dale a **Install dependencies** — instala `mediapipe==0.10.33` (que a su vez trae `opencv-contrib-python` y `numpy`) con `pip --user`, sin requerir permisos de administrador.
3. Si algo quedó instalado a medias por una corrida anterior de una versión previa del addon, usa el botón de reparación disponible en el mismo panel.

Requiere Blender 4.2 o superior (probado en 4.5 LTS). Python 3.11+ (el que trae Blender).

---

## Uso rápido

1. **3D View > Tool > BlendArMocap > MediaPipe**: elige Webcam o Video, tipo de detección (Pose/Hands/Face), dale a *Start Detection*.
2. Esto crea una jerarquía de empties `cgt_*` bajo la colección `cgt_DRIVERS`.
3. **Transfer**: elige tu Armature destino, la colección de Drivers (`cgt_POSE` / `cgt_HANDS` / `cgt_FACE`), y el Transfer Type:
   - `Rigify_Humanoid_DefaultFace_v0.6.1` → para un rig **ya generado** por Rigify (botón *Generate Rig*).
   - `Generic_MetaRig_Basic` → para el metarig crudo (sin generar) o un rig con nomenclatura de huesos similar.
=======
It was possible to port this for modern Blender and Mediapipe thanks to Claude.

*[Leer esto en español](README_es.md)*

**Fork / port of [BlendArMocap](https://github.com/cgtinker/BlendArMocap) (by [cgtinker](https://github.com/cgtinker)) updated to work with the modern MediaPipe Tasks API, on Blender 4.2+ (tested on 4.5 LTS).**

The original BlendArMocap stopped working on fresh Blender/Python installs because it relied on `mediapipe.solutions` (Pose, Hands, Face Mesh, Holistic), an API that Google has deprecated and removed from current `mediapipe` releases. This fork replaces that detection layer with the **Tasks API** (`PoseLandmarker`, `HandLandmarker`, `FaceLandmarker`) while keeping the original architecture intact: the capture node system, the `cgt_*` empties collection, and the animation transfer system that drives a rig through JSON config files.

> Original design, the retargeting system, and the vast majority of the codebase belong to **cgtinker**. This repository exists to keep the addon working with current Blender/Python/MediaPipe versions — not to claim authorship. GPLv3 license, same as the original (see `LICENSE`). The original repo is marked *discontinued* by its author; this fork grew out of that note.

---

## What's different from the original

### 1. Detection: `mediapipe.solutions` → Tasks API
The 4 detectors (`mp_pose_detector.py`, `mp_hand_detector.py`, `mp_face_detector.py`, `mp_holistic_detector.py`) were rewritten on top of `PoseLandmarker`, `HandLandmarker` and `FaceLandmarker` from `mediapipe.tasks.python.vision`, with `*Compat` wrapper classes that expose the same `.process(frame)` interface the original code expected — the rest of the node chain needed no changes.

- **`RunningMode.VIDEO`, not `IMAGE`.** The Tasks API offers `IMAGE` mode (each frame analyzed in isolation, no memory of the previous one) and `VIDEO` mode (increasing timestamps, tracking continuity between frames). Using `IMAGE` during live capture produces noticeable jitter; this port uses `VIDEO` with a monotonic timestamp counter per landmarker.
- **There is no single "Holistic" model in the Tasks API.** `mp_holistic_detector.py` runs Pose + Face + Hand separately on the same frame and combines the results into the same shape the original `HolisticDetector` produced.
- The `.task` model files are downloaded automatically the first time they're needed (from Google's public bucket) — unlike the old API, which shipped them embedded.

### 2. More resilient dependency installation
- `mediapipe` pinned to `0.10.33` (a tested version, not "whatever's latest") — avoids each reinstall pulling a different dependency chain.
- **`opencv-python` is no longer installed separately.** `mediapipe` already brings `opencv-contrib-python` as its own dependency; installing another opencv variant on top used to corrupt the `cv2` package on Windows (both share the same import name and pip has no idea they're mutually exclusive) — this was the source of the *"module 'cv2' has no attribute 'VideoCapture'"* error, even on fresh installs.
- The block in `cgt_dependencies.py` that checks installed versions runs **at module import time** (i.e. when the addon is enabled). Previously, if a package's metadata was incomplete (common after several manual reinstalls), an exception there would take down registration of **the entire addon** with a generic `RuntimeError`. Every step is now wrapped in try/except with safe fallback values.

### 3. New Transfer Type: `Generic_MetaRig_Basic`
The only config shipped with the original addon (`Rigify_Humanoid_DefaultFace_v0.6.1.json`) targets control bones that **only exist on an already-generated Rigify rig** (`hand_ik.L`, `forearm_tweak.L`, `upper_arm_fk.L`, etc.). Using it on the raw (ungenerated) metarig silently aborts bone by bone — no visible error, it simply never creates any constraint.

`Generic_MetaRig_Basic.json` is an alternative meant to animate a raw, ungenerated metarig directly (bones like `upper_arm.L`, `forearm.L`, `thigh.L`, `shin.L`, `head`...). It reuses the same driver mechanism as the original but with `Damped Track` constraints instead of `Copy Location`/`Copy Rotation` on IK bones: each bone points toward the next joint in the chain. Covers arms, legs, head, and a simple torso approximation (10 landmarks; hands and face aren't included yet — see *Limitations*).

---

## Installation

1. `Preferences > Add-ons > Install from Disk` → select this repo's `.zip`.
2. Enable the addon. Go to the dependencies tab (inside the addon's preferences) and click **Install dependencies** — installs `mediapipe==0.10.33` (which in turn brings `opencv-contrib-python` and `numpy`) via `pip --user`, no admin rights required.
3. If a previous addon version left something half-installed, use the repair button available on the same panel.

Requires Blender 4.2 or newer (tested on 4.5 LTS). Python 3.11+ (the one bundled with Blender).

---

## Quick start

1. **3D View > Tool > BlendArMocap > MediaPipe**: choose Webcam or Video, detection type (Pose/Hands/Face), click *Start Detection*.
2. This creates a `cgt_*` empties hierarchy under the `cgt_DRIVERS` collection.
3. **Transfer**: pick your target Armature, the Drivers collection (`cgt_POSE` / `cgt_HANDS` / `cgt_FACE`), and the Transfer Type:
   - `Rigify_Humanoid_DefaultFace_v0.6.1` → for a rig **already generated** by Rigify (via *Generate Rig*).
   - `Generic_MetaRig_Basic` → for the raw (ungenerated) metarig, or a rig with similar bone naming.
>>>>>>> 3cd40c352ef1d842c922acb72229314f99bffddc
4. **Load** → **Transfer Animation**.

---

<<<<<<< HEAD
## Limitaciones conocidas / trabajo pendiente

- `Generic_MetaRig_Basic` no cubre manos ni cara todavía, solo torso/brazos/piernas/cabeza — es nuevo en este release y agradecemos reportes de uso.
- El jitter mejoró notablemente con `RunningMode.VIDEO`, pero no hay un benchmark formal contra la implementación original.
- Desarrollo y pruebas hechos principalmente en Windows 11 + Blender 4.5 LTS. Falta reportar compatibilidad en macOS/Linux.

## Créditos

- Autor y diseño original: [cgtinker](https://github.com/cgtinker) — [BlendArMocap](https://github.com/cgtinker/BlendArMocap).
- Port a la Tasks API moderna y fixes de estabilidad: este fork.
- Licencia: GPLv3 (heredada del proyecto original, ver `LICENSE`).

Ver `PORTING_NOTES.md` para el detalle técnico archivo por archivo.
=======
## Known limitations / open work

- `Generic_MetaRig_Basic` doesn't cover hands or face yet, only torso/arms/legs/head — it's new in this release, feedback from real use is welcome.
- Jitter improved noticeably with `RunningMode.VIDEO`, but there's no formal benchmark against the original implementation.
- Development and testing done mainly on Windows 11 + Blender 4.5 LTS. macOS/Linux compatibility reports are still needed.

## Credits

- Original author and design: [cgtinker](https://github.com/cgtinker) — [BlendArMocap](https://github.com/cgtinker/BlendArMocap).
- Port to the modern Tasks API and stability fixes: this fork.
- License: GPLv3 (inherited from the original project, see `LICENSE`).

See `PORTING_NOTES.md` for the file-by-file technical breakdown.
>>>>>>> 3cd40c352ef1d842c922acb72229314f99bffddc
