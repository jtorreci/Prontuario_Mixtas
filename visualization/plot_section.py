# visualization/plot_section.py
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math

def plot_section(shapes, title="Sección Transversal", highlight_centroid=None, centroid_label="CDG",
                 homogenize_visual=False, modular_ratio=None,
                 xlims=None, ylims=None): # <-- NUEVOS ARGUMENTOS
    """
    Dibuja la sección transversal usando Matplotlib.
    Puede dibujar la sección original o una visualización homogeneizada (Hormigón->Acero).
    Permite especificar límites de ejes para consistencia entre plots.

    Args:
        # ... (argumentos anteriores) ...
        xlims (tuple, optional): Tupla (min_x, max_x) para los límites del eje X.
        ylims (tuple, optional): Tupla (min_y, max_y) para los límites del eje Y.
    """
    if homogenize_visual and (modular_ratio is None or modular_ratio <= 0):
        # Manejar caso inválido, quizás dibujando la original o mostrando error
        print(f"Advertencia: modular_ratio inválido ({modular_ratio}) para visualización homogeneizada. Dibujando original.")
        homogenize_visual = False # Dibujar la original como fallback
        # O podríamos lanzar un error:
        # raise ValueError("Se requiere 'modular_ratio' positivo para la visualización homogeneizada.")


    # Reducir figsize para que los gráficos sean más pequeños
    fig, ax = plt.subplots(figsize=(6, 6)) # <- Tamaño ajustado

    all_vertices_plot = [] # Vértices usados para este plot específico (para auto-escala si no se dan límites)
    legend_handles = {} # Para evitar leyendas duplicadas

    for shape in shapes:
        scale_factor = 1.0
        color = 'grey' # Default color
        hatch = None   # Default hatch
        base_label = "Desconocido" # Default label

        # Determinar estilo basado en material y si se visualiza homogeneización
        is_concrete = hasattr(shape, 'material') and shape.material == "concrete"
        is_steel = hasattr(shape, 'material') and shape.material == "steel"

        label_suffix = ""
        if is_steel:
             color = 'lightblue'
             hatch = '//'
             base_label = 'Acero'
        elif is_concrete:
             color = 'lightgrey'
             hatch = '..'
             base_label = 'Hormigón'
             if homogenize_visual:
                 # Asegurarse de que modular_ratio es válido antes de dividir
                 if modular_ratio is not None and modular_ratio > 0:
                     scale_factor = 1.0 / modular_ratio
                 else:
                     scale_factor = 1.0 # O manejar error
                 # Cambiar estilo para hormigón homogeneizado visualmente
                 color = 'lightcoral' # Diferente color
                 hatch = 'xx'
                 label_suffix = f' (Ancho/{modular_ratio:.2f})' if modular_ratio else ' (Error Ratio)'


        # Obtener vértices (escalados si es necesario para este plot)
        try:
            vertices = shape.get_vertices(width_scale_factor=scale_factor)
            all_vertices_plot.extend(vertices) # Añadir a la lista de este plot
        except TypeError: # Si get_vertices no acepta el argumento (clases antiguas?)
             print(f"Advertencia: {type(shape)}.get_vertices no acepta width_scale_factor. Usando factor 1.0.")
             vertices = shape.get_vertices()
             all_vertices_plot.extend(vertices)
        except Exception as e:
            print(f"Error obteniendo vértices para {type(shape)}: {e}. Saltando forma.")
            continue # Saltar esta forma si no se pueden obtener los vértices


        # Dibujar el polígono
        final_label = f"{base_label}{label_suffix}"
        # closed=True es el default para Polygon, pero lo ponemos explícito
        poly = patches.Polygon(vertices, closed=True, facecolor=color, edgecolor='black', hatch=hatch)
        ax.add_patch(poly)

        # Añadir a leyenda si es la primera vez que vemos este tipo/material/estado
        if final_label not in legend_handles:
             legend_handles[final_label] = poly # Guardar el patch para la leyenda

        # Anotar CDG original de la parte (siempre sobre la geometría original, si no es visualización homog.)
        # y si la forma tiene las propiedades cg_x, cg_y
        if not homogenize_visual and hasattr(shape, 'cg_x') and hasattr(shape, 'cg_y'):
             try:
                 ax.plot(shape.cg_x, shape.cg_y, 'ko', markersize=3, label='_nolegend_') # k=black, o=circle, no en leyenda
             except Exception as e:
                 print(f"Advertencia: No se pudo dibujar CDG para {type(shape)}: {e}")


    # --- Configurar límites y aspecto del gráfico ---

    # Usar límites proporcionados si existen
    if xlims is not None:
        ax.set_xlim(xlims)
    elif all_vertices_plot: # Auto-escala X si no se proporcionan límites y hay vértices
        all_x = [v[0] for v in all_vertices_plot]
        min_x, max_x = min(all_x), max(all_x)
        delta_x = max(max_x - min_x, 10)
        margin_x = delta_x * 0.15 + 10 # Margen ajustado
        ax.set_xlim(min_x - margin_x, max_x + margin_x)
    else:
        ax.set_xlim(-100, 100) # Default si no hay vértices ni límites

    if ylims is not None:
        ax.set_ylim(ylims)
    elif all_vertices_plot: # Auto-escala Y si no se proporcionan límites y hay vértices
        all_y = [v[1] for v in all_vertices_plot]
        min_y, max_y = min(all_y), max(all_y)
        delta_y = max(max_y - min_y, 10)
        margin_y = delta_y * 0.15 + 10 # Margen ajustado
        ax.set_ylim(min_y - margin_y, max_y + margin_y)
    else:
        ax.set_ylim(-100, 100) # Default

    # Dibujar centroide global resaltado si se proporciona
    if highlight_centroid and isinstance(highlight_centroid, dict) and 'x' in highlight_centroid and 'y' in highlight_centroid:
        try:
            cx, cy = highlight_centroid['x'], highlight_centroid['y']
            # Usar un marcador distinto y color llamativo
            marker_style = 'X' # 'X' o 'P' (plus) son visibles
            marker_color = 'red'
            marker_size = 8 # Reducir tamaño ligeramente
            marker = ax.plot(cx, cy, marker=marker_style, color=marker_color, markersize=marker_size, linestyle='None', label=centroid_label)[0]
            # Añadir texto cerca del marcador
            ax.text(cx, cy, f'  {centroid_label}', color=marker_color, va='bottom', ha='left', fontsize=8, fontweight='bold') # Fuente más pequeña
            # Añadir a la leyenda si no estaba ya (poco probable con etiqueta única)
            if centroid_label not in legend_handles:
                 legend_handles[centroid_label] = marker
        except Exception as e:
            print(f"Advertencia: No se pudo dibujar el centroide resaltado ({centroid_label}): {e}")


    # Configuración final del plot
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel("Coordenada X (mm)")
    ax.set_ylabel("Coordenada Y (mm)")
    ax.set_title(title, fontsize=10, fontweight='bold') # Fuente más pequeña para el título
    ax.grid(True, linestyle=':', linewidth=0.5, color='gray', alpha=0.7) # Estilo de rejilla más sutil
    # Crear leyenda única a partir de los handles guardados
    if legend_handles:
         ax.legend(legend_handles.values(), legend_handles.keys(), loc='best', fontsize=8) # Leyenda más pequeña

    # Devolver la figura de matplotlib
    return fig

