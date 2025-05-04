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
            p1 (tuple, optional): Coordenadas (x1, y1) del punto inicial.
                                 Requerido si no se usa vector/length.
            p2 (tuple, optional): Coordenadas (x2, y2) del punto final.
                                 Requerido si no se usa vector/length.
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
            self.L = np
