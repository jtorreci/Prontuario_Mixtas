# core/classification_ec3.py
import math

# Límites c/t de EC3 Tabla 5.2 para clases (simplificado, usando valores para S235)
# Estos deberían ajustarse con epsilon = sqrt(235/fy)
# Usaremos límites conservadores (compresión pura) inicialmente para simplificar

# Límites para alas a compresión (Outstand flanges) - Compresión Pura
CLASS_LIMITS_FLANGE_COMP = {
    1: 9.0,
    2: 10.0,
    3: 14.0,
}
# Límites para almas a compresión (Internal compression parts) - Compresión Pura
CLASS_LIMITS_WEB_COMP = {
    1: 33.0,
    2: 38.0,
    3: 42.0,
}

def get_element_class(ratio_ct, epsilon, element_type="internal"):
    """Clasifica un elemento basado en c/t, epsilon y tipo."""
    if element_type == "outstand":
        limits = CLASS_LIMITS_FLANGE_COMP
    else: # internal (web)
        limits = CLASS_LIMITS_WEB_COMP

    if ratio_ct <= limits[1] * epsilon:
        return 1
    elif ratio_ct <= limits[2] * epsilon:
        return 2
    elif ratio_ct <= limits[3] * epsilon:
        return 3
    else:
        return 4

