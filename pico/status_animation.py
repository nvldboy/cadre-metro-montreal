"""Images légères qui donnent un langage visuel aux états du cadre."""

OFF = (0, 0, 0)
WHITE = (180, 180, 165)
CYAN = (0, 190, 255)
MAGENTA = (200, 0, 140)
AMBER = (255, 120, 0)

BOOT = "boot"
LINE_TEST = "line_test"
WIFI_CONNECTING = "wifi_connecting"
WIFI_RETRY = "wifi_retry"
WIFI_CONNECTED = "wifi_connected"
CLOCK_SYNC = "clock_sync"
SCHEDULE_LOADING = "schedule_loading"
READY = "ready"
CONFIG_ERROR = "config_error"
SETUP_PORTAL = "setup_portal"
WIFI_UNAVAILABLE = "wifi_unavailable"
WIFI_RECONNECTING = "wifi_reconnecting"
GTFS_ERROR = "gtfs_error"
GTFS_EXPIRED = "gtfs_expired"
GTFS_UPDATING = "gtfs_updating"
GTFS_UPDATE_SUCCESS = "gtfs_update_success"
GTFS_UPDATE_ERROR = "gtfs_update_error"
API_STALE = "api_stale"
FATAL_ERROR = "fatal_error"
POWER_LIMITED = "power_limited"

LINE_ORDER = ("green", "orange", "yellow", "blue")


def _blank(count):
    return [OFF] * count


def _scale(color, factor):
    factor = max(0.0, min(1.0, factor))
    return tuple(int(channel * factor + 0.5) for channel in color)


def _put(frame, index, color):
    if 0 <= index < len(frame):
        frame[index] = color


