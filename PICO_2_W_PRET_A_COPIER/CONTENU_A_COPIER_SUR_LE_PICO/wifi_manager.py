"""Connexion Wi-Fi du Pico 2 W."""

import time
import network

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from config import WIFI_TIMEOUT_SECONDS


def normalize_networks(networks):
    """Valide les réseaux configurés et supprime les doublons."""
    normalized = []
    known_ssids = set()
    for candidate in networks or ():
        if not isinstance(candidate, (tuple, list)) or len(candidate) != 2:
            continue
        ssid, password = candidate
        if not isinstance(ssid, str) or not isinstance(password, str):
            continue
        if (
            not ssid
            or ssid == "NOM_DU_WIFI"
            or not password
            or password == "MOT_DE_PASSE_WIFI"
            or ssid in known_ssids
        ):
            continue
        normalized.append((ssid, password))
        known_ssids.add(ssid)
    return normalized


def prioritize_networks(networks, visible_ssids=None):
    """Place les réseaux détectés avant les réseaux temporairement absents."""
    configured = normalize_networks(networks)
    if visible_ssids is None:
        return configured
    visible = set(visible_ssids)
    return (
        [item for item in configured if item[0] in visible]
        + [item for item in configured if item[0] not in visible]
    )


def scan_visible_ssids(wlan=None):
    """Retourne les SSID visibles, ou None si le balayage est impossible."""
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        visible = set()
        for result in wlan.scan():
            raw_ssid = result[0]
            if isinstance(raw_ssid, bytes):
                ssid = raw_ssid.decode("utf-8")
            else:
                ssid = str(raw_ssid)
            if ssid:
                visible.add(ssid)
        return visible
    except Exception as error:
        print("Balayage Wi-Fi impossible:", error)
        return None


def _disconnect(wlan):
    try:
        wlan.disconnect()
    except Exception:
        pass


def connect(ssid, password, wlan=None):
    """Se connecte à un réseau précis."""
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan

    print("Connexion Wi-Fi à", ssid)
    _disconnect(wlan)
    wlan.connect(ssid, password)
    started = time.ticks_ms()

    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), started) > WIFI_TIMEOUT_SECONDS * 1000:
            _disconnect(wlan)
            raise OSError("Délai de connexion Wi-Fi dépassé")
        time.sleep_ms(200)

    print("Wi-Fi connecté:", wlan.ifconfig()[0])
    return wlan


def connect_any(networks):
    """Utilise le premier réseau configuré qui est disponible."""
    configured = normalize_networks(networks)
    if not configured:
        raise OSError("Aucun réseau Wi-Fi configuré")

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan

    visible = scan_visible_ssids(wlan)
    ordered = prioritize_networks(configured, visible)
    last_error = None
    for ssid, password in ordered:
        try:
            return connect(ssid, password, wlan=wlan)
        except Exception as error:
            last_error = error
            print("Réseau Wi-Fi inutilisable:", ssid, error)

    raise OSError(
        "Aucun réseau Wi-Fi configuré n'est accessible: {}".format(
            last_error
        )
    )


async def _sleep_ms(milliseconds):
    sleep_ms = getattr(asyncio, "sleep_ms", None)
    if sleep_ms is not None:
        await sleep_ms(milliseconds)
    else:
        await asyncio.sleep(milliseconds / 1000)


async def _connect_async(wlan, ssid, password):
    wlan.active(True)
    if wlan.isconnected():
        return wlan

    print("Connexion Wi-Fi à", ssid)
    _disconnect(wlan)
    wlan.connect(ssid, password)
    started = time.ticks_ms()

    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), started) > WIFI_TIMEOUT_SECONDS * 1000:
            _disconnect(wlan)
            raise OSError("Délai de connexion Wi-Fi dépassé")
        await _sleep_ms(200)

    print("Wi-Fi connecté:", wlan.ifconfig()[0])
    return wlan


async def connect_any_async(networks):
    """Version asynchrone utilisée pour se reconnecter sans figer les DEL."""
    configured = normalize_networks(networks)
    if not configured:
        raise OSError("Aucun réseau Wi-Fi configuré")

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan

    visible = scan_visible_ssids(wlan)
    ordered = prioritize_networks(configured, visible)
    last_error = None
    for ssid, password in ordered:
        try:
            return await _connect_async(wlan, ssid, password)
        except Exception as error:
            last_error = error
            print("Réseau Wi-Fi inutilisable:", ssid, error)

    raise OSError(
        "Aucun réseau Wi-Fi configuré n'est accessible: {}".format(
            last_error
        )
    )


def is_connected():
    return network.WLAN(network.STA_IF).isconnected()


def sync_clock():
    try:
        import ntptime
        ntptime.settime()
        print("Horloge synchronisée")
        return True
    except Exception as error:
        print("Synchronisation NTP ignorée:", error)
        return False
