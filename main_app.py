## FILE: main_app.py
# main_app.py
import streamlit as st
import pandas as pd
import numpy as np
import math # Necesario para RotatedSteelPlate
import locale # Para formato de fecha
from datetime import datetime # Para fecha

# Importaciones (asumiendo estructura de carpetas correcta)
# Intentar importaciones relativas si se ejecuta como módulo, si no, directas.
try:
    # Asume que ejecutas desde la carpeta raíz del proyecto
    from core.materials import calculate_ecm_ec2, get_modular_ratio, DEFAULT_ES
    from core.section_analysis import calculate_section_properties
    from core.stress_analysis import calculate_navier_stress # NUEVO
    from core.classification_ec3 import classify_section_ec3 # NUEVO
    from shapes.steel_plate import SteelPlate # Chapa original (alineada con ejes)
    from shapes.concrete_trapezoid import ConcreteTrapezoid
    from shapes.rotated_steel_plate import RotatedSteelPlate # ¡Nueva clase!
    from visualization.plot_section import plot_section
except ImportError as e:
     # Fallback si algo falla, puede indicar problema con __init__.py o PYTHONPATH
     st.error(f"Error importando módulos: {e}. Asegúrate de ejecutar desde la carpeta raíz del proyecto y que los archivos __init__.py existen.")
     # Salir si las importaciones fallan, ya que la app no funcionará
     st.stop()


# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Análisis de Secciones Mixtas",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Estado de la Sesión ---
# Inicializar listas de formas si no existen
if 'shapes' not in st.session_state:
    st.session_state.shapes = []
if 'undo_stack' not in st.session_state:
     st.session_state.undo_stack = [] # Para posible función de deshacer
# Inicializar estado de edición si no existe
if 'editing_index' not in st.session_state:
     st.session_state.editing_index = None
# Inicializar estado para resultados de análisis (para que persistan si no se recalcula)
if 'stress_results' not in st.session_state:
     st.session_state.stress_results = None
if 'classification_results' not in st.session_state:
     st.session_state.classification_results = None
if 'last_analysis_inputs' not in st.session_state:
     st.session_state.last_analysis_inputs = {} # Guardar N, M, fy usados


# --- Funciones Auxiliares ---
def add_shape(shape_object):
    """Añade una forma a la lista y guarda el estado anterior para deshacer."""
    current_shapes_copy = [s for s in st.session_state.shapes]
    st.session_state.undo_stack.append(current_shapes_copy)
    max_undo = 10
    if len(st.session_state.undo_stack) > max_undo: st.session_state.undo_stack.pop(0)
    st.session_state.shapes.append(shape_object)
    # Limpiar resultados de análisis al modificar la geometría
    st.session_state.stress_results = None
    st.session_state.classification_results = None

def update_shape(index, updated_shape_object):
    """Actualiza una forma en la lista y guarda el estado anterior para deshacer."""
    if 0 <= index < len(st.session_state.shapes):
        current_shapes_copy = [s for s in st.session_state.shapes]
        st.session_state.undo_stack.append(current_shapes_copy)
        max_undo = 10
        if len(st.session_state.undo_stack) > max_undo: st.session_state.undo_stack.pop(0)
        st.session_state.shapes[index] = updated_shape_object
        # Limpiar resultados de análisis al modificar la geometría
        st.session_state.stress_results = None
        st.session_state.classification_results = None
    else:
        st.error(f"Índice de edición {index} fuera de rango.")

def delete_shape(index):
    """Elimina una forma de la lista y guarda el estado anterior para deshacer."""
    if 0 <= index < len(st.session_state.shapes):
        current_shapes_copy = [s for s in st.session_state.shapes]
        st.session_state.undo_stack.append(current_shapes_copy)
        max_undo = 10
        if len(st.session_state.undo_stack) > max_undo: st.session_state.undo_stack.pop(0)
        st.session_state.shapes.pop(index)
         # Limpiar resultados de análisis al modificar la geometría
        st.session_state.stress_results = None
        st.session_state.classification_results = None
        return True
    else:
        st.error(f"Índice de borrado {index} fuera de rango.")
        return False