def classify_section_ec3(shapes, y_na, fy):
    """
    Realiza una clasificación SIMPLIFICADA de elementos de acero según EC3.

    Args:
        shapes (list): Lista de objetos de forma (SteelPlate, RotatedSteelPlate).
        y_na (float or None): Posición de la fibra neutra. Infinito si solo axil. None si sin tensiones.
        fy (float): Límite elástico del acero (MPa).

    Returns:
        dict: Contiene 'element_classes' (dict con clase por elemento),
              'overall_class' (clase global de la sección), 'warnings' (list).
    """
    results = {'element_classes': {}, 'overall_class': 1, 'warnings': []}
    if fy <= 0:
        results['warnings'].append("Fy inválido, no se puede calcular epsilon.")
        return results # No podemos clasificar sin fy

    epsilon = math.sqrt(235.0 / fy)
    max_class = 0 # Empezamos asumiendo clase 1 (la más favorable)

    for i, shape in enumerate(shapes):
        # Solo clasificamos chapas de acero
        if not hasattr(shape, 'material') or shape.material != "steel":
            continue

        element_key = f"steel_shape_{i+1}"
        shape_class = 1 # Asumir clase 1 por defecto si no está comprimido o no se analiza
        is_compressed = False # Flag para saber si alguna parte está comprimida

        try:
            y_min = shape.y_min
            y_max = shape.y_max
            t = 0.0 # Espesor
            c = 0.0 # Dimensión 'c' relevante para pandeo
            element_type = "internal" # Tipo por defecto

            # Determinar si la chapa está (parcialmente) en compresión
            # Necesitamos y_na. Si y_na es None o inf, la clasificación es diferente
            # (p.ej., compresión uniforme si y_na=inf y N<0).
            # Simplificación: si y_na es finito, asumimos flexión o flexo-compresión.
            if isinstance(y_na, (int, float)):
                # Asumimos compresión si la fibra neutra corta la pieza
                if y_na < y_max and y_na > y_min:
                    # Compresión parcial. Determinar la parte comprimida
                    # Si y_na > cg_y -> parte superior comprimida (y_na a y_max)
                    # Si y_na < cg_y -> parte inferior comprimida (y_min a y_na)
                    # Esta lógica asume M+ comprime arriba, necesita ser consistente con Navier
                    # Nuestro convenio Navier M+ comprime arriba (y>y_G)
                    # Nuestro cálculo de y_NA es y_NA = y_G + N*I/(M*A)
                    # Si M>0 (comprime arriba) y N=0, y_NA=y_G -> parte >y_G comprimida
                    # Si M>0 y N<0 (compresión), y_NA > y_G -> parte >y_NA comprimida
                    # Si M>0 y N>0 (tracción), y_NA < y_G -> parte >y_G comprimida
                    # Es complejo determinar la zona exacta sin las tensiones sigma_min/max

                    # Simplificación GROSERA: Si la FN corta, asumimos compresión y usamos la peor clase
                    # calculada como alma o ala, usando dimensiones totales. ¡Muy conservador!
                    is_compressed = True

                    # --- Lógica simplificada para SteelPlate ---
                    if isinstance(shape, SteelPlate):
                        h_dim = shape.height # Dimensión Y
                        w_dim = shape.width  # Dimensión X
                        # Heurística: Alma si H > W, Ala si W >= H
                        if h_dim > w_dim : # Alma vertical
                             element_type = "internal"
                             t = shape.width
                             c = shape.height # Altura total comprimida (conservador)
                        else: # Ala horizontal
                             element_type = "outstand"
                             t = shape.height
                             c = shape.width / 2 # Voladizo (conservador)

                    # --- Lógica simplificada para RotatedSteelPlate ---
                    elif isinstance(shape, RotatedSteelPlate):
                         element_type = "outstand" # Suponer siempre ala? O tratar como alma?
                         t = shape.t
                         c = shape.L # Usar longitud total? Muy conservador
                         results['warnings'].append(f"Clasificación Rotada {i+1} conservadora (c=L, t=t).")

                # Caso: Todo comprimido (y_na <= y_min) - Requiere comprobar signo N o tensiones
                # Caso: Todo traccionado (y_na >= y_max) - Clase 1
                # Simplificación: Si y_na está fuera, asumimos que la compresión domina si y_na está abajo
                elif y_na is not None and y_na <= y_min: # Potencialmente todo comprimido
                     is_compressed = True # Necesitaría chequeo de N o sigma
                     # Usar dimensiones totales como antes para ser conservador
                     if isinstance(shape, SteelPlate):
                          h_dim, w_dim = shape.height, shape.width
                          if h_dim > w_dim: t, c, element_type = w_dim, h_dim, "internal"
                          else: t, c, element_type = h_dim, w_dim / 2, "outstand"
                     elif isinstance(shape, RotatedSteelPlate):
                          t, c, element_type = shape.t, shape.L, "outstand" # Conservador
                          results['warnings'].append(f"Clasificación Rotada {i+1} conservadora (c=L, t=t).")

            # Si solo hay axil de compresión (y_na = +/- inf), todo está comprimido
            # Necesitaríamos N_ed aquí para saber el signo. Omitimos este caso por ahora.


            # Calcular clase si está comprimido y dimensiones válidas
            if is_compressed and t > 1e-6:
                ratio_ct = c / t
                shape_class = get_element_class(ratio_ct, epsilon, element_type)
                # Sobrescribir a Clase 1 si está conectado a hormigón (NO IMPLEMENTADO)
                # if is_connected_to_concrete(shape): shape_class = 1
            else:
                 shape_class = 1 # Si no está comprimido o espesor nulo

        except AttributeError:
            results['warnings'].append(f"Forma {i+1} ({type(shape)}) sin props. y_min/y_max para clasificación.")
            shape_class = 4 # Clase desconocida o no analizable -> pesimista
        except Exception as e:
             results['warnings'].append(f"Error clasificando forma {i+1}: {e}")
             shape_class = 4

        results['element_classes'][element_key] = shape_class
        if shape_class > max_class:
            max_class = shape_class

    # La clase global es la peor (más alta) de los elementos comprimidos
    results['overall_class'] = max_class

    # Advertencia sobre la no implementación de la regla EC4
    results['warnings'].append("Regla EC4 (contacto ala-hormigón -> Clase 1) NO implementada.")
    results['warnings'].append("Clasificación basada en heurística simple (alma/ala) y dimensiones totales comprimidas (conservador).")

    return results

