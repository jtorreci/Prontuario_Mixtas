# core/analysis/stress_analysis.py
import numpy as np
import logging

class StressCalculator:
    """Calcula tensiones elásticas y fibra neutra usando Navier."""

    def __init__(self, shapes, homog_props, N_ed, Mx_ed):
        """
        Inicializa el calculador de tensiones.

        Args:
            shapes (list): Lista de objetos de forma originales.
            homog_props (dict): Propiedades de la sección homogeneizada a acero
                                {'total_area', 'centroid_y', 'inertia_x'}.
            N_ed (float): Esfuerzo Axil (N). Positivo = Tracción, Negativo = Compresión.
            Mx_ed (float): Momento Flector respecto a eje X centroidal (N·mm).
                           Convenio: Positivo comprime fibras superiores (y > y_G).
        """
        self.shapes = shapes
        self.homog_props = homog_props
        self.N_ed = N_ed
        self.Mx_ed = Mx_ed
        self.A_h = homog_props.get('total_area')
        self.Iy_h = homog_props.get('inertia_x')
        self.y_G = homog_props.get('centroid_y')
        self.results = {'y_na': None, 'stresses': {}, 'error': None}

    def _validate_inputs(self):
        """Valida las propiedades de la sección homogeneizada."""

        if any(prop is None for prop in (self.A_h, self.Iy_h, self.y_G)):
            self.results['error'] = "Faltan propiedades homogeneizadas (A, Ix, yG)."
            return False

        if abs(self.A_h) < 1e-9:
            self.results['error'] = "Área homogeneizada es prácticamente cero."
            return False

        if abs(self.Iy_h) < 1e-9 and abs(self.Mx_ed) > 1e-9:
            self.results['error'] = "Inercia X homogeneizada nula con momento aplicado."
            return False

        return True

    def _calculate_axial_stress(self):
        """Calcula la tensión debida al esfuerzo axil."""

        return self.N_ed / self.A_h if self.A_h != 0 else 0

    def _calculate_neutral_axis(self, sigma_axial):
        """Calcula la posición de la fibra neutra."""

        if abs(self.Mx_ed) > 1e-9:
            try:
                y_na = self.y_G + (self.N_ed * self.Iy_h) / (self.Mx_ed * self.A_h)
                self.results['y_na'] = y_na
            except ZeroDivisionError:
                self.results['error'] = "División por cero al calcular y_NA (A o M pueden ser cero)."
                return False
        elif abs(self.N_ed) < 1e-9:  # Puro momento nulo o puro axil nulo -> Tensión cero
            self.results['y_na'] = None  # Indicar que no aplica o está en infinito
        else:  # Solo Axil (N_ed != 0, Mx_ed = 0)
            self.results['y_na'] = float('inf') if self.N_ed != 0 else None  # Fibra neutra en infinito
        return True

    def _calculate_stresses_at_points(self, sigma_axial):
        """Calcula las tensiones en los puntos clave de cada forma."""

        stresses = {}
        for i, shape in enumerate(self.shapes):
            try:
                y_min_shape = shape.y_min
                y_max_shape = shape.y_max

                sigma_min = sigma_axial
                sigma_max = sigma_axial
                if abs(self.Iy_h) > 1e-9:  # Solo añadir término de momento si la inercia no es nula
                    sigma_min -= (self.Mx_ed / self.Iy_h) * (y_min_shape - self.y_G)
                    sigma_max -= (self.Mx_ed / self.Iy_h) * (y_max_shape - self.y_G)

                stresses[f'shape_{i + 1}_ymin'] = {'y': y_min_shape, 'sigma_eq': sigma_min, 'mat': shape.material}
                stresses[f'shape_{i + 1}_ymax'] = {'y': y_max_shape, 'sigma_eq': sigma_max, 'mat': shape.material}

            except AttributeError:
                logging.warning(f"Forma {i + 1} ({type(shape)}) no tiene y_min/y_max, no se calculan tensiones.")
            except Exception as e:
                logging.error(f"Error calculando tensiones para forma {i + 1}: {e}")
                self.results['error'] = f"Error calculando tensión en forma {i + 1}."
        self.results['stresses'] = stresses

    def calculate_stresses(self):
        """
        Calcula las tensiones elásticas y la fibra neutra.

        Returns:
            dict: Contiene 'y_na' (posición fibra neutra), 'stresses' (dict con tensiones
                  en puntos clave), 'error' (mensaje de error si lo hay).
        """

        if not self._validate_inputs():
            return self.results

        sigma_axial = self._calculate_axial_stress()

        if not self._calculate_neutral_axis(sigma_axial):
            return self.results

        self._calculate_stresses_at_points(sigma_axial)

        return self.results