def undo_last_action():
    """Restaura el estado anterior de las formas."""
    if st.session_state.undo_stack:
        previous_shapes = st.session_state.undo_stack.pop()
        st.session_state.shapes = previous_shapes
        st.session_state.editing_index = None # Cancelar edición al deshacer
         # Limpiar resultados de análisis al deshacer cambio geométrico
        st.session_state.stress_results = None
        st.session_state.classification_results = None
        st.success("Última acción deshecha.")
        st.rerun()
    else:
        st.warning("No hay acciones que deshacer.")

# --- Interfaz Principal ---
st.title("📊 Analizador de Secciones Mixtas")
st.write("Herramienta para calcular propiedades geométricas, tensiones y clasificación de secciones compuestas Hormigón-Acero.")
st.write("*(Homogeneización: Hormigón transformado a Acero equivalente)*")


# --- Columnas para layout ---
col_input, col_results = st.columns([1, 1.5]) # Columna izquierda más estrecha

# --- Columna de Entrada ---
with col_input:
    st.header("🏗️ Definición de la Sección")

    # --- Contenedor para Materiales ---
    with st.container(border=True):
        st.subheader("GPa | Materiales")
        c1, c2 = st.columns(2)
        with c1:
            fck = st.number_input(
                "Hormigón, $f_{ck}$ (MPa)",
                min_value=12.0, max_value=90.0, value=30.0, step=1.0, key="fck_input",
                help="Resistencia característica del hormigón a compresión."
            )
        with c2:
            Es = st.number_input(
                "Acero, $E_s$ (MPa)",
                value=DEFAULT_ES, format="%f", step=1000.0, key="Es_input",
                help="Módulo de elasticidad del acero estructural."
            )
        # Calcular n y Ecm (manejar posible error fuera de la sección de resultados)
        n_display = "N/A"; n = 0; Ecm = 0
        try:
            n = get_modular_ratio(fck, Es)
            if n == float('inf') or n <= 0:
                st.warning(f"n inválido ({n:.2f}). Verifique fck/Es.")
                n_display = "Inválido"
            else:
                Ecm = Es / n
                st.caption(f"$E_{{cm}} \\approx {Ecm:.0f}$ MPa | $n \\approx {n:.2f}$")
                n_display = f"{n:.2f}"
        except Exception as e:
            st.error(f"Error en materiales: {e}")
            n_display = "Error"

    # --- Contenedor para Geometría ---
    with st.container(border=True):
        st.subheader("📐 Geometría")

        # Determinar estado de edición (debe hacerse antes de renderizar los forms)
        editing_mode = st.session_state.editing_index is not None
        shape_being_edited = None
        shape_type_being_edited = None
        edit_info_placeholder = st.empty() # Placeholder para mensaje de edición
        if editing_mode:
            try:
                shape_being_edited = st.session_state.shapes[st.session_state.editing_index]
                shape_type_being_edited = type(shape_being_edited)
                edit_info_placeholder.info(f"✏️ Editando Componente #{st.session_state.editing_index + 1} ({shape_type_being_edited.__name__}).")
            except IndexError:
                st.error("Error: Índice de edición no válido. Cancelando edición.")
                st.session_state.editing_index = None
                editing_mode = False # Actualizar flag

        # Pestañas para añadir/editar formas
        tab_aligned, tab_rotated, tab_concrete = st.tabs(["Chapa Alineada", "Chapa Rotada", "Hormigón Trapecio"])

        # Formulario Chapa Alineada
        with tab_aligned:
            editing_this_type = editing_mode and shape_type_being_edited == SteelPlate
            default_values_aligned = {}
            if editing_this_type: default_values_aligned = {"s_w": shape_being_edited.width, "s_h": shape_being_edited.height, "s_x": shape_being_edited.cg_x, "s_y": shape_being_edited.cg_y}
            with st.form("form_aligned", clear_on_submit=False, border=False):
                st.caption("Rectángulo alineado con ejes X, Y.")
                c1, c2 = st.columns(2); c3, c4 = st.columns(2)
                s_width = c1.number_input("Ancho (X)", min_value=0.1, value=default_values_aligned.get("s_w", 100.0), key="s_w_in")
                s_height = c2.number_input("Alto (Y)", min_value=0.1, value=default_values_aligned.get("s_h", 10.0), key="s_h_in")
                s_cg_x = c3.number_input("CDG X", format="%f", value=default_values_aligned.get("s_x", 0.0), key="s_x_in")
                s_cg_y = c4.number_input("CDG Y", format="%f", value=default_values_aligned.get("s_y", 0.0), key="s_y_in")
                submit_label = "💾 Guardar" if editing_this_type else "➕ Añadir"
                col_s, col_c = st.columns([0.7, 0.3])
                submitted = col_s.form_submit_button(submit_label, use_container_width=True, disabled=editing_mode and not editing_this_type)
                if editing_this_type:
                    if col_c.form_submit_button("❌ Cancelar", use_container_width=True):
                        st.session_state.editing_index = None; st.rerun()
                if submitted:
                    try:
                        plate = SteelPlate(s_width, s_height, s_cg_x, s_cg_y)
                        if editing_this_type: update_shape(st.session_state.editing_index, plate); st.success("Actualizado"); st.session_state.editing_index = None
                        else: add_shape(plate); st.success("Añadido")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        # Formulario Chapa Rotada
        with tab_rotated:
            editing_this_type = editing_mode and shape_type_being_edited == RotatedSteelPlate
            default_values_rotated = {}; initial_def_idx = 0
            if editing_this_type:
                shape = shape_being_edited
                default_values_rotated = {"t": shape.t, "p1x": shape.p1[0], "p1y": shape.p1[1], "p2x": shape.p2[0], "p2y": shape.p2[1],
                                          "vx": shape._vector_original[0], "vy": shape._vector_original[1], "l": shape._length_original}
                initial_def_idx = 1 if shape.definition_method == 'Vector' else 0
            with st.form("form_rotated", clear_on_submit=False, border=False):
                st.caption("Rectángulo con orientación genérica.")
                rot_t = st.number_input("Espesor", min_value=0.1, value=default_values_rotated.get("t", 10.0), key="rot_t_in")
                def_method = st.radio("Definir por:", ('Puntos', 'Vector+Longitud'), index=initial_def_idx, key="rot_method_in", horizontal=True)
                c1, c2 = st.columns(2)
                rot_p1_x = c1.number_input("P1 X", format="%f", value=default_values_rotated.get("p1x", 0.0), key="rot_p1x_in")
                rot_p1_y = c2.number_input("P1 Y", format="%f", value=default_values_rotated.get("p1y", 0.0), key="rot_p1y_in")
                if def_method == 'Puntos':
                    c1, c2 = st.columns(2)
                    rot_p2_x = c1.number_input("P2 X", format="%f", value=default_values_rotated.get("p2x", 100.0), key="rot_p2x_in")
                    rot_p2_y = c2.number_input("P2 Y", format="%f", value=default_values_rotated.get("p2y", 0.0), key="rot_p2y_in")
                    rot_v_x, rot_v_y, rot_l = None, None, None
                else:
                    c1, c2, c3 = st.columns(3)
                    rot_v_x = c1.number_input("Vec X", format="%f", value=default_values_rotated.get("vx", 1.0), key="rot_vx_in")
                    rot_v_y = c2.number_input("Vec Y", format="%f", value=default_values_rotated.get("vy", 0.0), key="rot_vy_in")
                    rot_l = c3.number_input("Longitud", min_value=0.1, format="%f", value=default_values_rotated.get("l", 100.0), key="rot_l_in")
                    rot_p2_x, rot_p2_y = None, None
                submit_label = "💾 Guardar" if editing_this_type else "➕ Añadir"
                col_s, col_c = st.columns([0.7, 0.3])
                submitted = col_s.form_submit_button(submit_label, use_container_width=True, disabled=editing_mode and not editing_this_type)
                if editing_this_type:
                    if col_c.form_submit_button("❌ Cancelar", use_container_width=True): st.session_state.editing_index = None; st.rerun()
                if submitted:
                    try:
                        kwargs = {'thickness': rot_t, 'p1': (rot_p1_x, rot_p1_y)}
                        if def_method == 'Puntos': kwargs.update({'p2': (rot_p2_x, rot_p2_y), 'definition_method': 'Points'})
                        else: kwargs.update({'vector': (rot_v_x, rot_v_y), 'length': rot_l, 'definition_method': 'Vector'})
                        plate = RotatedSteelPlate(**kwargs)
                        if editing_this_type: update_shape(st.session_state.editing_index, plate); st.success("Actualizado"); st.session_state.editing_index = None
                        else: add_shape(plate); st.success("Añadido")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        # Formulario Trapecio Hormigón
        with tab_concrete:
            editing_this_type = editing_mode and shape_type_being_edited == ConcreteTrapezoid
            default_values_concrete = {}
            if editing_this_type: default_values_concrete = {"b1": shape_being_edited.b1, "b2": shape_being_edited.b2, "h": shape_being_edited.h, "bx": shape_being_edited.bc_x, "by": shape_being_edited.bc_y}
            with st.form("form_concrete", clear_on_submit=False, border=False):
                st.caption("Trapecio de hormigón (simétrico).")
                c1, c2 = st.columns(2); c3, c4 = st.columns(2); c5, c6 = st.columns(2)
                c_b1 = c1.number_input("Ancho inf b1", min_value=0.0, format="%f", value=default_values_concrete.get("b1", 300.0), key="c_b1_in")
                c_b2 = c2.number_input("Ancho sup b2", min_value=0.0, format="%f", value=default_values_concrete.get("b2", 300.0), key="c_b2_in")
                c_h = c3.number_input("Altura h", min_value=0.1, format="%f", value=default_values_concrete.get("h", 200.0), key="c_h_in")
                c_bc_x = c5.number_input("X Centro Base", format="%f", value=default_values_concrete.get("bx", 0.0), key="c_bx_in")
                c_bc_y = c6.number_input("Y Nivel Base", format="%f", value=default_values_concrete.get("by", 0.0), key="c_by_in")
                submit_label = "💾 Guardar" if editing_this_type else "➕ Añadir"
                col_s, col_c = st.columns([0.7, 0.3])
                submitted = col_s.form_submit_button(submit_label, use_container_width=True, disabled=editing_mode and not editing_this_type)
                if editing_this_type:
                    if col_c.form_submit_button("❌ Cancelar", use_container_width=True): st.session_state.editing_index = None; st.rerun()
                if submitted:
                    try:
                        trap = ConcreteTrapezoid(c_b1, c_b2, c_h, c_bc_x, c_bc_y)
                        if editing_this_type: update_shape(st.session_state.editing_index, trap); st.success("Actualizado"); st.session_state.editing_index = None
                        else: add_shape(trap); st.success("Añadido")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

    # --- Contenedor para Lista de Componentes ---
    with st.container(border=True):
        st.subheader("🧩 Componentes Actuales")
        if not st.session_state.shapes:
            st.caption("Añade componentes usando las pestañas de arriba.")
        else:
            # Scrollable container for the list
            with st.container(height=250): # Ajustar altura si es necesario
                indices_a_borrar = []
                for i, shape in enumerate(st.session_state.shapes):
                    col1, col_edit, col_del = st.columns([0.8, 0.1, 0.1])
                    shape_desc = f"**{i+1}:** "; y_info = ""
                    try:
                        if isinstance(shape, SteelPlate): shape_desc += f"Chapa Alin. [A={shape.width:.1f}, H={shape.height:.1f}]"
                        elif isinstance(shape, RotatedSteelPlate): shape_desc += f"Chapa Rot. [L={shape.L:.1f}, t={shape.t:.1f}, θ={math.degrees(shape.theta):.1f}°]"
                        elif isinstance(shape, ConcreteTrapezoid): shape_desc += f"Trapecio [b1={shape.b1:.1f}, b2={shape.b2:.1f}, h={shape.h:.1f}]"
                        else: shape_desc += f"{type(shape).__name__}"
                        if hasattr(shape, 'y_min') and hasattr(shape, 'y_max'): y_info = f" (Y: {shape.y_min:.1f} a {shape.y_max:.1f})"
                    except Exception as e: shape_desc += f" Error: {e}"
                    col1.write(shape_desc + y_info)
                    edit_disabled = editing_mode and st.session_state.editing_index != i
                    if col_edit.button("✏️", key=f"edit_{i}", help="Editar", disabled=edit_disabled): st.session_state.editing_index = i; st.rerun()
                    delete_disabled = editing_mode
                    if col_del.button("🗑️", key=f"del_{i}", help="Eliminar", disabled=delete_disabled): indices_a_borrar.append(i)

            if indices_a_borrar:
                indices_borrados_ok = 0
                for index in sorted(indices_a_borrar, reverse=True):
                    if delete_shape(index):
                         indices_borrados_ok += 1
                         if editing_mode and st.session_state.editing_index == index: st.session_state.editing_index = None
                         elif editing_mode and index < st.session_state.editing_index: st.session_state.editing_index -= 1
                st.success(f"Eliminado(s) {indices_borrados_ok} componente(s)."); st.rerun()

        # --- Botones Apilar y Deshacer (fuera del scroll) ---
        col_stack, col_undo = st.columns(2)
        with col_stack:
            if st.session_state.shapes and not editing_mode:
                 last_shape = st.session_state.shapes[-1]
                 can_stack = isinstance(last_shape, SteelPlate) or isinstance(last_shape, RotatedSteelPlate)
                 if can_stack:
                     if st.button("➕ Apilar Chapa", key="stack_plate", help="Añade chapa sobre la última.", use_container_width=True):
                         try:
                             y_max_last = last_shape.y_max
                             if isinstance(last_shape, SteelPlate):
                                 new_h = last_shape.height; new_y = y_max_last + new_h / 2
                                 new_p = SteelPlate(last_shape.width, new_h, last_shape.cg_x, new_y)
                                 add_shape(new_p); st.success("Apilada."); st.rerun()
                             elif isinstance(last_shape, RotatedSteelPlate):
                                 st.warning("Apilado sobre Rotada: Añadiendo chapa Alineada.")
                                 new_h = 10.0; new_w = last_shape.t; new_y = y_max_last + new_h / 2
                                 new_p = SteelPlate(new_w, new_h, last_shape.cg_x, new_y)
                                 add_shape(new_p); st.success("Apilada."); st.rerun()
                         except Exception as e: st.error(f"Error al apilar: {e}")
        with col_undo:
             if st.session_state.undo_stack:
                 if st.button("↩️ Deshacer", use_container_width=True): undo_last_action()

    # --- Contenedor para Acciones y Análisis ---
    with st.container(border=True):
        st.subheader("⚙️ Acciones y Análisis")
        last_N = st.session_state.last_analysis_inputs.get('N', 0.0)
        last_M = st.session_state.last_analysis_inputs.get('M', 100.0)
        last_fy = st.session_state.last_analysis_inputs.get('fy', 235.0)
        c1, c2 = st.columns(2)
        N_ed_kn = c1.number_input("Axil $N_{Ed}$ [kN]", value=last_N, format="%.2f", key="N_ed_in")
        Mx_ed_knm = c2.number_input("Momento $M_{x,Ed}$ [kN·m]", value=last_M, format="%.2f", key="Mx_ed_in")
        fy = st.number_input("Límite Elástico $f_y$ [MPa]", min_value=200.0, value=last_fy, step=5.0, key="fy_in")
        run_analysis = st.button("🚀 Calcular Tensiones y Clasificar", type="primary", use_container_width=True, disabled=not st.session_state.shapes)
        if run_analysis: st.session_state.last_analysis_inputs = {'N': N_ed_kn, 'M': Mx_ed_knm, 'fy': fy}

