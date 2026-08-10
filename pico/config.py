"""Réglages du cadre lumineux du métro de Montréal."""

# Matériel
DATA_PIN = 0
NUMBER_OF_LEDS = 68
BRIGHTNESS = 0.20
# En mode trains, une station qui n'est influencée par aucun train est éteinte.
# Les interruptions et le mode nuit conservent leurs comportements propres.
TRAIN_BASE_LEVEL = 0.0
# Les heures GTFS statiques sont souvent arrondies à la minute. Une variation
# déterministe de quelques secondes par voyage évite que tous les trains ayant
# le même patron changent de station exactement au même instant.
TRAIN_TIMING_VARIATION_SECONDS = 28
# Affichage lisible inspiré de Metroboard : chaque train est un seul point
# lumineux à pleine intensité qui saute à la station suivante à mi-trajet.
# Les pixels Amazon sont des WS2811 5 V à 800 kHz.
PIXEL_TIMING = 1
# Cette guirlande attend les octets dans l'ordre RGB alors que le pilote
# MicroPython NeoPixel du Pico les transmet normalement dans l'ordre GRB.
# L'inversion logicielle compense cette différence matérielle.
PIXEL_SWAP_RED_GREEN = True

# Protection logicielle de l'alimentation et des pixels
# Le limiteur suppose au plus 20 mA par canal R, G ou B à pleine intensité,
# ajoute 2 mA de repos par pixel et garde la chaîne sous environ 1 A.
LED_CURRENT_LIMIT_MA = 1000
PIXEL_CHANNEL_FULL_MA = 20
PIXEL_IDLE_CURRENT_MA = 2
# Même si une animation contient par erreur (255, 255, 255), aucun canal ne
# dépassera 25 % avant l'application du budget global de courant.
LED_MAX_CHANNEL_VALUE = 64

# Fenêtre du mode nuit automatique. Dans cette fenêtre, le mode nuit ne
# s'active qu'après le dernier voyage GTFS et se termine dès le premier train.
NIGHT_MODE_ENABLED = True
NIGHT_START_HOUR = 23
NIGHT_END_HOUR = 6
NIGHT_BRIGHTNESS = 0.03
# Respiration très lente de toute la carte, entre 0,6 % et 3 % de luminosité
# réelle avec les valeurs ci-dessous.
NIGHT_AMBIENT_ENABLED = True
NIGHT_AMBIENT_PERIOD_MS = 18000
NIGHT_AMBIENT_MIN_LEVEL = 0.20
NIGHT_AMBIENT_MAX_LEVEL = 1.00

# Assistant de première configuration
SETUP_AP_SSID = "Metro-Setup"
SETUP_AP_PASSWORD = "metro-led-68"
SETUP_AP_IP = "192.168.4.1"
SETUP_BLINK_PERIOD_MS = 700

# Réseau STM
SERVICE_STATUS_URL = (
    "https://api.stm.info/pub/od/i3/v2/messages/etatservice"
)

# Une requête par minute = 1 440 requêtes/jour, sous le quota STM de 10 000.
POLL_INTERVAL_SECONDS = 60
API_MONITOR_INTERVAL_SECONDS = 60
# L'API i3 mélange parfois plus de 800 alertes d'autobus et de métro dans une
# réponse de plus de 500 ko. Le Pico doit atteindre les alertes métro placées à
# la fin sans abandonner prématurément la lecture HTTPS.
API_TIMEOUT_SECONDS = 90
WIFI_TIMEOUT_SECONDS = 20
WIFI_RECONNECT_INTERVAL_SECONDS = 10
# Après un échec, réessayer rapidement plutôt que d'attendre le prochain cycle
# normal d'une minute.
RETRY_DELAY_SECONDS = 15

# Mise à jour automatique de l'horaire GTFS compact
# Renseigner l'adresse après la publication du dossier updates sur un dépôt
# public. Laisser l'adresse vide maintient la fonction désactivée sans erreur.
GTFS_AUTO_UPDATE_ENABLED = True
GTFS_UPDATE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/nvldboy/"
    "cadre-metro-montreal-updates/main/updates/latest.json"
)
GTFS_UPDATE_STARTUP_DELAY_SECONDS = 90
GTFS_UPDATE_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
GTFS_UPDATE_TIMEOUT_SECONDS = 120

# Animation
# 40 ms = 25 images/s, dans la plage demandée de 20 à 30 Hz.
ANIMATION_FRAME_MS = 40
SLOW_PULSE_PERIOD_MS = 1800
STOP_BLINK_PERIOD_MS = 700
