# shapes/steel_plate.py
import numpy as np

class SteelPlate:
    """Representa una chapa de acero rectangular alineada con los ejes globales X,Y."""
    def __init__(self, width, height, cg_x, cg_y):
        self.width = float(width)   # Dimensión paralela al eje X
        self.height = float(height) # Dimensión paralela al eje Y
        self.cg_x = float(cg_x)
        self.cg_y = float(cg_y)
        self.material = "steel"

        if self.width <= 0 or self.height <= 0:
            raise ValueError("El ancho y alto de la chapa deben ser positivos.")

    @property
    def area(self):
        return self.width * self.height

    @property
    def inertia_x_local(self):
        """Inercia respecto al eje x que pasa por su CDG local (paralelo a X global)."""
        # Eje horizontal por el centroide: b*h^3/12 -> width * height^3 / 12
        return self.width * self.height**3 / 12

    @property
    def inertia_y_local(self):
        """Inercia respecto al eje y que pasa por su CDG local (paralelo a Y global)."""
        # Eje vertical por el centroide: h*b^3/12 -> height * width^3 / 12
        return self.height * self.width**3 / 12

    @property
    def y_min(self):
        return self.cg_y - self.height / 2
    @property
    def y_max(self):
        return self.cg_y + self.height / 2
    @property
    def x_min(self):
        return self.cg_x - self.width / 2
    @property
    def x_max(self):
        return self.cg_x + self.width / 2

    def get_vertices(self, width_scale_factor=1.0):
        """
        Devuelve las coordenadas de los 4 vértices para dibujar.
        El 'width_scale_factor' solo afecta si se quisiera visualizar
        la homogeneización de acero (normalmente no se hace).
        Aquí escala la dimensión 'width' (paralela a X).
        """
        scaled_width = self.width * width_scale_factor
        half_w = scaled_width / 2
        half_h = self.height / 2 # La altura (paralela a Y) no se escala por defecto

        return [
            (self.cg_x - half_w, self.cg_y - half_h), # Bottom-left
            (self.cg_x + half_w, self.cg_y - half_h), # Bottom-right
            (self.cg_x + half_w, self.cg_y + half_h), # Top-right
            (self.cg_x - half_w, self.cg_y + half_h)  # Top-left
        ]