def _anchors(count):
    return (0, count // 2, count - 1)


def _comet(frame, position, color, reverse=False):
    count = len(frame)
    if count <= 0:
        return
    position %= count
    if reverse:
        position = count - 1 - position
    direction = 1 if reverse else -1
    _put(frame, position, color)
    _put(frame, (position + direction) % count, _scale(color, 0.38))
    _put(frame, (position + 2 * direction) % count, _scale(color, 0.14))


def _pulse_on(elapsed_ms, period_ms, windows):
    phase = elapsed_ms % period_ms
    return any(start <= phase < end for start, end in windows)


def _triangle(elapsed_ms, period_ms):
    phase = elapsed_ms % period_ms
    half = max(1, period_ms // 2)
    if phase > half:
        phase = period_ms - phase
    return phase / half


def select_runtime_state(
    wifi_connected,
    feed_current,
    explicit_state=None,
    api_stale=False,
):
    """Choisit l'avertissement technique sans toucher aux alertes STM."""
    if explicit_state is not None:
        return explicit_state
    if not wifi_connected:
        return WIFI_RECONNECTING
    if not feed_current:
        return GTFS_EXPIRED
    if api_stale:
        return API_STALE
    return None


def state_frame(
    state,
    elapsed_ms,
    count=68,
    attempt=0,
    station_colors=None,
    line_groups=None,
    line_colors=None,
):
    """Construit une image logique RGB; l'appelant applique la luminosité."""
    elapsed_ms = max(0, int(elapsed_ms))
    frame = _blank(count)
    if state is None or count <= 0:
        return frame

    if state == BOOT:
        _comet(frame, elapsed_ms // 40, WHITE)

    elif state in (WIFI_CONNECTING, WIFI_RETRY):
        reverse = bool(attempt % 2) or state == WIFI_RETRY
        _comet(frame, elapsed_ms // 75, CYAN, reverse=reverse)

    elif state == WIFI_RECONNECTING:
        phase = elapsed_ms % 10000
        if phase < 1800:
            _comet(frame, phase // 70, CYAN, reverse=bool(attempt % 2))

    elif state == WIFI_CONNECTED:
        if _pulse_on(elapsed_ms, 1200, ((0, 180), (360, 540))):
            frame = [CYAN] * count

    elif state == CLOCK_SYNC:
        position = (elapsed_ms // 120) % count
        spacing = max(1, count // 4)
        for offset in range(0, count, spacing):
            _put(frame, (position + offset) % count, WHITE)

    elif state in (LINE_TEST, SCHEDULE_LOADING):
        step = (elapsed_ms // 300) % len(LINE_ORDER)
        line_name = LINE_ORDER[step]
        if line_groups and line_colors:
            color = line_colors.get(line_name, WHITE)
            for logical_index in line_groups.get(line_name, ()):
                _put(frame, logical_index, color)

    elif state == READY:
        if station_colors:
            visible = min(count, (elapsed_ms * count) // 1100 + 1)
            for index in range(visible):
                _put(frame, index, station_colors[index])

    elif state == CONFIG_ERROR:
        if _pulse_on(
            elapsed_ms,
            2600,
            ((0, 520), (800, 970), (1180, 1350)),
        ):
            for index in _anchors(count):
                _put(frame, index, MAGENTA)

    elif state == SETUP_PORTAL:
        _comet(frame, elapsed_ms // 70, MAGENTA)

    elif state == WIFI_UNAVAILABLE:
        level = 0.10 + 0.28 * _triangle(elapsed_ms, 2600)
        frame = [_scale(CYAN, level)] * count

    elif state == GTFS_ERROR:
        first_half = (elapsed_ms // 550) % 2 == 0
        for index in range(count):
            in_first = index < count // 2
            if in_first == first_half:
                frame[index] = MAGENTA
            else:
                frame[index] = AMBER

    elif state == GTFS_EXPIRED:
        phase = elapsed_ms % 30000
        if phase < 1400:
            position = (phase * count) // 1400
            _comet(frame, position, AMBER)
            _comet(frame, position + count // 2, AMBER)

    elif state == API_STALE:
        phase = elapsed_ms % 30000
        if _pulse_on(phase, 30000, ((0, 170), (340, 510))):
            _put(frame, 0, CYAN)
            _put(frame, count - 1, CYAN)

    elif state == GTFS_UPDATING:
        visible = min(count, (elapsed_ms % 3000) * count // 3000 + 1)
        for index in range(visible):
            frame[index] = _scale(CYAN, 0.22)
        _put(frame, visible - 1, CYAN)

    elif state == GTFS_UPDATE_SUCCESS:
        center = count // 2
        distance = min(center + 1, elapsed_ms * (center + 1) // 1200)
        _put(frame, center - distance, WHITE)
        _put(frame, center + distance, WHITE)

    elif state == GTFS_UPDATE_ERROR:
        if _pulse_on(elapsed_ms, 2400, ((0, 180), (360, 540))):
            for index, color in zip(_anchors(count), (MAGENTA, AMBER, MAGENTA)):
                _put(frame, index, color)

    elif state == POWER_LIMITED:
        if _pulse_on(
            elapsed_ms,
            2400,
            ((0, 150), (300, 450), (600, 750)),
        ):
            for index in _anchors(count):
                _put(frame, index, AMBER)

    elif state == FATAL_ERROR:
        if _pulse_on(elapsed_ms, 1800, ((0, 500), (760, 1260))):
            for index, color in zip(_anchors(count), (MAGENTA, WHITE, MAGENTA)):
                _put(frame, index, color)

    return frame


def recovery_frame(
    elapsed_ms,
    lines,
    count=68,
    line_groups=None,
    line_colors=None,
):
    """Balaye une fois les lignes qui viennent de reprendre leur service."""
    frame = _blank(count)
    if not lines or not line_groups or not line_colors:
        return frame
    progress = max(0.0, min(0.999, elapsed_ms / 1600))
    for line_name in lines:
        indexes = line_groups.get(line_name, ())
        if not indexes:
            continue
        position = int(progress * len(indexes))
        logical_index = indexes[min(position, len(indexes) - 1)]
        _put(frame, logical_index, line_colors.get(line_name, WHITE))
    return frame
