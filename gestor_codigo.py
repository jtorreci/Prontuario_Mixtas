#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
import sys
import re

# --- Marcador estándar para separar archivos en el bloque de texto ---
# Usamos un formato que sea comentario en muchos lenguajes y poco probable
# que aparezca naturalmente en el código.
FILE_MARKER_PREFIX = "## FILE: "

def create_files_from_block(code_block, base_dir="."):
    """
    Crea archivos y directorios a partir de un bloque de texto con marcadores.

    Args:
        code_block (str): El string multilínea que contiene el código y los marcadores.
        base_dir (str): El directorio base donde se crearán los archivos/carpetas.
    """
    current_file_path = None
    output_file = None
    lines = code_block.splitlines() # Usar splitlines para manejar diferentes finales de línea

    print(f"--- Creando archivos en el directorio base: {os.path.abspath(base_dir)} ---")

    try:
        for i, line in enumerate(lines):
            # Usamos strip() para eliminar espacios en blanco alrededor del marcador
            if line.strip().startswith(FILE_MARKER_PREFIX):
                if output_file:
                    output_file.close()
                    print(f"   [OK] Escrito: {current_file_path}")

                # Extraer la ruta relativa del archivo del marcador
                relative_path = line.strip()[len(FILE_MARKER_PREFIX):].strip()
                # Reemplazar separadores por el nativo del SO si es necesario,
                # aunque os.path.join debería manejarlo. Mejor normalizar a / y luego usar os.path.join
                normalized_relative_path = relative_path.replace('\\', '/')
                current_file_path = os.path.join(base_dir, *normalized_relative_path.split('/'))

                # Asegurarse de que el directorio exista
                dir_name = os.path.dirname(current_file_path)
                if dir_name: # Solo crear si no es el directorio base
                    if not os.path.exists(dir_name):
                         os.makedirs(dir_name, exist_ok=True)
                         print(f"   Directorio creado: {dir_name}")
                    elif not os.path.isdir(dir_name):
                         raise OSError(f"Error: '{dir_name}' existe pero no es un directorio.")


                # Abrir el nuevo archivo para escribir
                try:
                     output_file = open(current_file_path, 'w', encoding='utf-8')
                     print(f"   Abriendo para escribir: {current_file_path}...")
                except IOError as e:
                     print(f"\nERROR: No se pudo abrir el archivo '{current_file_path}' para escribir: {e}", file=sys.stderr)
                     # Decidir si continuar o abortar. Abortemos por seguridad.
                     if output_file: output_file.close() # Cerrar el anterior si estaba abierto
                     raise # Re-lanzar la excepción para detener el script


            elif output_file:
                # Escribir la línea en el archivo actual (manteniendo el final de línea original)
                # Para ello, volvemos a añadir \n ya que splitlines() lo quita.
                # Considerar no añadir \n si es la última línea del bloque y estaba vacía?
                # Por simplicidad, siempre añadimos \n.
                try:
                     output_file.write(line + '\n')
                except IOError as e:
                     print(f"\nERROR: No se pudo escribir en el archivo '{current_file_path}': {e}", file=sys.stderr)
                     output_file.close()
                     raise

    finally:
        # Asegurarse de cerrar el último archivo abierto
        if output_file and not output_file.closed:
            output_file.close()
            print(f"   [OK] Escrito: {current_file_path}")

    print("--- Proceso de creación de archivos completado. ---")


def create_block_from_files(root_dir, extensions=None, output_file=None):
    """
    Combina archivos de una estructura de directorios en un solo bloque de texto.

    Args:
        root_dir (str): El directorio raíz desde donde empezar a buscar.
        extensions (list, optional): Lista de extensiones de archivo a incluir (ej: ['.py', '.txt']).
                                     Si es None, incluye todos los archivos. Case-insensitive.
        output_file (str, optional): Ruta al archivo donde guardar el bloque generado.
                                     Si es None, imprime a la salida estándar (stdout).
    """
    if extensions:
        # Normalizar extensiones a minúsculas y asegurarse de que empiezan con '.'
        valid_extensions = tuple(ext.lower() if ext.startswith('.') else '.' + ext.lower() for ext in extensions)
    else:
        valid_extensions = None # Incluir todos

    output_lines = []
    root_dir_abs = os.path.abspath(root_dir)

    print(f"--- Combinando archivos desde: {root_dir_abs} ---")
    if valid_extensions:
        print(f"--- Incluyendo extensiones: {', '.join(valid_extensions)} ---")
    else:
         print(f"--- Incluyendo todos los archivos ---")


    # Ordenar los archivos encontrados para una salida consistente
    files_to_process = []
    for dirpath, _, filenames in os.walk(root_dir):
        # Ignorar directorios ocultos comunes (opcional)
        # if os.path.basename(dirpath).startswith('.'):
        #     continue
        for filename in filenames:
            # Ignorar archivos ocultos comunes (opcional)
            # if filename.startswith('.'):
            #     continue

            if valid_extensions is None or filename.lower().endswith(valid_extensions):
                full_path = os.path.join(dirpath, filename)
                files_to_process.append(full_path)

    files_to_process.sort() # Ordenar alfabéticamente por ruta completa

    for full_path in files_to_process:
        try:
            # Obtener la ruta relativa normalizada con '/'
            relative_path = os.path.relpath(full_path, root_dir_abs)
            normalized_relative_path = relative_path.replace(os.sep, '/')

            print(f"   Procesando: {normalized_relative_path}")

            # Añadir el marcador
            output_lines.append(f"{FILE_MARKER_PREFIX}{normalized_relative_path}")

            # Leer y añadir el contenido del archivo
            with open(full_path, 'r', encoding='utf-8') as infile:
                 # Usamos readlines() para preservar los finales de línea existentes
                 file_content_lines = infile.read().splitlines()
                 output_lines.extend(file_content_lines)

            # Añadir una línea en blanco después de cada archivo para separación visual (opcional)
            output_lines.append("")

        except Exception as e:
            print(f"\nADVERTENCIA: No se pudo procesar el archivo '{full_path}': {e}", file=sys.stderr)

    # Unir todas las líneas en un solo bloque
    final_block = "\n".join(output_lines)

    # Escribir a archivo o a stdout
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as outfile:
                outfile.write(final_block)
            print(f"--- Bloque combinado guardado en: {output_file} ---")
        except IOError as e:
            print(f"\nERROR: No se pudo escribir en el archivo de salida '{output_file}': {e}", file=sys.stderr)
            # Imprimir a stdout como fallback si falla la escritura
            print("\n--- Contenido del bloque (salida estándar como fallback) ---\n")
            print(final_block)

    else:
        print("\n--- Contenido del bloque combinado (salida estándar) ---")
        print(final_block)
        print("--- Fin del bloque combinado ---")


