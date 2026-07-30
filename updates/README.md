# Horaire compact publié

Ce dossier est généré par `scripts/publish_gtfs_update.py`.

- `latest.json` décrit la version, la période, la taille et le SHA-256.
- `metro_schedule_data.py` est le fichier compact téléchargé par le Pico.

Avec un dépôt GitHub public, le manifeste est disponible à une adresse de ce
type :

```text
https://raw.githubusercontent.com/UTILISATEUR/DEPOT/main/updates/latest.json
```

La tâche `.github/workflows/update-gtfs.yml` vérifie le GTFS STM chaque lundi,
exécute les tests et ne publie un commit que si l'horaire a réellement changé.
