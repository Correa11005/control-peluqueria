def aplicar_logica_melany(empleado_id, segundos_reales):
    """
    Aplica la lógica especial solo a Melany.
    No altera el tiempo real, solo devuelve el tiempo mostrado.
    """
    segundos_reales = max(0, int(segundos_reales))

    # Ajusta este ID si Melany no es 3 en tu base de datos
    if empleado_id != 3:
        return segundos_reales

    if segundos_reales < 4 * 3600:
        return segundos_reales

    return 3 * 3600 + ((segundos_reales - 4 * 3600) % 3600)