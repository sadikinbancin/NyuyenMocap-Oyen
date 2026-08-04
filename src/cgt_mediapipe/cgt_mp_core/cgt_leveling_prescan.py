import logging
import time
import numpy as np
from pathlib import Path

from . import cv_stream, mp_pose_detector
from ...cgt_core.cgt_calculators_nodes import cgt_leveling

# Mismo remapeo de ejes que PoseRotationCalculator.prepare_landmarks (MP -> Blender).
# Se duplica aquí (en vez de importar) porque este módulo trabaja directo sobre
# landmarks crudos de MediaPipe, sin pasar por el node chain / self.data.


def _remap(lm):
    return np.array([-lm[0], lm[2], -lm[1]])


def _up_vector_from_raw_landmarks(indexed_landmarks):
    """ indexed_landmarks: lista [[idx, [x, y, z]], ...] cruda de MediaPipe
    (pose_world_landmarks). Devuelve el vector "torso-arriba" en espacio
    Blender, o None si faltan hombros/caderas en este frame. """
    lookup = {idx: lm for idx, lm in indexed_landmarks}
    if not all(i in lookup for i in (11, 12, 23, 24)):
        return None
    shoulder_c = (_remap(lookup[11]) + _remap(lookup[12])) / 2.0
    hip_c = (_remap(lookup[23]) + _remap(lookup[24])) / 2.0
    return shoulder_c - hip_c


def _landmarks_to_list(landmark_list):
    """ Copia de DetectorNode.cvt2landmark_array, sin instanciar un DetectorNode
    completo (que arrastraría stream.draw()/exit_stream() -> ventanas de cv2,
    justo lo que el pre-escaneo silencioso quiere evitar). """
    if landmark_list is None:
        return []
    items = landmark_list.landmark if hasattr(landmark_list, "landmark") else landmark_list
    return [[idx, [lm.x, lm.y, lm.z]] for idx, lm in enumerate(items)]


def estimate_leveling_from_movie(mov_path: str, sample_step: int = 6, max_samples: int = 40,
                                  model_complexity: int = 0, min_confidence: float = 0.5,
                                  debug: bool = False) -> bool:
    """ Escanea el clip completo SIN abrir ventanas de cv2 ni crear objetos en
    la escena de Blender, para estimar el sesgo de nivelado de cámara antes de
    iniciar la detección real. Fija el resultado en cgt_leveling.LEVELING en
    modo 'fixed'. Devuelve True si se pudo estimar, False si no. """
    if not Path(mov_path).is_file():
        logging.error(f"[cgt_leveling] Ruta de pre-escaneo inválida: {mov_path}")
        return False

    cgt_leveling.LEVELING.debug = debug
    stream = None
    compat = None
    up_samples = []

    try:
        stream = cv_stream.Stream(mov_path, "Leveling Prescan (silent)")
        compat = mp_pose_detector._PoseLandmarkerCompat(model_complexity, min_confidence)

        read_count = 0
        while len(up_samples) < max_samples:
            stream.update()
            if not stream.updated or stream.frame is None:
                break  # fin del clip

            read_count += 1
            # solo procesamos 1 de cada `sample_step` frames leídos
            if read_count % sample_step != 0:
                continue

            stream.set_color_space('rgb')
            res = compat.process(stream.frame)

            if res.pose_world_landmarks:
                raw = _landmarks_to_list(res.pose_world_landmarks)
                up = _up_vector_from_raw_landmarks(raw)
                if up is not None:
                    up_samples.append(up)
                    if debug:
                        logging.info(f"[cgt_leveling] pre-escaneo muestra {len(up_samples)}: "
                                     f"up=({up[0]:.4f}, {up[1]:.4f}, {up[2]:.4f})")
    except Exception as e:
        logging.error(f"[cgt_leveling] Pre-escaneo falló: {e}")
    finally:
        if compat is not None:
            compat.close()
        del stream  # libera cv2.VideoCapture, no abre ventanas en ningún momento

    if not up_samples:
        logging.warning("[cgt_leveling] Pre-escaneo no encontró pose en el clip, se omite el nivelado.")
        return False

    avg_up = np.mean(up_samples, axis=0)
    ok = cgt_leveling.LEVELING.set_fixed_up(avg_up)
    logging.info(f"[cgt_leveling] Pre-escaneo completo: {len(up_samples)} muestras, "
                 f"ángulo de corrección = {cgt_leveling.LEVELING.last_angle_deg:.2f}°")
    return ok


def estimate_leveling_from_webcam(camera_index: int = 0, backend: int = 0, duration_seconds: float = 3.0,
                                   model_complexity: int = 0, min_confidence: float = 0.5,
                                   debug: bool = False) -> bool:
    """ Corre unos segundos de captura en vivo (sin ventanas de cv2) alimentando
    el EMA de cgt_leveling.LEVELING, para el botón de diagnóstico. Deja el
    estado en modo 'ema' con muestras ya acumuladas (arranque en caliente),
    a diferencia de estimate_leveling_from_movie que fija un valor único. """
    cgt_leveling.LEVELING.reset('ema')
    cgt_leveling.LEVELING.debug = debug

    stream = None
    compat = None
    got_sample = False

    try:
        stream = cv_stream.Stream(capture_input=camera_index, backend=backend)
        compat = mp_pose_detector._PoseLandmarkerCompat(model_complexity, min_confidence)

        t0 = time.perf_counter()
        while time.perf_counter() - t0 < duration_seconds:
            stream.update()
            if not stream.updated or stream.frame is None:
                continue

            stream.set_color_space('rgb')
            res = compat.process(stream.frame)

            if res.pose_world_landmarks:
                raw = _landmarks_to_list(res.pose_world_landmarks)
                up = _up_vector_from_raw_landmarks(raw)
                if up is not None:
                    cgt_leveling.LEVELING.feed_ema(up)
                    got_sample = True
    except Exception as e:
        logging.error(f"[cgt_leveling] Diagnóstico de webcam falló: {e}")
    finally:
        if compat is not None:
            compat.close()
        del stream

    if not got_sample:
        logging.warning("[cgt_leveling] No se detectó pose durante el diagnóstico de webcam.")
    return got_sample
