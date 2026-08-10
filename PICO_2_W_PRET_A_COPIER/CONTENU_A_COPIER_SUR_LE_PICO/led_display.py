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
    STATUS_BRIGHTNESS,
    STOP_LINE_PATTERN_PERIOD_MS,
    STOP_STATION_PATTERN_PERIOD_MS,
    TRAIN_BASE_LEVEL,
)
from power_safety import frame_requires_limiting, write_limited
from stations import (
    LINE_COLORS,
    STATION_INDEX,
    STATION_LINES,
    STATION_ORDER,
)
from stm_status import NORMAL, SLOW, STOPPED
from status_animation import (
    CONFIG_ERROR,
    POWER_LIMITED,
    recovery_frame,
    state_frame,
)

AMBER = (255, 120, 0)
RED = (255, 0, 0)
WHITE = (180, 180, 165)
MAGENTA = (180, 0, 120)
OFF = (0, 0, 0)


def _scaled(color, factor):
    factor = max(0.0, min(1.0, factor))
    # L'arrondi conserve mieux les rapports de couleur aux faibles niveaux
    # que la troncature, notamment le canal vert de la ligne orange.
    return tuple(int(channel * factor + 0.5) for channel in color)


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
            self.line_groups = stations_map["lines"]
            for line_name, led_indexes in stations_map["lines"].items():
                for led_index in led_indexes:
                    self.lines_by_led[led_index].append(line_name)
        else:
            self.line_groups = {
                line_name: []
                for line_name in LINE_COLORS
            }
            for station_name, led_index in STATION_INDEX.items():
                self.lines_by_led[led_index] = STATION_LINES[station_name]
                for line_name in STATION_LINES[station_name]:
                    self.line_groups[line_name].append(led_index)
        self.station_colors = [
            _normal_station_color(station_name)
            for station_name in STATION_ORDER
        ]
        self.last_frame = -ANIMATION_FRAME_MS
        self.clear()

    def clear(self):
        write_limited(self.pixels, [OFF] * NUMBER_OF_LEDS)

    def show_configuration_error(self):
        self.show_system_state(CONFIG_ERROR)

    def _physical_frame(self, logical_frame, physical_order=False):
        if physical_order:
            return logical_frame
        physical = [OFF] * NUMBER_OF_LEDS
        for logical_index, color in enumerate(logical_frame):
            physical[self.logical_to_physical[logical_index]] = color
        return physical

    def show_system_state(
        self,
        state,
        started_ms=0,
        now_ms=None,
        attempt=0,
        physical_order=False,
    ):
        """Affiche une image d'état sans contourner la sécurité électrique."""
        if now_ms is None:
            now_ms = time.ticks_ms()
        elapsed_ms = max(0, time.ticks_diff(now_ms, started_ms))
        logical = state_frame(
            state,
            elapsed_ms,
            NUMBER_OF_LEDS,
            attempt=attempt,
            station_colors=self.station_colors,
            line_groups=self.line_groups,
            line_colors=LINE_COLORS,
        )
        scaled = [_scaled(color, STATUS_BRIGHTNESS) for color in logical]
        write_limited(
            self.pixels,
            self._physical_frame(scaled, physical_order=physical_order),
        )

    def play_system_animation(
        self,
        state,
        duration_ms,
        attempt=0,
        physical_order=False,
    ):
        """Joue une courte séquence bloquante avant le moteur asynchrone."""
        started_ms = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), started_ms) < duration_ms:
            self.show_system_state(
                state,
                started_ms,
                attempt=attempt,
                physical_order=physical_order,
            )
            time.sleep_ms(ANIMATION_FRAME_MS)
        self.clear()

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
        technical_state=None,
        technical_started_ms=0,
        recovery_lines=(),
        recovery_started_ms=0,
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
        line_stop_phase = now_ms % STOP_LINE_PATTERN_PERIOD_MS
        line_stopped_on = (
            line_stop_phase < 180
            or 360 <= line_stop_phase < 540
        )
        station_stop_phase = now_ms % STOP_STATION_PATTERN_PERIOD_MS
        station_stopped_on = (
            station_stop_phase < 140
            or 280 <= station_stop_phase < 420
            or 560 <= station_stop_phase < 700
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
        severities = [NORMAL] * NUMBER_OF_LEDS

        for station_name, logical_index in STATION_INDEX.items():
            physical_index = self.logical_to_physical[logical_index]
            station_severity = status["stations"].get(station_name, NORMAL)
            line_severity = NORMAL
            for line_name in self.lines_by_led[logical_index]:
                line_severity = max(
                    line_severity,
                    status["lines"].get(line_name, NORMAL),
                )
            severity = max(station_severity, line_severity)
            severities[logical_index] = severity

            if severity == STOPPED:
                stopped_on = (
                    line_stopped_on
                    if line_severity == STOPPED
                    else station_stopped_on
                )
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

        if not night_mode and technical_state is not None:
            technical = state_frame(
                technical_state,
                max(0, time.ticks_diff(now_ms, technical_started_ms)),
                NUMBER_OF_LEDS,
                station_colors=self.station_colors,
                line_groups=self.line_groups,
                line_colors=LINE_COLORS,
            )
            for logical_index, color in enumerate(technical):
                if color != OFF and severities[logical_index] == NORMAL:
                    physical_index = self.logical_to_physical[logical_index]
                    frame[physical_index] = _scaled(color, STATUS_BRIGHTNESS)

        if not night_mode and recovery_lines:
            recovery = recovery_frame(
                max(0, time.ticks_diff(now_ms, recovery_started_ms)),
                recovery_lines,
                NUMBER_OF_LEDS,
                self.line_groups,
                LINE_COLORS,
            )
            for logical_index, color in enumerate(recovery):
                if color != OFF and severities[logical_index] == NORMAL:
                    physical_index = self.logical_to_physical[logical_index]
                    frame[physical_index] = _scaled(color, BRIGHTNESS)

        if not night_mode and frame_requires_limiting(frame):
            warning = state_frame(
                POWER_LIMITED,
                now_ms,
                NUMBER_OF_LEDS,
            )
            for logical_index, color in enumerate(warning):
                if color != OFF and severities[logical_index] == NORMAL:
                    physical_index = self.logical_to_physical[logical_index]
                    frame[physical_index] = _scaled(color, STATUS_BRIGHTNESS)

        write_limited(self.pixels, frame)
