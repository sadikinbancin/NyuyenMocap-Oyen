import time
import numpy as np


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * float(np.clip(t, 0.0, 1.0))


class OneEuroFilter:
    """ Filtro de paso bajo adaptativo (Casiez, Pietriga & Roussel, 2012).
    A diferencia de un promedio/EMA de factor fijo, éste sube el corte (menos
    suavizado) cuando la señal se mueve rápido, y lo baja (más suavizado)
    cuando está casi quieta. Eso es exactamente lo que necesitamos: un pie
    apoyado en el piso queda prácticamente inmóvil (mucho jitter, poco corte
    de frecuencia -> se suaviza fuerte), pero un paso real no se queda "pegado"
    (velocidad alta -> el filtro se abre y sigue el movimiento sin lag notorio).

    mincutoff, beta y dcutoff se pasan en cada llamada (no se fijan en el
    constructor) para poder ajustarlos en vivo desde la UI sin perder el
    estado (posición/velocidad previas) del filtro. """

    def __init__(self):
        self._x_prev: np.ndarray = None
        self._dx_prev: np.ndarray = None
        self._t_prev: float = None

    def reset(self):
        self._x_prev = None
        self._dx_prev = None
        self._t_prev = None

    @staticmethod
    def _alpha(cutoff: np.ndarray, dt: float) -> np.ndarray:
        tau = 1.0 / (2.0 * np.pi * np.maximum(cutoff, 1e-6))
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: np.ndarray, mincutoff: float, beta: float,
               dcutoff: float = 1.0, t: float = None) -> np.ndarray:
        if t is None:
            t = time.perf_counter()
        x = np.asarray(x, dtype=float)

        if self._x_prev is None:
            self._x_prev = x.copy()
            self._dx_prev = np.zeros_like(x)
            self._t_prev = t
            return self._x_prev.copy()

        dt = max(t - self._t_prev, 1e-6)

        # velocidad filtrada (para decidir cuánto abrir el corte)
        dx = (x - self._x_prev) / dt
        a_d = self._alpha(np.array(dcutoff), dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self._dx_prev

        # corte adaptativo: sube con la velocidad (beta), nunca baja de mincutoff
        cutoff = mincutoff + beta * np.abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1.0 - a) * self._x_prev

        self._x_prev = x_hat
        self._dx_prev = dx_hat
        self._t_prev = t
        return x_hat.copy()


# Landmarks de pie (tobillo, talón, punta) — donde el usuario nota más jitter
# y donde el pie debería quedarse quieto mientras está apoyado en el piso.
FOOT_IDS = frozenset({27, 28, 29, 30, 31, 32})

# Hombro y cadera: alimentan torso_rotation()/shoulder_rotation(), así que su
# ruido se ve como "tambaleo" en TODO el rig, no solo en el propio landmark.
ROOT_IDS = frozenset({11, 12, 23, 24})


class SmoothingConfig:
    """ Traduce dos sliders 0..1 (uno general, uno para pies+raíz) a los
    parámetros reales del One Euro Filter. Vive como instancia compartida
    (ver CONFIG al final) para que la UI la pueda ajustar en caliente sin
    tener que atravesar el node chain. """

    def __init__(self):
        self.enabled = True
        self.general_amount = 0.55
        self.foot_amount = 0.85

    def general_params(self):
        mincutoff = _lerp(3.5, 1.0, self.general_amount)
        beta = _lerp(0.3, 2.0, self.general_amount)
        return mincutoff, beta

    def root_params(self):
        # un punto intermedio entre "general" y "pie": la raíz del torso
        # también se beneficia de más quietud, pero no debe ir tan lento
        # como el pie o el torso entero se sentiría "pegajoso".
        mincutoff = _lerp(3.0, 0.3, self.foot_amount)
        beta = _lerp(0.3, 1.0, self.foot_amount)
        return mincutoff, beta

    def foot_params(self):
        mincutoff = _lerp(2.5, 0.15, self.foot_amount)
        beta = _lerp(0.3, 1.2, self.foot_amount)
        return mincutoff, beta

    def params_for(self, idx: int):
        if idx in FOOT_IDS:
            return self.foot_params()
        if idx in ROOT_IDS:
            return self.root_params()
        return self.general_params()


CONFIG = SmoothingConfig()


class LandmarkSmoother:
    """ Un OneEuroFilter por índice de landmark (33 puntos de pose). Vive
    como atributo de instancia de PoseRotationCalculator — como esa clase se
    reinstancia en cada corrida de detección (ver cgt_core_chains.PoseNodeChain),
    el historial de suavizado arranca limpio en cada "Detect Clip"/"Start
    Detection" sin necesidad de resetear nada manualmente. """

    def __init__(self, config: SmoothingConfig = CONFIG):
        self.config = config
        self._filters = {}

    def smooth(self, indexed_points, t: float = None):
        if not self.config.enabled:
            return indexed_points
        if t is None:
            t = time.perf_counter()

        out = []
        for idx, landmark in indexed_points:
            f = self._filters.get(idx)
            if f is None:
                f = OneEuroFilter()
                self._filters[idx] = f
            mincutoff, beta = self.config.params_for(idx)
            out.append([idx, f.filter(landmark, mincutoff, beta, t=t)])
        return out