# --- Fin Columna de Entrada ---


# --- Columna de Resultados ---
with col_results:
    st.header("📊 Resultados del Análisis")

    # Inicializar variables de resultados
    props_homog = None
    n = 0
    n_display = "N/A"

    # --- Cálculo y Visualización de Propiedades ---
    if st.session_state.shapes:
        try:
            # Recalcular n aquí por si fck/Es cambiaron desde la última vez
            n = get_modular_ratio(fck, Es) # Usa fck, Es de la columna de input
            if n == float('inf') or n <= 0:
                st.error(f"Relación modular n inválida ({n:.2f}). Verifique fck/Es.")
                n_display = "Inválido"
            else:
                n_display = f"{n:.2f}"
                # Calcular propiedades si n es válido
                props_orig = calculate_section_properties(st.session_state.shapes, homogenize=False)
                props_homog = calculate_section_properties(st.session_state.shapes, homogenize=True, modular_ratio=n)

                # Mostrar propiedades geométricas
                st.subheader("📈 Propiedades Geométricas")
                def format_num(value, precision=2, is_area=False, is_inertia=False):
                    try:
                        num = float(value)
                        if is_inertia: return f"{num:,.{precision}e} mm⁴"
                        unit = " mm²" if is_area else " mm"
                        return f"{num:,.{precision}f}{unit}"
                    except: return str(value) if value is not None else "Error"
                data = {
                    'Propiedad': ['Área (A)', 'CDG X (Xg)', 'CDG Y (Yg)', 'Inercia Ix', 'Inercia Iy'],
                    'Original': [format_num(props_orig['total_area'], 1, True), format_num(props_orig['centroid_x']), format_num(props_orig['centroid_y']),
                                 format_num(props_orig.get('inertia_x'), 3, is_inertia=True) or "N/A", format_num(props_orig.get('inertia_y'), 3, is_inertia=True) or "N/A"],
                    'Homog. (a Acero)': [f"{format_num(props_homog['total_area'], 1, True)}", f"{format_num(props_homog['centroid_x'])}", f"{format_num(props_homog['centroid_y'])}",
                                          f"{format_num(props_homog.get('inertia_x'), 3, is_inertia=True) or 'N/A'}", f"{format_num(props_homog.get('inertia_y'), 3, is_inertia=True) or 'N/A'}"]
                }
                st.dataframe(pd.DataFrame(data).set_index('Propiedad'), use_container_width=True)

                # Visualización de secciones
                st.subheader("🖼️ Visualización Sección")
                plot_xlims, plot_ylims = None, None
                all_orig_vertices = [vt for shape in st.session_state.shapes for vt in shape.get_vertices(1.0)]
                if all_orig_vertices:
                     all_x = [v[0] for v in all_orig_vertices] + [0]; all_y = [v[1] for v in all_orig_vertices] + [0]
                     g_min_x, g_max_x, g_min_y, g_max_y = min(all_x), max(all_x), min(all_y), max(all_y)
                     dx, dy = max(g_max_x - g_min_x, 20), max(g_max_y - g_min_y, 20)
                     mx, my = dx * 0.15 + 10, dy * 0.15 + 10
                     plot_xlims, plot_ylims = (g_min_x - mx, g_max_x + mx), (g_min_y - my, g_max_y + my)

                # --- Mostrar Plots usando los límites calculados ---
                plot_col1, plot_col2 = st.columns(2)

                with plot_col1:
                    st.write("**Sección Original**")
                    st.caption("CDG Original marcado en rojo.")
                    try:
                        # --- LLAMADA ORIGINAL INCORRECTA (implícita) ---
                        # fig_orig = plot_section(st.session_state.shapes, "", props_orig.get('centroid_x'), props_orig.get('centroid_y'), "CDG Orig.", xlims=plot_xlims, ylims=plot_ylims) # Incorrecta!

                        # --- LLAMADA CORREGIDA ---
                        centroid_orig_dict = None
                        if props_orig: # Asegurarse que props_orig existe
                            centroid_orig_dict = {'x': props_orig.get('centroid_x'), 'y': props_orig.get('centroid_y')}

                        fig_orig = plot_section(
                            shapes=st.session_state.shapes,
                            title="", # Título vacío o "Sección Original"
                            highlight_centroid=centroid_orig_dict, # Pasar como dict
                            centroid_label="CDG Orig.",
                            # homogenize_visual=False, # Es el default, no necesario
                            # modular_ratio=None, # No aplica
                            xlims=plot_xlims, # Pasar por nombre
                            ylims=plot_ylims  # Pasar por nombre
                        )
                        st.pyplot(fig_orig, use_container_width=True)
                    except Exception as plot_err: st.error(f"Err Graf Orig: {plot_err}")

                with plot_col2:
                    st.write(f"**Visual. Homogeneizada**")
                    st.caption(f"Hormigón (ancho/{n_display}). CDG Homog. en rojo.")
                    # Solo intentar plotear si n es válido y props_homog existe
                    if n > 0 and props_homog:
                        try:
                            # --- LLAMADA ORIGINAL INCORRECTA ---
                            # fig_homog = plot_section(st.session_state.shapes, "", props_homog.get('centroid_x'), props_homog.get('centroid_y'), "CDG Homog.", True, n, xlims=plot_xlims, ylims=plot_ylims) # Incorrecta!

                            # --- LLAMADA CORREGIDA ---
                            centroid_homog_dict = {'x': props_homog.get('centroid_x'), 'y': props_homog.get('centroid_y')}

                            fig_homog_vis = plot_section(
                                shapes=st.session_state.shapes,
                                title="", # Título vacío o "Visual. Homog."
                                highlight_centroid=centroid_homog_dict, # Pasar como dict
                                centroid_label="CDG Homog.",
                                homogenize_visual=True, # Indicar visualización homogeneizada
                                modular_ratio=n, # Pasar n (asegurado que es > 0)
                                xlims=plot_xlims, # Pasar por nombre
                                ylims=plot_ylims  # Pasar por nombre
                            )
                            st.pyplot(fig_homog_vis, use_container_width=True)
                        except Exception as plot_err: st.error(f"Err Graf Homog: {plot_err}")
                    else:
                        # Mostrar un placeholder o mensaje si no se puede dibujar
                        st.warning("No se puede generar gráfico homogeneizado (n inválido o error en props).")


        except Exception as e:
            st.error(f"Error calculando propiedades/visualización: {e}")
            props_homog = None # Indicar fallo

    else: # Si no hay formas
         st.info("Añada componentes geométricos para ver los resultados.")
         props_homog = None


    # --- SECCIÓN: Resultados de Tensiones y Clasificación ---
    st.markdown("---")
    st.header("🔬 Tensiones y Clasificación")

    # Ejecutar análisis si se pulsó el botón
    if run_analysis:
        if props_homog and n > 0:
            N_ed_kn = st.session_state.last_analysis_inputs.get('N', 0.0)
            Mx_ed_knm = st.session_state.last_analysis_inputs.get('M', 0.0)
            fy = st.session_state.last_analysis_inputs.get('fy', 0.0)
            N_ed_N, Mx_ed_Nmm = N_ed_kn * 1000.0, Mx_ed_knm * 1e6
            st.session_state.stress_results = calculate_navier_stress(N_ed_N, Mx_ed_Nmm, st.session_state.shapes, props_homog)
            y_na = st.session_state.stress_results.get('y_na')
            st.session_state.classification_results = classify_section_ec3(st.session_state.shapes, y_na, fy)
        else:
            st.session_state.stress_results, st.session_state.classification_results = None, None
            if not props_homog: st.error("Faltan propiedades homogeneizadas.")
            if n <= 0: st.error("Relación modular inválida.")


    # Mostrar resultados si existen en el estado
    if st.session_state.stress_results:
        sr = st.session_state.stress_results
        if sr['error']: st.error(f"Error Tensiones: {sr['error']}")
        else:
            st.subheader("⚡ Tensiones Elásticas (Navier)")
            y_na = sr['y_na']
            if y_na is None: st.write("FN (y_NA): Indeterminada.")
            elif y_na == float('inf') or y_na == float('-inf'): st.write("FN (y_NA): Infinito (solo axil).")
            else: st.write(f"FN (y_NA): {y_na:.2f} mm")
            st.caption("Tensiones (Acero Equivalente y Real):")
            stress_data = []; max_ss, min_ss = -float('inf'), float('inf'); max_sc, min_sc = -float('inf'), float('inf')
            for k, d in sr['stresses'].items():
                 s_eq = d['sigma_eq']; is_c = d['mat']=='concrete'; s_r = s_eq/n if is_c and n>0 else s_eq
                 stress_data.append({"Comp": k.split('_')[1], "Pt": "min" if "min" in k else "max", "Y": f"{d['y']:.1f}", "σEq": f"{s_eq:.1f}", "σReal": f"{s_r:.1f}", "M": "H" if is_c else "A"})
                 if is_c: max_sc, min_sc = max(max_sc, s_r), min(min_sc, s_r)
                 else: max_ss, min_ss = max(max_ss, s_r), min(min_ss, s_r)
            if stress_data:
                 st.dataframe(pd.DataFrame(stress_data), use_container_width=True, hide_index=True, height=200)
                 st.markdown(f"**Resumen $\sigma$ Real:** Acero [{min_ss:.1f}, {max_ss:.1f}] MPa" + (f" | Hormigón [{min_sc:.1f}, {max_sc:.1f}] MPa" if max_sc > -float('inf') else ""))
            else: st.caption("No se calcularon tensiones.")

    if st.session_state.classification_results:
        cr = st.session_state.classification_results
        st.subheader("🔢 Clasificación Sección (EC3/EC4 - Simplif.)")
        st.write(f"**Clase Global Sección: {cr['overall_class']}**")
        class_data = [{"Comp. Acero #": k.split('_')[-1], "Clase": v} for k, v in cr['element_classes'].items()]
        if class_data: st.dataframe(pd.DataFrame(class_data), hide_index=True, use_container_width=True)
        else: st.caption("No hay elementos de acero a clasificar.")
        if cr['warnings']: st.warning("Advertencias Clasificación:")
        for w in cr.get('warnings', []): st.warning(f"- {w}")

    if not st.session_state.stress_results and not st.session_state.classification_results:
         st.info("Introduzca acciones y pulse 'Calcular Tensiones y Clasificar'.")


# --- Pié de Página o Sidebar ---
st.sidebar.header("Acerca de")
st.sidebar.info(
    f"""
    **Analizador de Secciones Mixtas v0.6**

    Calcula props. geométricas, tensiones (Navier) y clasificación
    simplif. (EC3/EC4@{st.session_state.last_analysis_inputs.get('fy', 'N/A')} MPa).
    - Homog.: Horm.->Acero (n={n_display}).
    - Visual.: Orig./Homog. (escala común).
    - Edición, Apilado, Deshacer.
    """
)
# ... (resto sidebar con fecha y versiones) ...
st.sidebar.markdown("---")
try: locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except: pass
now = datetime.now(); current_date_str = now.strftime("%A, %d %b %Y - %H:%M:%S")
st.sidebar.markdown(f"*{current_date_str} (Cáceres)*")
try:
    import streamlit as st_ver; sv = st_ver.__version__; import pandas as pd_ver; pv = pd_ver.__version__
    import matplotlib as mpl_ver; mv = mpl_ver.__version__; import numpy as np_ver; nv = np_ver.__version__
    st.sidebar.caption(f"Streamlit v{sv} | Pandas v{pv} | Matplotlib v{mv} | Numpy v{nv}")
except: pass