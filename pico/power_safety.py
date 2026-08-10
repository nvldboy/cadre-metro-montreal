"""Limiteur logiciel commun à toutes les écritures vers les DEL."""

from config import (
    LED_CURRENT_LIMIT_MA,
    LED_MAX_CHANNEL_VALUE,
    NUMBER_OF_LEDS,
    PIXEL_CHANNEL_FULL_MA,
    PIXEL_IDLE_CURRENT_MA,
    PIXEL_SWAP_RED_GREEN,
)


def _clamp_channel(value):
    return max(0, min(LED_MAX_CHANNEL_VALUE, int(value)))


def _clamp_color(color):
    if not isinstance(color, (tuple, list)) or len(color) != 3:
        raise ValueError("Une couleur doit contenir trois canaux RGB")
    return tuple(_clamp_channel(channel) for channel in color)


def color_for_pixel_driver(color):
    """Convertit une couleur RGB logique pour l'ordre réel de la guirlande."""
    if PIXEL_SWAP_RED_GREEN:
        red, green, blue = color
        return (green, red, blue)
    return color


def estimate_frame_current_ma(colors):
    """Estimation conservatrice du courant de la chaîne pour une image."""
    channel_total = sum(sum(color) for color in colors)
    active_current = (
        channel_total * PIXEL_CHANNEL_FULL_MA / 255.0
    )
    return len(colors) * PIXEL_IDLE_CURRENT_MA + active_current


def limit_frame(colors):
    """Valide et réduit une image afin de respecter les deux plafonds."""
    if not isinstance(colors, (tuple, list)):
        raise ValueError("L'image des DEL doit être une liste")
    if len(colors) != NUMBER_OF_LEDS:
        raise ValueError(
            "L'image doit contenir exactement {} DEL".format(
                NUMBER_OF_LEDS
            )
        )

    limited = [_clamp_color(color) for color in colors]
    idle_current = len(limited) * PIXEL_IDLE_CURRENT_MA
    active_current = estimate_frame_current_ma(limited) - idle_current
    available_active = max(0, LED_CURRENT_LIMIT_MA - idle_current)

    if active_current <= available_active or active_current <= 0:
        return limited

    factor = available_active / active_current
    return [
        tuple(int(channel * factor) for channel in color)
        for color in limited
    ]


def write_limited(pixels, colors):
    """Seul point d'écriture normal vers le tampon NeoPixel."""
    limited = limit_frame(colors)
    for index, color in enumerate(limited):
        pixels[index] = color_for_pixel_driver(color)
    pixels.write()
    return estimate_frame_current_ma(limited)
