# core/stress_analysis.py
import numpy as np

def calculate_navier_stress(N_ed, Mx_ed, shapes, homog_props):
    """
    Calcula tensiones elásticas y fibra neutra usando Navier en sección homogeneizada.

    Args:
        N_ed (float): Esfuerzo Axil (N). Positivo = Tracción, Negativo = Compresión.
        Mx_ed (float): Momento Flector respecto a eje X centroidal (N·mm).
                       Convenio: Positivo comprime fibras superiores (y > y_G).
        shapes (list): Lista de objetos de forma originales.
        homog_props (dict): Propiedades de la sección homogeneizada a acero
                            {'total_area', 'centroid_y', 'inertia_x'}.

    Returns:
        dict: Contiene 'y_na' (posición fibra neutra), 'stresses' (dict con tensiones
              en puntos clave), 'error' (mensaje de error si lo hay).
    """
    A_h = homog_props.get('total_area')
    Iy_h = homog_props.get('inertia_x') # Usamos la inercia respecto al eje X centroidal global
    y_G = homog_props.get('centroid_y')

    results = {'y_na': None, 'stresses': {}, 'error': None}

    # Validaciones básicas
    if A_h is None or Iy_h is None or y_G is None:
        results['error'] = "Faltan propiedades homogeneizadas (A, Ix, yG)."
        return results
    if abs(A_h) < 1e-9:
        results['error'] = "Área homogeneizada es prácticamente cero."
        return results
    # Permitir Inercia cero solo si no hay momento? O error directo? Mejor error.
    if abs(Iy_h) < 1e-9 and abs(Mx_ed) > 1e-9 :
         results['error'] = "Inercia X homogeneizada nula con momento aplicado."
         return results

    # Calcular Tensión debida al Axil
    sigma_axial = N_ed / A_h if A_h != 0 else 0

    # --- Calcular Fibra Neutra (y_NA) ---
    # y_NA = y_G + (N_ed * Iy_h) / (Mx_ed * A_h)  (Convenio M+ tracciona arriba)
    # Con nuestro convenio M+ comprime arriba:
    # 0 = N/A - M/I * (y_NA - y_G) -> y_NA - y_G = N*I / (M*A)
    y_na = None
    if abs(Mx_ed) > 1e-9: # Evitar división por cero si no hay momento
        try:
            y_na = y_G + (N_ed * Iy_h) / (Mx_ed * A_h)
            results['y_na'] = y_na
        except ZeroDivisionError:
             results['error'] = "División por cero al calcular y_NA (A o M pueden ser cero)."
             # No continuar si hay error aquí
             return results
    elif abs(N_ed) < 1e-9: # Puro momento nulo o puro axil nulo -> Tensión cero
         y_na = None # Fibra neutra en el infinito o indeterminada
         results['y_na'] = None # Indicar que no aplica o está en infinito
         # Las tensiones serán cero, lo calculamos abajo
    else: # Solo Axil (N_ed != 0, Mx_ed = 0)
        y_na = float('inf') if N_ed != 0 else None # Fibra neutra en infinito
        results['y_na'] = y_na

    # --- Calcular Tensiones en puntos clave ---
    stresses = {}
    for i, shape in enumerate(shapes):
        try:
            y_min_shape = shape.y_min
            y_max_shape = shape.y_max

            # Calcular tensión en la fibra inferior y superior de la forma
            # sigma(y) = sigma_axial - (Mx_ed / Iy_h) * (y - y_G)
            sigma_min = sigma_axial
            sigma_max = sigma_axial
            if abs(Iy_h) > 1e-9: # Solo añadir término de momento si la inercia no es nula
                sigma_min -= (Mx_ed / Iy_h) * (y_min_shape - y_G)
                sigma_max -= (Mx_ed / Iy_h) * (y_max_shape - y_G)

            # Guardar tensiones (éstas son en acero equivalente)
            stresses[f'shape_{i+1}_ymin'] = {'y': y_min_shape, 'sigma_eq': sigma_min, 'mat': shape.material}
            stresses[f'shape_{i+1}_ymax'] = {'y': y_max_shape, 'sigma_eq': sigma_max, 'mat': shape.material}

            # Podríamos añadir puntos intermedios o CDG si fuera necesario
            # y_cg_shape = shape.cg_y
            # sigma_cg = sigma_axial - (Mx_ed / Iy_h) * (y_cg_shape - y_G) if Iy_h != 0 else sigma_axial
            # stresses[f'shape_{i+1}_ycg'] = {'y': y_cg_shape, 'sigma_eq': sigma_cg, 'mat': shape.material}

        except AttributeError:
            print(f"Advertencia: Forma {i+1} ({type(shape)}) no tiene y_min/y_max, no se calculan tensiones.")
        except Exception as e:
             print(f"Error calculando tensiones para forma {i+1}: {e}")
             results['error'] = f"Error calculando tensión en forma {i+1}."
             # Podríamos decidir continuar o parar aquí

    results['stresses'] = stresses
    return results

