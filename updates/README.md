# Horaire compact publié

Ce dossier est généré par `scripts/publish_gtfs_update.py`.

- `latest.json` décrit la version, la période, la taille et le SHA-256.
- `metro_schedule_data.py` est le fichier compact téléchargé par le Pico.

Le manifeste réellement utilisé par le Pico est publié dans le dépôt public de
données :

```text
https://raw.githubusercontent.com/nvldboy/cadre-metro-montreal-updates/main/updates/latest.json
```

Le dépôt principal peut ainsi rester privé et aucun secret n'est exposé.

La tâche `.github/workflows/update-gtfs.yml` vérifie le GTFS STM chaque lundi,
exécute les tests et ne publie un commit que si l'horaire a réellement changé.
