"""Programme asynchrone du cadre lumineux du métro de Montréal."""

import json
import gc
import time
from machine import Pin, reset

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from async_stm_api import fetch_service_status_async, prepare_stm_endpoint
from config import (
    ANIMATION_FRAME_MS,
    API_STALE_FAILURE_COUNT,
    API_MONITOR_INTERVAL_SECONDS,
    API_TIMEOUT_SECONDS,
    GTFS_AUTO_UPDATE_ENABLED,
    GTFS_UPDATE_CHECK_INTERVAL_SECONDS,
    GTFS_UPDATE_MANIFEST_URL,
    GTFS_UPDATE_STARTUP_DELAY_SECONDS,
    GTFS_UPDATE_TIMEOUT_SECONDS,
    RETRY_DELAY_SECONDS,
    WIFI_RECONNECT_INTERVAL_SECONDS,
)
from gtfs_updater import (
    confirm_schedule,
    recover_schedule,
    rollback_schedule,
)
from led_mapping import load_led_mapping
from led_display import MetroDisplay
from night_mode import anchored_clock_parts, is_night
from stm_status import NORMAL, SLOW, STOPPED, empty_status, parse_service_status
from status_animation import (
    BOOT,
    CLOCK_SYNC,
    CONFIG_ERROR,
    FATAL_ERROR,
    GTFS_ERROR,
    GTFS_UPDATE_ERROR,
    GTFS_UPDATE_SUCCESS,
    GTFS_UPDATING,
    LINE_TEST,
    READY,
    SCHEDULE_LOADING,
    WIFI_CONNECTED,
    WIFI_RECONNECTING,
    WIFI_UNAVAILABLE,
    select_runtime_state,
)
from wifi_manager import (
    connect_any,
    connect_any_async,
    is_connected,
    normalize_networks,
    sync_clock,
)

try:
    from secrets import WIFI_SSID, WIFI_PASSWORD, STM_API_KEY
except ImportError:
    WIFI_SSID = ""
    WIFI_PASSWORD = ""
    STM_API_KEY = ""

try:
    from secrets import WIFI_NETWORKS
except ImportError:
    WIFI_NETWORKS = ()

STATE_NAMES = {
    NORMAL: "ok",
    SLOW: "slow",
    STOPPED: "interrupted",
}

# État partagé entre api_monitor_loop et animate_loop.
system_status = {
    "green": "ok",
    "orange": "ok",
    "yellow": "ok",
    "blue": "ok",
}
service_status = empty_status()
clock_anchor_epoch = 0
clock_anchor_ticks = 0
stm_endpoint = None
runtime_notice_state = None
runtime_notice_started_ms = 0
runtime_notice_duration_ms = 0
api_failure_count = 0
recovery_lines = ()
recovery_started_ms = 0
runtime_animation_anchor_ticks = time.ticks_ms()
fatal_animation_state = FATAL_ERROR
last_render_snapshot = {
    "epoch": 0,
    "trains": 0,
    "active": (),
}


def _load_stations_map():
    with open("stations_map.json", "r") as handle:
        station_map = json.load(handle)
    if len(station_map.get("stations", ())) != 68:
        raise ValueError("stations_map.json doit contenir 68 stations")
    return station_map


def _clock_now():
    elapsed_ms = time.ticks_diff(time.ticks_ms(), clock_anchor_ticks)
    # Ne jamais additionner une fraction au grand timestamp Unix sur le Pico.
    # Son float 32 bits arrondirait alors l'heure par bonds d'environ 128 s.
    return anchored_clock_parts(clock_anchor_epoch, elapsed_ms)


def _configured_networks():
    candidates = list(WIFI_NETWORKS or ())
    candidates.append((WIFI_SSID, WIFI_PASSWORD))
    return normalize_networks(candidates)


def _anchor_clock():
    global clock_anchor_epoch, clock_anchor_ticks
    clock_anchor_epoch = int(time.time())
    clock_anchor_ticks = time.ticks_ms()


def _configured():
    return bool(_configured_networks())


def _set_runtime_notice(state, duration_ms=0):
    global runtime_notice_state, runtime_notice_started_ms
    global runtime_notice_duration_ms
    runtime_notice_state = state
    runtime_notice_started_ms = time.ticks_ms()
    runtime_notice_duration_ms = max(0, int(duration_ms))


