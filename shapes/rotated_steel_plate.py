# shapes/rotated_steel_plate.py
import numpy as np
import math

class RotatedSteelPlate:
    """
    Representa una chapa de acero rectangular con un espesor, definida por:
    1) Punto inicial, punto final y espesor.
    2) Punto inicial, vector director, longitud y espesor.
    La chapa puede estar rotada en el plano XY.
    """
    def __init__(self, thickness, p1=None, p2=None, vector=None, length=None, definition_method=None):
        """
        Inicializa la chapa rotada.

        Args:
            thickness (float): Espesor de la chapa (será el 'ancho' local).
            p1 (tuple, optional): Coordenadas (x1, y1) del punto inicial. Requerido si no se usa vector/length.
            p2 (tuple, optional): Coordenadas (x2, y2) del punto final. Requerido si no se usa vector/length.
            vector (tuple, optional): Vector director (vx, vy). Usado con p1 y length.
            length (float, optional): Longitud de la chapa. Usado con p1 y vector.
            definition_method (str, optional): Almacena cómo fue definida ('Points' o 'Vector') para la edición.

        Raises:
            ValueError: Si los argumentos de entrada no son suficientes o son inconsistentes.
        """
        self.t = float(thickness)
        self.material = "steel"
        self.definition_method = definition_method # Guardar para la edición

        if self.t <= 0:
             raise ValueError("El espesor de la chapa debe ser positivo.")

        if p1 is None:
            raise ValueError("El punto inicial 'p1' es requerido.")
        self.p1 = np.array(p1, dtype=float)

        if p2 is not None:
            # Definición por p1 y p2
            self.p2 = np.array(p2, dtype=float)
            if vector is not None or length is not None:
                # Permitir pero advertir puede ser peligroso si los datos son inconsistentes.
                # Mejor ser estricto o elegir una prioridad clara.
                # print("Advertencia: Se proporcionaron p1/p2 y vector/length. Se usarán p1 y p2.")
                pass # Ignorar vector/length si se dan p1 y p2
            diff = self.p2 - self.p1
            self.L = np.linalg.norm(diff)
            if self.L < 1e-9:
                raise ValueError("Los puntos p1 y p2 son coincidentes (longitud cero).")
            # Vector director unitario
            self.u_dir = diff / self.L
            # Calcular vector y longitud originales para posible edición
            self._vector_original = tuple(diff) # Guardar vector no unitario
            self._length_original = self.L # Guardar longitud
            if not self.definition_method: self.definition_method = 'Points'

        elif vector is not None and length is not None:
            # Definición por p1, vector y length
            self.L = float(length)
            if self.L <= 0:
                raise ValueError("La longitud 'length' debe ser positiva.")
            v = np.array(vector, dtype=float)
            v_norm = np.linalg.norm(v)
            if v_norm < 1e-9:
                raise ValueError("El vector director no puede ser cero.")
            # Vector director unitario
            self.u_dir = v / v_norm
            self.p2 = self.p1 + self.L * self.u_dir
             # Guardar vector y longitud originales para posible edición
            self._vector_original = tuple(v)
            self._length_original = self.L
            if not self.definition_method: self.definition_method = 'Vector'
        else:
            raise ValueError("Debe proporcionar 'p2' o ('vector' y 'length').")

        # Calcular ángulo con el eje X global (en radianes)
        self.theta = math.atan2(self.u_dir[1], self.u_dir[0])

        # Calcular centro de gravedad (punto medio del eje longitudinal)
        self.cg_x = (self.p1[0] + self.p2[0]) / 2
        self.cg_y = (self.p1[1] + self.p2[1]) / 2

    @property
    def area(self):
        """Área de la chapa."""
        return self.L * self.t

    # --- Propiedades de Inercia ---
    # Calculamos Ix e Iy respecto a ejes paralelos a los globales X,Y
    # pero que pasan por el CDG de la chapa.

    @property
    def inertia_x_local(self):
        """Inercia respecto a eje X' // X global, pasando por CDG local."""
        # Iu = Inercia sobre eje longitudinal (u) = t * L^3 / 12
        # Iv = Inercia sobre eje transversal (v) = L * t^3 / 12
        # Nota: 'u' es el eje a lo largo de L, 'v' es el eje a lo largo de t.
        Iu = self.t * self.L**3 / 12
        Iv = self.L * self.t**3 / 12
        sin_t = math.sin(self.theta)
        cos_t = math.cos(self.theta)
        # Fórmula de rotación de tensor de inercia:
        # Ix_cg = (Iu+Iv)/2 + (Iu-Iv)/2 * cos(2*theta) <-- Incorrecto para ejes X,Y
        # Usando transformación directa: Ix_cg = Iu*sin^2(theta) + Iv*cos^2(theta)
        return Iu * sin_t**2 + Iv * cos_t**2

    @property
    def inertia_y_local(self):
        """Inercia respecto a eje Y' // Y global, pasando por CDG local."""
        Iu = self.t * self.L**3 / 12
        Iv = self.L * self.t**3 / 12
        sin_t = math.sin(self.theta)
        cos_t = math.cos(self.theta)
        # Iy_cg = Iu*cos^2(theta) + Iv*sin^2(theta)
        return Iu * cos_t**2 + Iv * sin_t**2

    def get_vertices(self, width_scale_factor=1.0):
        """
        Devuelve las coordenadas de los 4 vértices de la chapa rectangular.
        El 'width_scale_factor' escala el espesor (t).
        """
        scaled_t = self.t * width_scale_factor
        if scaled_t < 0: scaled_t = 0 # Evitar espesor negativo
        half_t = scaled_t / 2

        # Vector normal (perpendicular a u_dir, longitud 1)
        # Rotar u_dir 90 grados: (x, y) -> (-y, x)
        u_norm = np.array([-self.u_dir[1], self.u_dir[0]])

        # Calcular los 4 vértices usando p1, p2 y el vector normal escalado
        v1 = self.p1 + half_t * u_norm
        v2 = self.p2 + half_t * u_norm
        v3 = self.p2 - half_t * u_norm
        v4 = self.p1 - half_t * u_norm

        # Devolver como lista de tuplas
        return [tuple(v1), tuple(v2), tuple(v3), tuple(v4)]

    # Propiedades para límites bounding box (calculadas a partir de vértices)
    @property
    def _vertices_coords(self):
        """Helper para no recalcular vértices innecesariamente."""
        # Podríamos cachear esto si fuera costoso, pero por ahora lo recalculamos
        return self.get_vertices() # Llama al método existente con factor 1.0

    @property
    def y_min(self):
        return min(v[1] for v in self._vertices_coords)
    @property
    def y_max(self):
        return max(v[1] for v in self._vertices_coords)
    @property
    def x_min(self):
        return min(v[0] for v in self._vertices_coords)
    @property
    def x_max(self):
        return max(v[0] for v in self._vertices_coords)

