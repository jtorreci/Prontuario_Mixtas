# core/materials.py
import math

DEFAULT_ES = 210000.0  # Módulo de Young del acero (MPa) - Usar 200000 o 210000 según norma aplicable

def calculate_ecm_ec2(fck):
    """Calcula el módulo de elasticidad secante del hormigón según EC2 (MPa)."""
    if fck <= 0:
        return 0
    # Fórmula Ecm = 22 * (fcm / 10)^0.3, donde fcm = fck + 8
    fcm = fck + 8
    ecm = 22000 * math.pow(fcm / 10, 0.3)
    return ecm

def get_modular_ratio(fck, Es=DEFAULT_ES):
    """Calcula la relación modular n = Es / Ecm."""
    Ecm = calculate_ecm_ec2(fck)
    if Ecm <= 1e-9: # Evitar división por cero o valores muy pequeños
        # Considerar lanzar un error o devolver infinito/un valor muy grande
        print(f"Advertencia: Ecm calculado es muy bajo ({Ecm:.2f}) para fck={fck}. La relación modular será muy alta.")
        return float('inf')
    return Es / Ecm