def _active_runtime_notice(now_ms):
    global runtime_notice_state
    if (
        runtime_notice_state is not None
        and runtime_notice_duration_ms
        and time.ticks_diff(now_ms, runtime_notice_started_ms)
        >= runtime_notice_duration_ms
    ):
        runtime_notice_state = None
    return runtime_notice_state


def _play_waiting_state(display, state, duration_ms, attempt=0):
    started_ms = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), started_ms) < duration_ms:
        display.show_system_state(
            state,
            started_ms,
            attempt=attempt,
        )
        time.sleep_ms(ANIMATION_FRAME_MS)


def _wifi_progress_renderer(display):
    def render_progress(state, elapsed_ms, attempt):
        display.show_system_state(
            state,
            started_ms=0,
            now_ms=elapsed_ms,
            attempt=attempt,
        )

    return render_progress


async def wifi_monitor_loop(networks, onboard):
    """Rétablit Internet automatiquement sans arrêter l'animation."""
    global stm_endpoint
    while True:
        await asyncio.sleep(WIFI_RECONNECT_INTERVAL_SECONDS)
        if is_connected():
            continue

        onboard.value(0)
        print("Wi-Fi perdu; recherche d'un réseau de secours.")
        _set_runtime_notice(WIFI_RECONNECTING)
        try:
            await connect_any_async(networks)
            if sync_clock():
                _anchor_clock()
            stm_endpoint = None
            _set_runtime_notice(WIFI_CONNECTED, 1200)
            print("Connexion Wi-Fi rétablie.")
        except Exception as error:
            print("Reconnexion Wi-Fi impossible:", error)


def _publish_service_status(parsed):
    global service_status, recovery_lines, recovery_started_ms
    previous = dict(system_status)
    service_status = parsed
    for line_name in system_status:
        system_status[line_name] = STATE_NAMES[
            parsed["lines"].get(line_name, NORMAL)
        ]
    recovered = tuple(
        line_name
        for line_name in system_status
        if previous.get(line_name, "ok") != "ok"
        and system_status[line_name] == "ok"
    )
    if recovered:
        recovery_lines = recovered
        recovery_started_ms = time.ticks_ms()


async def animate_loop(display):
    """Anime les trains à 25 Hz et applique immédiatement les interruptions."""
    global last_render_snapshot, recovery_lines, fatal_animation_state
    # L'horaire compact est volumineux. Il n'est chargé qu'après l'assistant
    # de configuration afin de garder le maximum de mémoire disponible.
    try:
        from train_schedule import (
            feed_is_current,
            positions_now,
            station_levels,
            without_interrupted_lines,
        )
    except Exception:
        if rollback_schedule():
            print("Horaire GTFS restauré; redémarrage.")
            time.sleep(1)
            reset()
        fatal_animation_state = GTFS_ERROR
        raise
    confirm_schedule()

    last_reported_minute = -1
    last_night_mode = None
    last_snapshot_second = -1
    while True:
        epoch_seconds, fractional_ms = _clock_now()
        fractional_second = fractional_ms / 1000
        positions, local_parts = positions_now(
            epoch_seconds,
            fractional_second=fractional_second,
        )

        # Une ligne interrompue disparaît immédiatement de la simulation.
        running_positions = without_interrupted_lines(
            positions,
            system_status,
        )
        levels, line_counts = station_levels(
            running_positions,
            animation_seconds=fractional_second,
        )
        snapshot_second = epoch_seconds
        if snapshot_second != last_snapshot_second:
            last_snapshot_second = snapshot_second
            last_render_snapshot = {
                "epoch": epoch_seconds,
                "millisecond": fractional_ms,
                "trains": sum(line_counts),
                "active": tuple(
                    (
                        logical_index,
                        display.logical_to_physical[logical_index],
                        round(level, 3),
                    )
                    for logical_index, level in enumerate(levels)
                    if level > 0.02
                ),
            }
        now_ms = time.ticks_ms()
        # Utiliser les positions avant le filtrage des interruptions : une
        # panne générale du réseau ne doit pas être confondue avec la fermeture
        # planifiée du métro.
        night_mode = is_night(local_parts, trains_running=bool(positions))
        feed_current = feed_is_current(local_parts)
        notice_state = _active_runtime_notice(now_ms)
        technical_state = select_runtime_state(
            is_connected(),
            feed_current,
            explicit_state=notice_state,
            api_stale=api_failure_count >= API_STALE_FAILURE_COUNT,
        )
        technical_started_ms = (
            runtime_notice_started_ms
            if notice_state is not None
            else runtime_animation_anchor_ticks
        )
        if (
            recovery_lines
            and time.ticks_diff(now_ms, recovery_started_ms) >= 1600
        ):
            recovery_lines = ()
        display.render(
            service_status,
            now_ms,
            levels,
            night_mode=night_mode,
            technical_state=technical_state,
            technical_started_ms=technical_started_ms,
            recovery_lines=recovery_lines,
            recovery_started_ms=recovery_started_ms,
        )

        if night_mode != last_night_mode:
            last_night_mode = night_mode
            print(
                "Mode nuit actif."
                if night_mode
                else "Mode jour actif."
            )

        current_minute = local_parts[4]
        if current_minute != last_reported_minute:
            last_reported_minute = current_minute
            print("Trains théoriques:", sum(line_counts), line_counts)
            if not feed_current:
                print("Attention: l'horaire GTFS doit être mis à jour.")

        await asyncio.sleep_ms(ANIMATION_FRAME_MS)


