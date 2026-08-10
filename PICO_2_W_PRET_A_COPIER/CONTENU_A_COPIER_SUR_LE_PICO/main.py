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
from night_mode import is_night
from stm_status import NORMAL, SLOW, STOPPED, empty_status, parse_service_status
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


def _load_stations_map():
    with open("stations_map.json", "r") as handle:
        station_map = json.load(handle)
    if len(station_map.get("stations", ())) != 68:
        raise ValueError("stations_map.json doit contenir 68 stations")
    return station_map


def _clock_now():
    elapsed_ms = time.ticks_diff(time.ticks_ms(), clock_anchor_ticks)
    return clock_anchor_epoch + elapsed_ms / 1000


def _configured_networks():
    candidates = list(WIFI_NETWORKS or ())
    candidates.append((WIFI_SSID, WIFI_PASSWORD))
    return normalize_networks(candidates)


def _anchor_clock():
    global clock_anchor_epoch, clock_anchor_ticks
    clock_anchor_epoch = time.time()
    clock_anchor_ticks = time.ticks_ms()


def _configured():
    return bool(_configured_networks())


async def wifi_monitor_loop(networks, onboard):
    """Rétablit Internet automatiquement sans arrêter l'animation."""
    global stm_endpoint
    while True:
        await asyncio.sleep(WIFI_RECONNECT_INTERVAL_SECONDS)
        if is_connected():
            continue

        onboard.value(0)
        print("Wi-Fi perdu; recherche d'un réseau de secours.")
        try:
            await connect_any_async(networks)
            if sync_clock():
                _anchor_clock()
            stm_endpoint = None
            print("Connexion Wi-Fi rétablie.")
        except Exception as error:
            print("Reconnexion Wi-Fi impossible:", error)


def _publish_service_status(parsed):
    global service_status
    service_status = parsed
    for line_name in system_status:
        system_status[line_name] = STATE_NAMES[
            parsed["lines"].get(line_name, NORMAL)
        ]


async def animate_loop(display):
    """Anime les trains à 25 Hz et applique immédiatement les interruptions."""
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
        raise
    confirm_schedule()

    last_reported_minute = -1
    last_night_mode = None
    while True:
        epoch = _clock_now()
        positions, local_parts = positions_now(epoch)

        # Une ligne interrompue disparaît immédiatement de la simulation.
        running_positions = without_interrupted_lines(
            positions,
            system_status,
        )
        levels, line_counts = station_levels(
            running_positions,
            animation_seconds=epoch,
        )
        now_ms = time.ticks_ms()
        # Utiliser les positions avant le filtrage des interruptions : une
        # panne générale du réseau ne doit pas être confondue avec la fermeture
        # planifiée du métro.
        night_mode = is_night(local_parts, trains_running=bool(positions))
        display.render(
            service_status,
            now_ms,
            levels,
            night_mode=night_mode,
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
            if not feed_is_current(local_parts):
                print("Attention: l'horaire GTFS doit être mis à jour.")

        await asyncio.sleep_ms(ANIMATION_FRAME_MS)


async def api_monitor_loop(onboard):
    """Surveille l'état du réseau toutes les 60 secondes sans bloquer l'animation."""
    global stm_endpoint
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


async def gtfs_update_loop():
    """Vérifie chaque jour si un nouvel horaire compact est publié."""
    from metro_schedule_data import FEED, GENERATED_AT
    from gtfs_updater import check_and_install_update

    await asyncio.sleep(GTFS_UPDATE_STARTUP_DELAY_SECONDS)
    while True:
        if is_connected():
            try:
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
                    await asyncio.sleep(1)
                    reset()
                print("Horaire GTFS automatique vérifié.")
            except Exception as error:
                print("Mise à jour GTFS ignorée:", error)
        await asyncio.sleep(GTFS_UPDATE_CHECK_INTERVAL_SECONDS)


async def main_async(display, onboard, networks):
    tasks = [
        animate_loop(display),
        api_monitor_loop(onboard),
        wifi_monitor_loop(networks, onboard),
    ]
    if GTFS_AUTO_UPDATE_ENABLED and GTFS_UPDATE_MANIFEST_URL:
        tasks.append(gtfs_update_loop())
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
    display.test_sequence()

    networks = _configured_networks()
    if not networks:
        print("Copier secrets.example.py vers secrets.py et compléter le Wi-Fi.")
        display.show_configuration_error()
        while True:
            onboard.toggle()
            time.sleep_ms(500)

    while True:
        try:
            connect_any(networks)
            if sync_clock():
                break
        except Exception as error:
            print("Initialisation réseau impossible:", error)
        onboard.toggle()
        time.sleep(5)

    _anchor_clock()
    if STM_API_KEY and STM_API_KEY != "CLE_API_STM":
        try:
            stm_endpoint = prepare_stm_endpoint()
        except Exception as error:
            print("Résolution STM reportée:", error)
    print("Horloge NTP synchronisée; démarrage des tâches.")

    try:
        asyncio.run(main_async(display, onboard, networks))
    finally:
        display.clear()


run()
