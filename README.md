<p align="center">
  <img
    src="docs/images/inspiration-salon.jpg"
    alt="Concept d’un cadre lumineux de métro dans un salon montréalais"
    width="100%"
  >
</p>

<h1 align="center">Cadre lumineux du métro de Montréal</h1>

<p align="center">
  Un cadre mural 18 × 24 po qui anime les passages théoriques du métro et
  signale les perturbations du réseau avec 68 DEL et un Raspberry Pi Pico 2 W.
</p>

<p align="center">
  <strong>Français</strong> ·
  <a href="docs/README_EN.md">English</a> ·
  <a href="docs/README_ES.md">Español</a> ·
  <a href="docs/README_IT.md">Italiano</a>
</p>

<p align="center">
  <img alt="Raspberry Pi Pico 2 W" src="https://img.shields.io/badge/Pico-2%20W-c51a4a">
  <img alt="MicroPython" src="https://img.shields.io/badge/MicroPython-1.28-2b2728">
  <img alt="Assistant en quatre langues" src="https://img.shields.io/badge/assistant-FR%20%7C%20EN%20%7C%20ES%20%7C%20IT-00a650">
  <img alt="Tests" src="https://img.shields.io/badge/tests-49%20r%C3%A9ussis-167c3a">
</p>

> Les positions affichées sont des estimations calculées à partir des horaires
> GTFS. La STM ne publie pas la position réelle de ses trains de métro. Les
> interruptions et perturbations proviennent toutefois de son API d’état du
> service.

## Une seule version, quatre langues

L’assistant de première configuration est intégré dans une seule page légère.
Il :

- détecte automatiquement la langue du téléphone ou de l’ordinateur;
- propose le français, l’anglais, l’espagnol et l’italien;
- permet de changer de langue à tout moment;
- mémorise le choix dans le navigateur;
- conserve les noms officiels des stations;
- n’ajoute aucune tâche permanente pendant le fonctionnement normal.

La page complète pèse environ **26 ko** et n’est chargée que lorsqu’un nouveau
cadre doit associer ses DEL aux stations.

## Ce que le cadre fait

| Fonction | Résultat |
|---|---|
| Trains théoriques | Interpolation fluide entre les stations selon les horaires GTFS |
| État du réseau | Ralentissements et interruptions lus toutes les 60 secondes |
| Mode nuit | Respiration lente et douce après le dernier passage prévu |
| Première installation | Assistant Web qui identifie chaque DEL sans imposer l’ordre du câblage |
| Protection | Luminosité et courant estimé plafonnés par logiciel |
| Mise à jour GTFS | Téléchargement validé par SHA-256 avec sauvegarde et restauration |
| Simulation | Même animation visible localement dans un navigateur avant le branchement |

## Démarrage rapide

### 1. Préparer le Pico