async def api_monitor_loop(onboard):
    """Surveille l'état du réseau toutes les 60 secondes sans bloquer l'animation."""
    global stm_endpoint, api_failure_count
    while True:
        started_ms = time.ticks_ms()
        next_delay = API_MONITOR_INTERVAL_SECONDS
        if STM_API_KEY and STM_API_KEY != "CLE_API_STM":
            try:
                if not is_connected():
                    raise OSError("Wi-Fi non connecté")
                # La résolution DNS synchrone est faite avant le démarrage de
                # l'animation. Elle n'est reprise ici que si elle avait échoué,
                # afin d'éviter un gel visible toutes les 60 secondes.
                if stm_endpoint is None:
                    stm_endpoint = prepare_stm_endpoint()
                gc.collect()
                payload = await asyncio.wait_for(
                    fetch_service_status_async(STM_API_KEY),
                    API_TIMEOUT_SECONDS,
                )
                if payload is not None:
                    parsed = parse_service_status(payload)
                    _publish_service_status(parsed)
                    # Seul l'état compact publié est encore nécessaire. La
                    # réponse filtrée peut être libérée avant la prochaine
                    # minute pour garder une marge de mémoire confortable.
                    payload = None
                    parsed = None
                    gc.collect()
                onboard.value(1)
                api_failure_count = 0
                elapsed_ms = time.ticks_diff(time.ticks_ms(), started_ms)
                print(
                    "État STM:",
                    system_status,
                    "serveur",
                    stm_endpoint,
                    "en",
                    elapsed_ms // 1000,
                    "s",
                )
                # Conserver un départ de requête approximativement chaque
                # minute même lorsque la grosse réponse prend du temps.
                next_delay = max(
                    1,
                    API_MONITOR_INTERVAL_SECONDS - elapsed_ms // 1000,
                )
            except Exception as error:
                onboard.value(0)
                api_failure_count += 1
                error_name = getattr(
                    getattr(error, "__class__", None),
                    "__name__",
                    "Erreur",
                )
                # Un délai de lecture ou une réponse HTTP invalide ne remet
                # pas en cause l'adresse DNS déjà résolue. Une vraie erreur de
                # transport force toutefois une nouvelle résolution.
                if error_name not in ("TimeoutError", "AsyncStmApiError"):
                    stm_endpoint = None
                detail = str(error)
                print(
                    "Mise à jour STM impossible:",
                    error_name + ((": " + detail) if detail else ""),
                )
                # Le dernier état valide reste affiché.
                next_delay = RETRY_DELAY_SECONDS
        else:
            onboard.value(1)
            print("Alertes STM désactivées: aucune clé API.")

        await asyncio.sleep(next_delay)


