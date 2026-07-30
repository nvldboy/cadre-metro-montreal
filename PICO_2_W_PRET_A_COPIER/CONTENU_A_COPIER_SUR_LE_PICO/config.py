"""Réglages du cadre lumineux du métro de Montréal."""

# Matériel
DATA_PIN = 0
NUMBER_OF_LEDS = 68
BRIGHTNESS = 0.20
# En mode trains, les stations sans train restent visibles à 15 % de la
# luminosité maximale; le passage d'un train monte progressivement à 100 %.
TRAIN_BASE_LEVEL = 0.15
# Les pixels Amazon sont des WS2811 5 V à 800 kHz.
PIXEL_TIMING = 1

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
API_TIMEOUT_SECONDS = 20
WIFI_TIMEOUT_SECONDS = 20
WIFI_RECONNECT_INTERVAL_SECONDS = 10
RETRY_DELAY_SECONDS = 15

# Mise à jour automatique de l'horaire GTFS compact
# Renseigner l'adresse après la publication du dossier updates sur un dépôt
# public. Laisser l'adresse vide maintient la fonction désactivée sans erreur.
GTFS_AUTO_UPDATE_ENABLED = True
GTFS_UPDATE_MANIFEST_URL = ""
GTFS_UPDATE_STARTUP_DELAY_SECONDS = 90
GTFS_UPDATE_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
GTFS_UPDATE_TIMEOUT_SECONDS = 120

# Animation
# 40 ms = 25 images/s, dans la plage demandée de 20 à 30 Hz.
ANIMATION_FRAME_MS = 40
SLOW_PULSE_PERIOD_MS = 1800
STOP_BLINK_PERIOD_MS = 700