Installe [MicroPython pour le Pico 2 W](https://micropython.org/download/RPI_PICO2_W/),
puis ouvre Thonny avec l’interpréteur **MicroPython (Raspberry Pi Pico)**.

### 2. Configurer les accès locaux

Dans [`pico/`](pico), duplique `secrets.example.py` sous le nom `secrets.py`,
puis inscris :

```python
WIFI_NETWORKS = [
    ("NOM_DU_WIFI", "MOT_DE_PASSE"),
]

STM_API_KEY = "CLE_API_STM"
```

`secrets.py` est ignoré par Git : il ne sera jamais publié par erreur.

### 3. Copier le programme

Copie le contenu du dossier [`pico/`](pico) à la racine `/` du Pico avec
Thonny. Une copie organisée se trouve aussi dans
[`PICO_2_W_PRET_A_COPIER/`](PICO_2_W_PRET_A_COPIER).

### 4. Associer les DEL

Au premier démarrage :

1. connecte ton téléphone au réseau `Metro-Setup`;
2. utilise le mot de passe `metro-led-68`;
3. ouvre `http://192.168.4.1`;
4. choisis ta langue;
5. indique la station placée devant chaque DEL qui clignote;
6. enregistre : le Pico redémarre automatiquement.

L’ordre physique des DEL n’a donc pas besoin de suivre l’ordre géographique des
stations.

### 5. Tester sans matériel

```bash
python3 simulator/server.py
```

Ouvre ensuite :

- simulateur : `http://127.0.0.1:8765/`;
- assistant initial : `http://127.0.0.1:8765/setup-preview`;
- aperçu espagnol direct : `http://127.0.0.1:8765/setup-preview?lang=es`.

## Signification des animations

| Animation | Signification |
|---|---|
| Couleur de ligne qui se déplace | Passage théorique d’un train |
| Deux stations voisines partiellement allumées | Train estimé entre les stations |
| Blanc | Correspondance entre plusieurs lignes |
| Pulsation ambre | Service ralenti ou perturbé |
| Clignotement rouge | Ligne interrompue ou station fermée |
| Respiration lente et très faible | Mode nuit |
| Magenta fixe au démarrage | Configuration Wi-Fi absente |

## Matériel et sécurité

Le projet cible 68 pixels WS2811 de 12 mm alimentés en **5 V** et un Pico 2 W.
Les DEL et le Pico peuvent partager une même batterie USB, mais les DEL doivent
recevoir leur propre branche 5 V correctement dimensionnée.

- Ne fais jamais passer le courant des DEL dans la broche `3V3` du Pico.
- Relie obligatoirement la masse du Pico à celle des DEL.
- Coupe l’alimentation avant de modifier un fil.
- Commence avec la luminosité limitée fournie par le logiciel.
- Vérifie le sens `DATA IN → DATA OUT` de chaque guirlande.

Le [guide technique complet](docs/GUIDE_FR.md) contient le schéma de câblage,
l’installation détaillée, les diagnostics et les limites électriques.

## Inspiration

<table>
  <tr>
    <td width="50%">
      <img
        src="docs/images/inspiration-salon.jpg"
        alt="Concept du cadre lumineux installé dans un salon"
      >
    </td>
    <td width="50%">
      <img
        src="docs/images/inspiration-atelier.jpg"
        alt="Concept du cadre lumineux en cours de construction dans un atelier"
      >
    </td>
  </tr>
  <tr>
    <td align="center">Intégration murale chaleureuse</td>
    <td align="center">Construction accessible en atelier</td>
  </tr>
</table>

Ces images sont des **visualisations conceptuelles originales**. Elles servent
d’inspiration et ne représentent pas exactement le tracé final, les proportions
des composants ni une œuvre commerciale existante.

## Organisation du projet

| Dossier | Contenu |
|---|---|
| [`pico/`](pico) | Programme MicroPython installé sur le Pico |
| [`simulator/`](simulator) | Simulation Web locale et aperçu de l’assistant |
| [`tests/`](tests) | Tests automatisés du logiciel |
| [`scripts/`](scripts) | Conversion et publication du GTFS |
| [`updates/`](updates) | Horaire compact et manifeste destinés au Pico |
| [`PICO_2_W_PRET_A_COPIER/`](PICO_2_W_PRET_A_COPIER) | Livrable simplifié pour Thonny |
| [`docs/`](docs) | Guides traduits et documentation détaillée |

## Documentation

- [Guide technique détaillé en français](docs/GUIDE_FR.md)
- [English quick start](docs/README_EN.md)
- [Guía rápida en español](docs/README_ES.md)
- [Guida rapida in italiano](docs/README_IT.md)

## Données et confidentialité

Les horaires planifiés proviennent de la Société de transport de Montréal et
sont distribués sous licence CC BY 4.0. Les secrets Wi-Fi et API demeurent
uniquement dans le fichier local `secrets.py`.

Le dépôt peut rester privé et être partagé avec des collaborateurs GitHub.
Avant de le rendre public, il faudra choisir une licence logicielle adaptée.
