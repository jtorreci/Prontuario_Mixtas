# core/analysis/section_analysis.py
import numpy as np

class SectionPropertiesCalculator:
    """Calcula las propiedades geométricas de una sección."""

    def __init__(self, shapes, homogenize=False, modular_ratio=None):
        self.shapes = shapes
        self.homogenize = homogenize
        self.modular_ratio = modular_ratio
        self.total_area = 0.0
        self.moment_x = 0.0
        self.moment_y = 0.0
        self.inertia_x_global = 0.0
        self.inertia_y_global = 0.0
        self.processed_shapes = []

        self._validate_inputs()

    def _validate_inputs(self):
        if self.homogenize and self.modular_ratio is None:
            raise ValueError("Se requiere 'modular_ratio' para homogeneizar.")
        if self.homogenize and self.modular_ratio <= 0:
            raise ValueError("'modular_ratio' debe ser positivo para homogeneizar.")

    def _process_shape(self, shape):
        try:
            A = shape.area
            x = shape.cg_x
            y = shape.cg_y
            Ix_local = shape.inertia_x_local
            Iy_local = shape.inertia_y_local if hasattr(shape, 'inertia_y_local') and shape.inertia_y_local is not None else 0.0
        except AttributeError as e:
            raise AttributeError(f"El objeto {type(shape)} no tiene una propiedad necesaria: {e}")

        if self.homogenize and hasattr(shape, 'material') and shape.material == "concrete":
            if self.modular_ratio == 0:
                raise ValueError("Intento de división por cero en homogeneización (modular_ratio=0).")
            A /= self.modular_ratio
            Ix_local /= self.modular_ratio
            Iy_local /= self.modular_ratio  # Precaución con esta simplificación para Iy

        if abs(A) > 1e-9:
            self.processed_shapes.append({'A': A, 'x': x, 'y': y, 'Ix': Ix_local, 'Iy': Iy_local})
            self.total_area += A
            self.moment_x += A * y
            self.moment_y += A * x

    def calculate_properties(self):
        for shape in self.shapes:
            self._process_shape(shape)

        if abs(self.total_area) < 1e-9:
            return {'total_area': 0, 'centroid_x': 0, 'centroid_y': 0, 'inertia_x': 0, 'inertia_y': 0}

        centroid_x = self.moment_y / self.total_area
        centroid_y = self.moment_x / self.total_area

        for props in self.processed_shapes:
            dy = props['y'] - centroid_y
            dx = props['x'] - centroid_x
            self.inertia_x_global += props['Ix'] + props['A'] * dy**2
            self.inertia_y_global += props['Iy'] + props['A'] * dx**2

        return {
            'total_area': self.total_area,
            'centroid_x': centroid_x,
            'centroid_y': centroid_y,
            'inertia_x': self.inertia_x_global,
            'inertia_y': self.inertia_y_global
        }

