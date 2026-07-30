"""Rendu des 68 DEL du cadre."""

import math
import time
from machine import Pin
from neopixel import NeoPixel

from config import (
    ANIMATION_FRAME_MS,
    BRIGHTNESS,
    DATA_PIN,
    NIGHT_AMBIENT_ENABLED,
    NIGHT_AMBIENT_MAX_LEVEL,
    NIGHT_AMBIENT_MIN_LEVEL,
    NIGHT_AMBIENT_PERIOD_MS,
    NIGHT_BRIGHTNESS,
    NUMBER_OF_LEDS,
    PIXEL_TIMING,
    SLOW_PULSE_PERIOD_MS,
    STOP_BLINK_PERIOD_MS,
    TRAIN_BASE_LEVEL,
)
from power_safety import write_limited
from stations import (
    LINE_COLORS,
    STATION_INDEX,
    STATION_LINES,
    STATION_ORDER,
)
from stm_status import NORMAL, SLOW, STOPPED

AMBER = (255, 120, 0)
RED = (255, 0, 0)
WHITE = (180, 180, 165)
MAGENTA = (180, 0, 120)
OFF = (0, 0, 0)


def _scaled(color, factor):
    factor = max(0.0, min(1.0, factor))
    return tuple(int(channel * factor) for channel in color)


def _normal_station_color(station_name):
    lines = STATION_LINES[station_name]
    if len(lines) > 1:
        return WHITE
    return LINE_COLORS[lines[0]]


class MetroDisplay:
    def __init__(self, stations_map=None, logical_to_physical=None):
        self.pixels = NeoPixel(
            Pin(DATA_PIN, Pin.OUT),
            NUMBER_OF_LEDS,
            timing=PIXEL_TIMING,
        )
        if logical_to_physical is None:
            logical_to_physical = list(range(NUMBER_OF_LEDS))
        if (
            len(logical_to_physical) != NUMBER_OF_LEDS
            or len(set(logical_to_physical)) != NUMBER_OF_LEDS
            or any(
                type(index) is not int
                or index < 0
                or index >= NUMBER_OF_LEDS
                for index in logical_to_physical
            )
        ):
            raise ValueError("La correspondance physique des DEL est invalide")
        self.logical_to_physical = logical_to_physical
        self.lines_by_led = [[] for _ in range(NUMBER_OF_LEDS)]
        if stations_map:
            for line_name, led_indexes in stations_map["lines"].items():
                for led_index in led_indexes:
                    self.lines_by_led[led_index].append(line_name)
        else:
            for station_name, led_index in STATION_INDEX.items():
                self.lines_by_led[led_index] = STATION_LINES[station_name]
        self.last_frame = -ANIMATION_FRAME_MS
        self.clear()

    def clear(self):
        write_limited(self.pixels, [OFF] * NUMBER_OF_LEDS)

    def show_configuration_error(self):
        color = _scaled(MAGENTA, BRIGHTNESS)
        write_limited(self.pixels, [color] * NUMBER_OF_LEDS)

    def test_sequence(self, delay_ms=80):
        """Allume chaque DEL et affiche son numéro dans la console."""
        self.clear()
        for logical_index, station_name in enumerate(STATION_ORDER):
            physical_index = self.logical_to_physical[logical_index]
            print(
                "physique",
                physical_index,
                "logique",
                logical_index,
                station_name,
            )
            frame = [OFF] * NUMBER_OF_LEDS
            frame[physical_index] = _scaled(WHITE, BRIGHTNESS)
            write_limited(self.pixels, frame)
            time.sleep_ms(delay_ms)
        self.clear()

    def render(
        self,
        status,
        now_ms=None,
        train_levels=None,
        night_mode=False,
    ):
        if now_ms is None:
            now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, self.last_frame) < ANIMATION_FRAME_MS:
            return
        self.last_frame = now_ms

        slow_phase = (
            0.45
            + 0.55 * (
                math.sin(2 * math.pi * (now_ms % SLOW_PULSE_PERIOD_MS)
                         / SLOW_PULSE_PERIOD_MS)
                + 1
            ) / 2
        )
        stopped_on = (now_ms % STOP_BLINK_PERIOD_MS) < (
            STOP_BLINK_PERIOD_MS // 2
        )
        brightness = NIGHT_BRIGHTNESS if night_mode else BRIGHTNESS
        night_ambient_level = 0.0
        if night_mode and NIGHT_AMBIENT_ENABLED:
            phase = (
                2
                * math.pi
                * (now_ms % NIGHT_AMBIENT_PERIOD_MS)
                / NIGHT_AMBIENT_PERIOD_MS
            )
            breath = (math.sin(phase - math.pi / 2) + 1) / 2
            night_ambient_level = (
                NIGHT_AMBIENT_MIN_LEVEL
                + (
                    NIGHT_AMBIENT_MAX_LEVEL
                    - NIGHT_AMBIENT_MIN_LEVEL
                )
                * breath
            )
        frame = [OFF] * NUMBER_OF_LEDS

        for station_name, logical_index in STATION_INDEX.items():
            physical_index = self.logical_to_physical[logical_index]
            severity = status["stations"].get(station_name, NORMAL)
            for line_name in self.lines_by_led[logical_index]:
                severity = max(severity, status["lines"].get(line_name, NORMAL))

            if severity == STOPPED:
                color = RED if stopped_on else OFF
                factor = brightness
            elif severity == SLOW:
                color = AMBER
                factor = brightness * slow_phase
            else:
                color = _normal_station_color(station_name)
                if night_mode:
                    factor = brightness * night_ambient_level
                elif train_levels is None:
                    factor = brightness
                else:
                    train_level = train_levels[logical_index]
                    factor = brightness * (
                        TRAIN_BASE_LEVEL
                        + (1.0 - TRAIN_BASE_LEVEL) * train_level
                    )

            frame[physical_index] = _scaled(color, factor)

        write_limited(self.pixels, frame)