async def gtfs_update_loop(display):
    """Vérifie chaque jour si un nouvel horaire compact est publié."""
    from metro_schedule_data import FEED, GENERATED_AT
    from gtfs_updater import check_and_install_update

    await asyncio.sleep(GTFS_UPDATE_STARTUP_DELAY_SECONDS)
    while True:
        if is_connected():
            try:
                _set_runtime_notice(GTFS_UPDATING)
                updated = await asyncio.wait_for(
                    check_and_install_update(
                        GTFS_UPDATE_MANIFEST_URL,
                        FEED,
                        GENERATED_AT,
                    ),
                    GTFS_UPDATE_TIMEOUT_SECONDS,
                )
                if updated:
                    print("Nouvel horaire GTFS installé; redémarrage.")
                    _set_runtime_notice(GTFS_UPDATE_SUCCESS, 1600)
                    await asyncio.sleep_ms(1600)
                    reset()
                _set_runtime_notice(None)
                print("Horaire GTFS automatique vérifié.")
            except Exception as error:
                print("Mise à jour GTFS ignorée:", error)
                _set_runtime_notice(GTFS_UPDATE_ERROR, 5000)
        await asyncio.sleep(GTFS_UPDATE_CHECK_INTERVAL_SECONDS)


async def main_async(display, onboard, networks):
    tasks = [
        animate_loop(display),
        api_monitor_loop(onboard),
        wifi_monitor_loop(networks, onboard),
    ]
    if GTFS_AUTO_UPDATE_ENABLED and GTFS_UPDATE_MANIFEST_URL:
        tasks.append(gtfs_update_loop(display))
    await asyncio.gather(*tasks)


def run():
    global clock_anchor_epoch, clock_anchor_ticks, stm_endpoint

    if recover_schedule():
        print("Horaire GTFS récupéré après une mise à jour interrompue.")

    onboard = Pin("LED", Pin.OUT)
    stations_map = _load_stations_map()
    led_mapping = load_led_mapping(
        station_count=len(stations_map["stations"])
    )
    if led_mapping is None:
        from setup_assistant import run_setup_assistant
        run_setup_assistant(stations_map)
        return

    display = MetroDisplay(stations_map, led_mapping)
    gc.collect()
    display.play_system_animation(
        BOOT,
        2800,
        physical_order=True,
    )
    display.play_system_animation(LINE_TEST, 1200)

    networks = _configured_networks()
    if not networks:
        print("Copier secrets.example.py vers secrets.py et compléter le Wi-Fi.")
        started_ms = time.ticks_ms()
        while True:
            display.show_system_state(CONFIG_ERROR, started_ms)
            onboard.toggle()
            time.sleep_ms(ANIMATION_FRAME_MS)

    wifi_progress = _wifi_progress_renderer(display)
    wifi_attempt = 0
    while True:
        try:
            connect_any(networks, progress_callback=wifi_progress)
            display.play_system_animation(WIFI_CONNECTED, 1200)
            display.show_system_state(CLOCK_SYNC, 0)
            if sync_clock():
                break
        except Exception as error:
            print("Initialisation réseau impossible:", error)
        onboard.toggle()
        _play_waiting_state(
            display,
            WIFI_UNAVAILABLE,
            5000,
            attempt=wifi_attempt,
        )
        wifi_attempt += 1

    _anchor_clock()
    if STM_API_KEY and STM_API_KEY != "CLE_API_STM":
        try:
            stm_endpoint = prepare_stm_endpoint()
        except Exception as error:
            print("Résolution STM reportée:", error)
    display.play_system_animation(SCHEDULE_LOADING, 1200)
    display.play_system_animation(READY, 1300)
    print("Horloge NTP synchronisée; démarrage des tâches.")

    try:
        asyncio.run(main_async(display, onboard, networks))
    except Exception as error:
        print("Erreur fatale du programme:", error)
        started_ms = time.ticks_ms()
        while True:
            display.show_system_state(fatal_animation_state, started_ms)
            onboard.toggle()
            time.sleep_ms(ANIMATION_FRAME_MS)
    else:
        display.clear()


try:
    run()
except Exception as fatal_startup_error:
    print("Erreur fatale au démarrage:", fatal_startup_error)
    emergency_display = MetroDisplay()
    emergency_started_ms = time.ticks_ms()
    while True:
        emergency_display.show_system_state(
            FATAL_ERROR,
            emergency_started_ms,
            physical_order=True,
        )
        time.sleep_ms(ANIMATION_FRAME_MS)
