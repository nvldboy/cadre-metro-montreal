"""Client HTTP minimal pour les API ouvertes de la STM."""

try:
    import requests
except ImportError:
    import urequests as requests

from config import SERVICE_STATUS_URL


class StmApiError(Exception):
    pass


def fetch_service_status(api_key):
    if not api_key or api_key == "CLE_API_STM":
        raise StmApiError("La clé API STM n'est pas configurée")

    response = None
    try:
        response = requests.get(
            SERVICE_STATUS_URL,
            headers={
                "apiKey": api_key,
                "Accept": "application/json",
                "User-Agent": "metro-montreal-led-pico/1.0",
            },
        )
        status_code = getattr(response, "status_code", 0)
        if status_code != 200:
            raise StmApiError("Réponse HTTP STM: {}".format(status_code))
        return response.json()
    finally:
        if response is not None:
            response.close()


# Les deux flux ci-dessous sont documentés pour les autobus et répondent en
# protobuf. Ils sont conservés ici pour une extension future, mais ne permettent
# pas d'obtenir la position des trains du métro.
GTFS_TRIP_UPDATES_URL = (
    "https://api.stm.info/pub/od/gtfs-rt/ic/v2/tripUpdates"
)
GTFS_VEHICLE_POSITIONS_URL = (
    "https://api.stm.info/pub/od/gtfs-rt/ic/v2/vehiclePositions"
)