def main():
    parser = argparse.ArgumentParser(
        description="Script para crear archivos desde un bloque de código o combinar archivos en un bloque.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Modo de operación")

    # --- Subcomando 'crear' ---
    parser_create = subparsers.add_parser(
        "crear",
        help="Crea archivos y directorios desde un bloque de texto (leído desde archivo o stdin)."
    )
    parser_create.add_argument(
        "-i", "--input",
        metavar="ARCHIVO_ENTRADA",
        type=str,
        default=None,
        help="Archivo de entrada que contiene el bloque de código. Si no se especifica, lee desde stdin."
    )
    parser_create.add_argument(
        "-d", "--directorio-base",
        metavar="RUTA",
        type=str,
        default=".",
        help="Directorio base donde se crearán los archivos/carpetas (por defecto: directorio actual)."
    )

    # --- Subcomando 'combinar' ---
    parser_combine = subparsers.add_parser(
        "combinar",
        help="Combina archivos de una estructura de directorios en un solo bloque de texto."
    )
    parser_combine.add_argument(
        "directorio_raiz",
        metavar="DIRECTORIO_RAIZ",
        type=str,
        help="Directorio raíz desde donde empezar a buscar archivos."
    )
    parser_combine.add_argument(
        "-e", "--extensiones",
        metavar="EXT",
        type=str,
        nargs='*', # 0 o más extensiones
        default=['.py'], # Por defecto, solo archivos Python
        help="Extensiones de archivo a incluir (ej: .py .txt .md). Si no se especifica, incluye solo '.py'. Para incluir todos, usa un argumento vacío como '' o no uses -e y añade un caso especial."
    )
    parser_combine.add_argument(
        "-o", "--output",
        metavar="ARCHIVO_SALIDA",
        type=str,
        default=None,
        help="Archivo donde guardar el bloque combinado. Si no se especifica, imprime a stdout."
    )


    args = parser.parse_args()

    try:
        if args.mode == "crear":
            code_block_content = ""
            if args.input:
                print(f"Leyendo bloque de código desde: {args.input}")
                try:
                    with open(args.input, 'r', encoding='utf-8') as f:
                        code_block_content = f.read()
                except FileNotFoundError:
                     print(f"ERROR: Archivo de entrada no encontrado: {args.input}", file=sys.stderr)
                     sys.exit(1)
                except IOError as e:
                     print(f"ERROR: No se pudo leer el archivo de entrada '{args.input}': {e}", file=sys.stderr)
                     sys.exit(1)

            else:
                print("Leyendo bloque de código desde la entrada estándar (stdin). Presiona Ctrl+D (Linux/macOS) o Ctrl+Z+Enter (Windows) para finalizar.")
                code_block_content = sys.stdin.read()

            if not code_block_content.strip():
                 print("ERROR: El bloque de código de entrada está vacío.", file=sys.stderr)
                 sys.exit(1)

            create_files_from_block(code_block_content, args.directorio_base)

        elif args.mode == "combinar":
             # Manejar el caso de querer todas las extensiones
             extensions_to_use = args.extensiones
             if extensions_to_use == []: # Si el usuario pasó -e sin argumentos, o si queremos un modo "todos"
                 print("Advertencia: No se especificaron extensiones con -e, se incluirán TODOS los archivos.")
                 extensions_to_use = None # Señal para incluir todos
             elif extensions_to_use == ['.py'] and len(sys.argv) <= 3 : # Si solo está el comando y el dir_raiz, usa default .py
                 print("Usando extensión por defecto: .py")
                 # extensions_to_use ya es ['.py']
             elif '' in extensions_to_use: # Si el usuario puso '' explícitamente
                  print("Se detectó extensión vacía (''), se incluirán TODOS los archivos.")
                  extensions_to_use = None


             if not os.path.isdir(args.directorio_raiz):
                 print(f"ERROR: El directorio raíz especificado no existe o no es un directorio: {args.directorio_raiz}", file=sys.stderr)
                 sys.exit(1)

             create_block_from_files(args.directorio_raiz, extensions_to_use, args.output)

    except Exception as e:
         print(f"\nERROR INESPERADO: {e}", file=sys.stderr)
         # Opcional: Imprimir traceback completo para depuración
         # import traceback
         # traceback.print_exc()
         sys.exit(1)

    sys.exit(0) # Salida exitosa


if __name__ == "__main__":
    main()