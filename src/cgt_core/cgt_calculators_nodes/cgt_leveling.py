import logging
import numpy as np
from mathutils import Vector, Quaternion

TARGET_UP = Vector((0.0, 0.0, 1.0))


class CameraLevelingState:
    """ Estima y aplica la corrección de nivelado (tilt) de cámara.

    MediaPipe entrega los landmarks en el espacio de la cámara, no en el
    espacio de la gravedad. Si la cámara está inclinada, el "arriba" del
    torso detectado no coincide con el eje Z de Blender, y ese sesgo se
    propaga a TODO el point cloud (posiciones vía CHAIN/COPY_LOCATION y
    rotaciones vía REMAP/COPY_ROTATION).

    Este objeto sólo estima un vector "torso-arriba" (hombro_centro - cadera_centro,
    ya en espacio Blender) y expone una rotación que lleva ese vector a (0, 0, 1).
    Se alimenta de dos formas:

    - modo 'ema' (webcam / tiempo real): se promedia el vector arriba de cada
      frame; el sesgo de cámara es constante, el movimiento real del cuerpo
      oscila alrededor de él y tiende a promediarse a cero.
    - modo 'fixed' (clips ya grabados): se fija una sola vez con el resultado
      de un pre-escaneo del clip completo (ver cgt_leveling_prescan.py), para
      no arrancar con corrección incompleta en los primeros frames.
    - modo 'off': sin corrección (identidad). Se usa cuando no hay datos de
      pose disponibles (p.ej. detección solo de manos o cara).

    Instancia única (LEVELING, al final del archivo) compartida entre
    mp_calc_pose_rot.py y mp_calc_hand_rot.py, para que ambos usen siempre
    el mismo ángulo de corrección sin acoplar los módulos entre sí.
    """

    def __init__(self, ema_alpha: float = 0.02):
        self.ema_alpha = ema_alpha
        self.enabled = True
        self.mode = 'off'  # 'ema' | 'fixed' | 'off'
        self.debug = False

        self._up_ema: Vector = None
        self._fixed_up: Vector = None
        self.last_angle_deg = 0.0
        self.sample_count = 0

        # Ajuste manual: rotación extra en grados sobre el eje de profundidad
        # (Y en espacio Blender tras el remapeo de ejes = eje de vista de la
        # cámara), para afinar a mano cuando la estimación automática deja un
        # remanente de inclinación. Se aplica DESPUÉS de la corrección
        # automática, nunca la reemplaza.
        self.manual_offset_deg = 0.0

    def reset(self, mode: str = 'off'):
        """ Llamar al comenzar cada corrida de detección nueva. """
        self.mode = mode
        self._up_ema = None
        self._fixed_up = None
        self.last_angle_deg = 0.0
        self.sample_count = 0

    def set_fixed_up(self, up_vector) -> bool:
        """ Fija la corrección una sola vez (modo clip). Devuelve False si el
        vector es degenerado y no se pudo fijar. """
        v = Vector((float(up_vector[0]), float(up_vector[1]), float(up_vector[2])))
        if v.length < 1e-6:
            logging.warning("[cgt_leveling] up vector inválido, se omite el nivelado fijo.")
            self._fixed_up = None
            return False
        v.normalize()
        self._fixed_up = v
        self.mode = 'fixed'
        self._log_angle(v, source="fixed (pre-escaneo)")
        return True

    def feed_ema(self, up_vector):
        """ Alimenta una muestra nueva en modo EMA (webcam en vivo). """
        v = Vector((float(up_vector[0]), float(up_vector[1]), float(up_vector[2])))
        if v.length < 1e-6:
            return
        v.normalize()

        if self._up_ema is None:
            self._up_ema = v
        else:
            blended = self._up_ema * (1.0 - self.ema_alpha) + v * self.ema_alpha
            if blended.length > 1e-6:
                blended.normalize()
                self._up_ema = blended

        self.sample_count += 1
        self._log_angle(self._up_ema, source=f"ema (muestra {self.sample_count})")

    def _log_angle(self, up: Vector, source: str = ""):
        try:
            angle = up.angle(TARGET_UP)
        except ValueError:
            angle = 0.0
        self.last_angle_deg = float(np.degrees(angle))
        if self.debug:
            logging.info(
                f"[cgt_leveling] up=({up.x:.4f}, {up.y:.4f}, {up.z:.4f}) "
                f"correction_angle={self.last_angle_deg:.2f}° [{source}]"
            )

    def get_current_up(self):
        if self.mode == 'fixed':
            return self._fixed_up
        if self.mode == 'ema':
            return self._up_ema
        return None

    def get_correction_quaternion(self) -> Quaternion:
        """ Rotación que lleva el 'arriba' medido/estimado a (0, 0, 1). """
        up = self.get_current_up()
        if not self.enabled or up is None:
            return Quaternion((1.0, 0.0, 0.0, 0.0))
        return up.rotation_difference(TARGET_UP)

    def get_manual_quaternion(self) -> Quaternion:
        """ Rotación extra fija (grados -> radianes) sobre el eje de
        profundidad (Y), para el ajuste fino manual desde la UI. """
        if abs(self.manual_offset_deg) < 1e-6:
            return Quaternion((1.0, 0.0, 0.0, 0.0))
        return Quaternion(Vector((0.0, 1.0, 0.0)), np.radians(self.manual_offset_deg))

    def apply(self, indexed_points):
        """ Rota un point cloud completo con la corrección actual (automática
        + ajuste manual). indexed_points: lista de [idx, np.array([x, y, z])].
        Devuelve una lista nueva con la misma forma. Si no hay ninguna
        corrección activa, devuelve la lista sin tocar (barato). """
        quat = self.get_correction_quaternion()
        manual_quat = self.get_manual_quaternion()
        if abs(quat.angle) < 1e-6 and abs(manual_quat.angle) < 1e-6:
            return indexed_points

        out = []
        for idx, landmark in indexed_points:
            v = Vector((float(landmark[0]), float(landmark[1]), float(landmark[2])))
            v.rotate(quat)
            v.rotate(manual_quat)
            out.append([idx, np.array([v.x, v.y, v.z])])
        return out


# Instancia única compartida por todo el addon durante una corrida de detección.
LEVELING = CameraLevelingState()
