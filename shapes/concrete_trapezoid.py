# shapes/concrete_trapezoid.py
import numpy as np

class ConcreteTrapezoid:
    """
    Representa un trapecio de hormigón, definido por anchos inferior/superior,
    altura y coordenadas del centro de la base inferior.
    Se asume simetría vertical respecto al eje que pasa por el centro de la base inferior.
    """
    def __init__(self, bottom_width, top_width, height, bottom_center_x, bottom_center_y):
        self.b1 = float(bottom_width)  # Ancho inferior
        self.b2 = float(top_width)    # Ancho superior
        self.h = float(height)
        self.bc_x = float(bottom_center_x) # X del centro de la base inferior
        self.bc_y = float(bottom_center_y) # Y del centro (y nivel) de la base inferior
        self.material = "concrete"

        if self.h <= 0:
            raise ValueError("La altura del trapecio debe ser positiva.")
        if self.b1 < 0 or self.b2 < 0:
            raise ValueError("Los anchos del trapecio no pueden ser negativos.")

    @property
    def area(self):
        return (self.b1 + self.b2) / 2 * self.h

    @property
    def cg_y_local(self):
        """Distancia vertical del CDG a la base inferior."""
        sum_b = self.b1 + self.b2
        if abs(sum_b) < 1e-9: # Evitar división por cero si el área es 0 (b1=b2=0)
            # Si el área es cero, el CDG está indefinido, pero podemos devolver la mitad de la altura
            # o manejarlo como un caso especial. Devolver h/2 es razonable.
            return self.h / 2
        # Fórmula para la posición Y del Cdg respecto a la base inferior
        return (self.h / 3) * (self.b1 + 2 * self.b2) / sum_b

    @property
    def cg_x(self):
        """Coordenada X global del CDG (asume simetría respecto al eje vertical que pasa por bc_x)."""
        # Para un trapecio isósceles (o definido simétricamente), el CDG está en el eje de simetría
        return self.bc_x

    @property
    def cg_y(self):
        """Coordenada Y global del CDG."""
        return self.bc_y + self.cg_y_local

    @property
    def inertia_x_local(self):
        """Inercia respecto al eje x que pasa por su CDG local (paralelo a X global)."""
        sum_b = self.b1 + self.b2
        if abs(sum_b) < 1e-9:
            return 0 # Inercia cero si el área es cero
        # Fórmula de la inercia de un trapecio respecto a su eje centroidal horizontal
        return (self.h**3 / 36) * (self.b1**2 + 4 * self.b1 * self.b2 + self.b2**2) / sum_b

    @property
    def inertia_y_local(self):
        """Inercia respecto al eje y que pasa por su CDG local (paralelo a Y global, asume simetría)."""
        # Fórmula para trapecio simétrico respecto al eje vertical centroidal
        sum_b = self.b1 + self.b2
        if abs(sum_b) < 1e-9 or self.h == 0:
            return 0.0
        try:
            # Esta fórmula SÍ parece corresponder a la inercia respecto al eje Y centroidal para un trapecio ISÓSCELES.
            inertia = (self.h * (self.b1 + self.b2) * (self.b1**2 + self.b2**2)) / 48.0
            return inertia
        except ZeroDivisionError:
            return 0.0

    @property
    def y_min(self):
        return self.bc_y
    @property
    def y_max(self):
        return self.bc_y + self.h
    @property
    def x_min(self):
        # El mínimo X está en el borde exterior de la base o el top, el que sea más ancho
        max_half_b = max(self.b1 / 2, self.b2 / 2) if self.b1 >= 0 and self.b2 >= 0 else 0
        return self.bc_x - max_half_b
    @property
    def x_max(self):
        max_half_b = max(self.b1 / 2, self.b2 / 2) if self.b1 >= 0 and self.b2 >= 0 else 0
        return self.bc_x + max_half_b

    def get_vertices(self, width_scale_factor=1.0):
        """
        Devuelve las coordenadas de los 4 vértices para dibujar.
        El 'width_scale_factor' escala los anchos b1 y b2 (usado para visualizar homogeneización).
        """
        scaled_b1 = self.b1 * width_scale_factor
        scaled_b2 = self.b2 * width_scale_factor
        half_b1 = scaled_b1 / 2
        half_b2 = scaled_b2 / 2
        # bc_x es el centro de la base inferior original. El escalado se hace simétrico respecto a él.
        return [
            (self.bc_x - half_b1, self.bc_y),             # Bottom-left
            (self.bc_x + half_b1, self.bc_y),             # Bottom-right
            (self.bc_x + half_b2, self.bc_y + self.h),    # Top-right
            (self.bc_x - half_b2, self.bc_y + self.h)     # Top-left
        ]

