"""Copier ce fichier sous le nom secrets.py et remplacer les valeurs."""

WIFI_SSID = "NOM_DU_WIFI"
WIFI_PASSWORD = "MOT_DE_PASSE_WIFI"

# Le premier réseau disponible est utilisé. Décommenter et compléter la
# deuxième ligne pour ajouter un réseau de secours.
WIFI_NETWORKS = [
    (WIFI_SSID, WIFI_PASSWORD),
    # ("NOM_DU_DEUXIEME_WIFI", "MOT_DE_PASSE_DEUXIEME_WIFI"),
]

STM_API_KEY = "CLE_API_STM"

# Panneau Web local: http://ADRESSE_IP_DU_PICO/admin
# Choisir de 4 à 32 caractères. La valeur par défaut est "metro68" si cette
# ligne est absente, mais il est préférable de la personnaliser.
CONTROL_PANEL_PIN = "CHOISIR_UN_NIP"

# Facultatif : Transit v4 peut compléter les alertes STM.
TRANSIT_API_KEY = ""
# Facultatif : laisser vide pour que le simulateur découvre le réseau STM.
TRANSIT_NETWORK_IDS = ""
