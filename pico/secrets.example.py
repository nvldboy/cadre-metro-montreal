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

# Facultatif : Transit v4 peut compléter les alertes STM.
TRANSIT_API_KEY = ""
# Facultatif : laisser vide pour que le simulateur découvre le réseau STM.
TRANSIT_NETWORK_IDS = ""
