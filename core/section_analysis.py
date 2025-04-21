# core/section_analysis.py
import numpy as np
# No necesitamos importar get_modular_ratio aquí si se pasa desde fuera

def calculate_section_properties(shapes, homogenize=False, modular_ratio=None):
    """
    Calcula las propiedades geométricas de una colección de formas.
    Si homogenize es True, transforma el HORMIGÓN a ACERO equivalente
    dividiendo sus propiedades (A, Ix, Iy) por modular_ratio (n=Es/Ecm).
    Requiere que modular_ratio sea proporcionado si homogenize es True.

    Args:
        shapes (list): Lista de objetos SteelPlate y ConcreteTrapezoid.
        homogenize (bool): True para realizar la homogeneización a acero.
        modular_ratio (float, optional): Relación modular n = Es / Ecm. Necesario si homogenize=True.

    Returns:
        dict: Diccionario con 'total_area', 'centroid_x', 'centroid_y',
              'inertia_x', 'inertia_y'.

    Raises:
        ValueError: Si se intenta homogeneizar sin un modular_ratio válido.
    """
    if homogenize and modular_ratio is None:
        raise ValueError("Se requiere 'modular_ratio' para homogeneizar.")
    if homogenize and modular_ratio <= 0:
         raise ValueError("'modular_ratio' debe ser positivo para homogeneizar.")

    total_area = 0.0
    moment_x = 0.0  # Sum(Ai * yi)
    moment_y = 0.0  # Sum(Ai * xi)
    inertia_x_global = 0.0 # Sum(Ix_local_i + Ai * dy_i^2)
    inertia_y_global = 0.0 # Sum(Iy_local_i + Ai * dx_i^2)

    processed_shapes = [] # Guardaremos las propiedades (A, x, y, Ix, Iy) de cada parte

    for shape in shapes:
        try:
            A = shape.area
            x = shape.cg_x
            y = shape.cg_y
            Ix_local = shape.inertia_x_local
            # Manejar posible None de Iy_local en Trapecio o si no está implementado
            Iy_local = shape.inertia_y_local if hasattr(shape, 'inertia_y_local') and shape.inertia_y_local is not None else 0.0
        except AttributeError as e:
             raise AttributeError(f"El objeto {type(shape)} no tiene una propiedad necesaria: {e}")


        if homogenize and hasattr(shape, 'material') and shape.material == "concrete":
            # Homogeneizar hormigón a acero dividiendo por n
            # Se asume que Ix e Iy locales escalan con 1/n.
            # (Verificado para Ix, pero Iy puede tener dependencia n^3 para formas como rectángulos)
            # Procedemos con 1/n para ambos por simplicidad inicial, enfocado en Ix.
            if modular_ratio == 0: # Doble chequeo por si acaso
                 raise ValueError("Intento de división por cero en homogeneización (modular_ratio=0).")
            A /= modular_ratio
            Ix_local /= modular_ratio
            Iy_local /= modular_ratio # Precaución con esta simplificación para Iy

        # Las partes de acero no cambian en esta homogeneización
        # else: # shape.material == "steel" or not homogenize
        #     pass # Keep original properties

        # Ignorar formas con área nula o negativa (podría ocurrir con escalas raras)
        if abs(A) > 1e-9: # Usar abs() por si acaso
            processed_shapes.append({'A': A, 'x': x, 'y': y, 'Ix': Ix_local, 'Iy': Iy_local})
            total_area += A
            moment_x += A * y
            moment_y += A * x
        # else: # Opcional: Informar si se ignora una forma
             # print(f"Advertencia: Ignorando forma {type(shape)} con área calculada cercana a cero: {A}")


    if abs(total_area) < 1e-9:
        # Devuelve ceros si el área total es despreciable
        return {'total_area': 0, 'centroid_x': 0, 'centroid_y': 0, 'inertia_x': 0, 'inertia_y': 0}

    # Calcular centroide global
    centroid_x = moment_y / total_area
    centroid_y = moment_x / total_area

    # Calcular inercias globales usando el Teorema de Steiner (Ejes Paralelos)
    for props in processed_shapes:
        dy = props['y'] - centroid_y
        dx = props['x'] - centroid_x
        # Steiner: I_global = Sum( I_local_cg + A * d^2 )
        inertia_x_global += props['Ix'] + props['A'] * dy**2
        inertia_y_global += props['Iy'] + props['A'] * dx**2

    return {
        'total_area': total_area,
        'centroid_x': centroid_x,
        'centroid_y': centroid_y,
        'inertia_x': inertia_x_global, # Inercia respecto al eje X que pasa por el CDG global
        'inertia_y': inertia_y_global  # Inercia respecto al eje Y que pasa por el CDG global
    }

