# Cadre lumineux du métro de Montréal

> [Retour à l’accueil du projet](../README.md) · Guide technique détaillé en français

Guide complet pour la première mise en marche d’un cadre de 18 × 24 pouces
utilisant :

- un Raspberry Pi Pico 2 W;
- 68 pixels RGB adressables WS2811 de 12 mm, 5 V et 800 kHz;
- les horaires GTFS planifiés de la STM;
- l’API STM i3 v2 pour les interruptions et l’état réel du réseau.

> **Important :** les positions affichées sont des estimations calculées à
> partir des horaires. La STM ne publie pas la position réelle de ses trains de
> métro. Les alertes et interruptions proviennent toutefois de l’API STM.

## Ce que le cadre affiche

| Apparence | Signification |
|---|---|
| Station éteinte | Aucun train théorique à proximité |
| Une station vivement colorée | Présence estimée d’un train |
| Point qui saute à la station suivante | Déplacement estimé d’un train, représenté par une seule DEL nette |
| Changements répartis sur le réseau | Chaque rame suit son propre horaire légèrement désynchronisé |
| Blanc | Station de correspondance desservie par plusieurs lignes |
| Pulsation ambre | Service ralenti ou perturbé |
| Deux éclats rouges | Ligne interrompue |
| Trois éclats rouges sur une DEL | Station fermée |
| Magenta long–court–court | Configuration absente ou invalide |
| Point blanc parcourant la chaîne | Mise sous tension et autotest |
| Chenillard cyan | Connexion ou reconnexion Wi‑Fi |
| Une DEL blanche clignote et le Wi‑Fi `Metro-Setup` apparaît | Assistant de première configuration |
| Respiration à environ 0,1–0,45 % après le dernier train | Mode nuit automatique |

Lorsqu’une ligne est interrompue, ses trains théoriques sont immédiatement
retirés de l’animation. Ses stations clignotent en rouge pendant que les autres
lignes continuent normalement.

## Avant de commencer

### Matériel recommandé

- Raspberry Pi Pico 2 W;
- 68 pixels WS2811 5 V de 12 mm;
- une seule batterie USB 5 V;
- si nécessaire, un répartiteur 5 V pour créer les deux branches;
- résistance de 330 à 470 Ω pour la ligne DATA;
- condensateur électrolytique d’environ 1 000 µF, 6,3 V ou plus;
- fils suffisamment gros pour transporter le courant 5 V;
- connecteurs et gaine thermorétractable;
- idéalement, convertisseur logique `74AHCT125` ou équivalent 3,3 V vers 5 V;
- multimètre;
- ruban-cache et marqueur pour numéroter les pixels.

### Puissance nécessaire

Un pixel RGB peut théoriquement consommer jusqu’à environ 60 mA en blanc à
pleine puissance :

```text
68 × 0,060 A = 4,08 A
```

Le programme limite normalement la luminosité à 20 %. Un deuxième limiteur
indépendant plafonne chaque canal à 25 % et maintient le courant estimé de
l’ensemble des DEL sous environ 1 A, même si une animation demande
accidentellement du blanc à pleine puissance.

L’installation doit tout de même conserver une marge de sécurité. Une source
5 V pouvant fournir au moins 3 A est recommandée; 5 V / 5 A donne davantage
de marge et ne force pas les DEL à consommer 5 A.

Ne jamais alimenter les 68 DEL à partir de la broche 3V3 du Pico.

Le limiteur logiciel ne protège pas contre un court-circuit, une inversion de
polarité ou l’application d’une tension incorrecte. Des fils adéquats et un
câblage vérifié avant la mise sous tension restent nécessaires. Avec une
batterie USB commerciale qui possède ses propres protections contre les
surintensités et les courts-circuits, un fusible ajouté en ligne est une
protection supplémentaire facultative, pas une condition de fonctionnement.

## Branchement électrique

Effectuer ou modifier le câblage uniquement lorsque toutes les sources
d’alimentation sont débranchées.

### Connexions de base

Une seule batterie alimente tout le cadre, au moyen de deux branches :

```text
                         BATTERIE 5 V
                              │
                  ┌────────────┴────────────┐
                  │                         │
           USB vers le Pico             +5 V des DEL

Pico GP0 ── résistance 330–470 Ω ── DATA IN du pixel 0
Pico GND ────────────────────────── GND des DEL
```

La deuxième branche peut provenir d’une deuxième sortie simultanée de la
batterie ou d’un répartiteur 5 V correctement dimensionné. Le courant des DEL
ne doit pas traverser la broche `3V3` du Pico.

Un petit fusible en ligne peut être ajouté plus tard pour une protection
supplémentaire, surtout avec une alimentation brute de forte puissance. Il
n’est pas requis pour les premiers essais avec une batterie USB protégée.

La masse du Pico et celle de l’alimentation des DEL doivent obligatoirement être
communes.

Placer le condensateur de 1 000 µF entre `+5 V` et `GND` près du premier pixel.
Respecter sa polarité.

### Signal DATA

Le Pico produit un signal logique de 3,3 V tandis que les pixels fonctionnent
à 5 V. Un fil court entre GP0 et le premier pixel fonctionne souvent pour les
essais, mais un `74AHCT125` est recommandé pour un fonctionnement fiable dans
le cadre terminé.

Toujours suivre les indications `DATA IN`, `DIN`, `DATA OUT`, `DOUT` ou les
flèches du fabricant. La couleur des fils n’est pas une garantie.

### Deux guirlandes de 50 pixels

La première guirlande contient les pixels `0` à `49`.

Relier :

```text
DATA OUT du pixel 49 → DATA IN du premier pixel de la deuxième guirlande
```

Les 18 premiers pixels de la deuxième guirlande deviennent les indices `50` à
`67`. Les 32 pixels restants ne sont pas utilisés. Il est préférable de couper
ou déconnecter la chaîne après le pixel 67, puis d’isoler les extrémités.

Injecter de nouveau le 5 V et le GND près du début de la deuxième guirlande.
Une injection supplémentaire à l’extrémité peut être utile si la tension chute.

### Première alimentation sécuritaire

Pour les essais sur la table :

1. Alimenter le Pico depuis le Mac par son câble USB.
2. Alimenter les DEL depuis la batterie 5 V.
3. Relier les deux GND.
4. Ne pas relier la branche `+5 V` des DEL à `3V3`, `VBUS` ou `VSYS`.
5. Commencer avec une faible luminosité.

Dans le cadre terminé, la même batterie alimente le Pico par USB et les DEL par
la branche 5 V séparée représentée ci-dessus. Ne pas alimenter en même temps le
Pico par le Mac et par un raccordement supplémentaire sur `VSYS` sans circuit
de sélection d’alimentation. Le [schéma d’alimentation officiel du Pico 2
W](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf) décrit les
protections requises lorsqu’on combine plusieurs sources.

## Comment les DEL sont adressées

Les pixels WS2811 ne possèdent pas d’adresse permanente à programmer.

L’adresse dépend uniquement de la position électrique dans la chaîne :

```text
GP0 → pixel 0 → pixel 1 → pixel 2 → … → pixel 67
```

Le pixel dont `DATA IN` reçoit le signal du Pico est toujours l’index `0`.
Chaque pixel consomme sa portion du message et transmet le reste au suivant.

Après une coupure d’alimentation, les adresses demeurent donc les mêmes tant
que l’ordre du câblage n’a pas changé.

## Étape 1 — Installer MicroPython

1. Télécharger la version stable de MicroPython destinée au **Raspberry Pi
   Pico 2 W**.
2. Débrancher le Pico.
3. Maintenir le bouton `BOOTSEL`.
4. Rebrancher le câble USB tout en maintenant `BOOTSEL`.
5. Relâcher le bouton lorsque le lecteur USB du Pico apparaît.
6. Copier le fichier `.uf2` MicroPython sur ce lecteur.
7. Attendre le redémarrage du Pico.
8. Dans Thonny, sélectionner l’interpréteur MicroPython pour Raspberry Pi Pico.

## Étape 2 — Copier le programme sur le Pico

Copier le contenu du dossier [`pico/`](../pico/) à la racine du Pico :

```text
async_stm_api.py
config.py
gtfs_updater.py
led_mapping.py
led_display.py
main.py
metro_schedule_data.py
night_mode.py
power_safety.py
secrets.py
setup.html
setup_assistant.py
stations.py
stations_map.json
stm_status.py
train_schedule.py
wifi_manager.py
```

Les fichiers `stm_api.py` et `transit_status.py` peuvent également être copiés,
mais ne sont pas nécessaires à la boucle principale du Pico.

`main.py` doit se trouver à la racine du Pico pour démarrer automatiquement.

## Étape 3 — Configurer le Wi‑Fi et la clé STM

Créer le fichier privé `pico/secrets.py` à partir du modèle
[`pico/secrets.example.py`](../pico/secrets.example.py). Le vrai `secrets.py`
est ignoré par Git et ne doit jamais être publié ou envoyé avec une clé réelle.

S’il n’existe pas encore, copier `secrets.example.py` sous le nom `secrets.py`,
puis le remplir :

```python
WIFI_SSID = "NOM_DU_WIFI"
WIFI_PASSWORD = "MOT_DE_PASSE_WIFI"

WIFI_NETWORKS = [
    (WIFI_SSID, WIFI_PASSWORD),
    ("NOM_DU_WIFI_DE_SECOURS", "MOT_DE_PASSE_DU_WIFI_DE_SECOURS"),
]

STM_API_KEY = "VOTRE_CLE_PUBLIQUE_STM"

TRANSIT_API_KEY = ""
TRANSIT_NETWORK_IDS = ""
```

Le Wi‑Fi est nécessaire pour synchroniser l’horloge par NTP. Sans heure exacte,
le Pico ne peut pas déterminer quels trains théoriques devraient circuler.
Le Pico balaie les réseaux configurés dans `WIFI_NETWORKS`, choisit le premier
réseau visible selon l’ordre de priorité et essaie le suivant lorsque le
premier est absent. S’il perd la connexion pendant son fonctionnement, il
continue les animations et tente une reconnexion toutes les 10 secondes.

La clé STM est facultative pour l’animation GTFS, mais nécessaire pour
superposer les interruptions réelles du réseau.

Dans le portail STM :

1. Ajouter l’API « État du service » à l’application.
2. Créer une clé de type `Public`.
3. Enregistrer et publier la clé.
4. Copier la valeur `API Key`, pas le secret partagé.

## Étape 4 — Faire un test électrique sur la table

Ce test est facultatif, mais permet de repérer une erreur de câblage avant de
fermer le cadre. Il n’est pas nécessaire de décider quelle station correspond
à chaque numéro à cette étape : l’assistant de première configuration le fera.

### Tester un seul pixel

Dans Thonny, arrêter temporairement `main.py` avec `Ctrl-C`, puis exécuter :

```python
from led_display import MetroDisplay

display = MetroDisplay()
display.clear()
display.pixels[0] = (20, 20, 20)
display.pixels.write()
```

Seul le premier pixel doit s’allumer faiblement en blanc.

Pour l’éteindre :

```python
display.clear()
```

Si le premier pixel ne s’allume pas, vérifier le 5 V, le GND commun, le sens
`DIN/DOUT`, GP0 et la résistance DATA avant de brancher les 68 pixels.

### Tester la chaîne complète

Une fois la chaîne reliée :

```python
from led_display import MetroDisplay

display = MetroDisplay()
display.test_sequence(1000)
```

Chaque pixel s’allume seul pendant une seconde. La console affiche :

```text
physique 0 logique 0 Honoré-Beaugrand
physique 1 logique 1 Radisson
physique 2 logique 2 Langelier
...
physique 67 logique 67 Saint-Michel
```

Avant la configuration, cette commande utilise simplement l’ordre logique par
défaut. Au démarrage normal, l’autotest utilise plutôt la correspondance
enregistrée par l’assistant.

## Étape 5 — Installer les pixels sans imposer leur ordre

Installer chaque pixel derrière la station désirée. L’ordre électrique peut
être quelconque :

```text
DEL physique 1  → Radisson
DEL physique 2  → Champ-de-Mars
DEL physique 3  → Angrignon
…
```

Le programme n’exige pas que les pixels suivent visuellement une ligne de
métro. Les fils peuvent faire des sauts derrière l’affiche et les stations de
correspondance n’utilisent qu’un seul pixel.

Les nombres physiques sont déterminés uniquement par le câblage : le pixel
branché au Pico est la DEL physique 1 dans l’assistant, puis viennent 2 à 68.
Il n’est pas nécessaire d’étiqueter les stations à l’avance.

Le fichier [`pico/stations_map.json`](../pico/stations_map.json) décrit la
topologie logique du métro. Il ne doit pas être réécrit pour refléter l’ordre
des fils.

## Étape 6 — Utiliser l’assistant de première configuration

Au premier démarrage, `led_mapping.json` n’existe pas encore. Le Pico démarre
automatiquement un petit site Web local et fait clignoter une DEL blanche.

1. Alimenter le Pico et les pixels.
2. Sur un téléphone ou un ordinateur, rejoindre le réseau Wi‑Fi
   **`Metro-Setup`**.
3. Entrer le mot de passe **`metro-led-68`**.
4. Si le téléphone indique « Aucun accès à Internet », rester connecté à ce
   réseau.
5. Ouvrir **[http://192.168.4.1](http://192.168.4.1)** dans le navigateur.
6. Confirmer la langue détectée ou choisir français, anglais, espagnol ou
   italien dans le menu.
7. Regarder quelle DEL physique clignote.
8. Choisir la station placée devant elle, par exemple `Radisson` ou
   `Champ-de-Mars`.
9. Appuyer sur **Associer et passer à la suivante**.
10. Répéter jusqu’à ce que les 68 DEL soient associées.
11. Appuyer sur **Enregistrer et redémarrer**.

La langue du navigateur est détectée automatiquement. Un choix manuel est
mémorisé dans ce navigateur; il peut être modifié à tout moment sans interrompre
la configuration.

Chaque réponse est sauvegardée immédiatement dans
`led_mapping_draft.json`. Si le Pico est débranché au milieu de l’opération,
l’assistant reprend au même endroit au prochain démarrage.

Une même station ne peut pas être attribuée à deux DEL. Les boutons numérotés
permettent de revenir à n’importe quelle DEL pour corriger son association ou
relancer son clignotement.

À la fin, les 68 DEL deviennent vertes pendant trois secondes. Le Pico crée
`led_mapping.json`, efface le brouillon et redémarre automatiquement. Tous les
trains, couleurs et alertes utilisent ensuite cette correspondance.

### Refaire la correspondance plus tard

Avec Thonny, supprimer `led_mapping.json` de la racine du Pico, puis le
redémarrer. L’assistant réapparaîtra. Pour repartir complètement de zéro,
supprimer aussi `led_mapping_draft.json` s’il existe.

## Étape 7 — Démarrage normal

Au démarrage normal, le Pico effectue les opérations suivantes :

1. Charge `stations_map.json`.
2. Vérifie `led_mapping.json`.
3. Si la correspondance est absente ou invalide, lance l’assistant Web.
4. Sinon, initialise les 68 pixels sur GP0 avec la correspondance sauvegardée.
5. Exécute un bref test séquentiel.
6. Vérifie `secrets.py`.
7. Se connecte au Wi‑Fi.
8. Synchronise son horloge avec NTP.
9. Résout l’adresse de l’API STM.
10. Lance les deux tâches `uasyncio`.

La simulation ne démarre qu’après une synchronisation NTP réussie. Si le réseau
ou NTP est indisponible, le Pico réessaie automatiquement.

## Fonctionnement des animations

### Train théorique

Le moteur détermine les voyages GTFS actifs à l’heure locale de Montréal.

Pour un train situé entre la station A et la station B :

```text
première moitié du trajet : A vivement allumée, B éteinte
milieu du trajet          : le point saute nettement de A vers B
seconde moitié du trajet  : A éteinte, B vivement allumée
```

Comme le cadre ne possède pas de pixel entre deux stations, chaque rame est
représentée par une seule DEL à pleine intensité. Le saut net au milieu du temps
de parcours est beaucoup plus facile à distinguer qu’un changement subtil de
luminosité. Chaque rame possède sa propre phase; les sauts sont donc indépendants
et la carte reste visiblement active sans dépendre d'une séquence de test.

Les stations sans train sont complètement éteintes. La luminosité globale des
stations occupées reste limitée à 20 % dans `config.py`.

Comme le GTFS statique arrondit souvent les passages à la minute, chaque voyage
reçoit une petite variation déterministe pouvant atteindre 28 secondes. Cette
variation demeure stable après un redémarrage et évite que plusieurs trains
avancent en bloc.

### Mode nuit

Le mode nuit utilise l’heure locale de Montréal et les voyages GTFS actifs.
Par défaut :

- 23 h ouvre seulement la fenêtre où le mode nuit devient possible;
- tant qu’au moins un train planifié circule, le cadre reste en mode jour;
- il s’active après le dernier train planifié;
- il se termine dès le premier train du matin, ou au plus tard à 6 h;
- toute la carte respire lentement dans ses couleurs de ligne;
- un cycle complet dure 18 secondes;
- la luminosité oscille doucement entre environ 0,1 % et 0,45 %;
- les perturbations restent visibles à seulement 0,75 % au maximum pendant la
  fermeture.

Une prolongation d’horaire repousse donc automatiquement le mode nuit. Une
interruption générale du réseau ne déclenche pas le mode nuit : le programme
regarde les voyages planifiés avant d’appliquer les alertes STM.

Le passage jour/nuit se fait sans interrompre les tâches ni les requêtes STM.
Les bornes de la fenêtre et la luminosité sont modifiables dans `config.py`.

### Limiteur de courant

Toutes les écritures, y compris l’assistant, l’autotest et l’écran d’erreur,
passent par `power_safety.py`. Avant chaque image, ce module :

- bloque les valeurs RGB négatives ou supérieures au plafond;
- limite chaque canal à `64/255`, soit environ 25 %;
- estime le courant des 68 contrôleurs et canaux RGB;
- réduit proportionnellement l’image entière si elle dépasse 1 000 mA.

Ce plafond concerne la chaîne de DEL. Il faut ajouter la consommation du Pico à
celle de la chaîne pour choisir la batterie.

### Station de correspondance

Une station appartenant à plusieurs lignes est affichée en blanc. Son intensité
peut représenter un train de n’importe laquelle de ses lignes.

### Plusieurs trains près de la même station

Une seule DEL ne peut pas afficher plusieurs trains séparément. Le programme
conserve donc l’intensité la plus élevée calculée pour cette station.

### Service ralenti

Les stations concernées pulsent en ambre. Une pulsation complète dure environ
1,8 seconde.

### Interruption

Toutes les stations de la ligne concernée produisent deux éclats rouges rapides,
suivis d’une pause. Ce motif dure 2,4 secondes et ne peut pas être confondu avec
la fermeture d’une seule station.

Les trains théoriques de cette ligne sont retirés immédiatement. Les autres
lignes continuent leur mouvement.

### Fermeture ou problème à une station

Si une alerte de service cible clairement une station, seule cette station
reçoit l’effet correspondant. Une fermeture produit trois petits éclats rouges;
un ralentissement conserve la respiration ambre.

Les avis concernant uniquement un accès fermé, un arrêt d’autobus déplacé ou
des travaux sans effet sur le service métro sont ignorés.

### Erreur de configuration

Si le Wi‑Fi est absent ou contient encore les valeurs d’exemple, trois DEL
magenta produisent un motif long–court–court. Une erreur fatale utilise plutôt
le motif magenta–blanc–magenta.

### Langage des états techniques

| État | Animation |
|---|---|
| Mise sous tension | Point blanc parcourant les 68 DEL |
| Vérification des lignes | Verte, orange, jaune et bleue successivement |
| Connexion Wi‑Fi | Chenillard cyan; sa direction change au réseau suivant |
| Wi‑Fi connecté | Deux impulsions cyan |
| Synchronisation de l’heure | Quatre repères blancs en mouvement |
| Chargement de l’horaire | Les quatre lignes apparaissent successivement |
| Système prêt | Révélation colorée de toute la carte, puis affichage des trains |
| Wi‑Fi perdu | Court chenillard cyan toutes les 10 secondes; les trains continuent |
| API STM inaccessible trois fois | Deux repères cyan toutes les 30 secondes |
| Horaire GTFS expiré | Double balayage ambre toutes les 30 secondes |
| Mise à jour GTFS | Progression cyan le long de la chaîne |
| Mise à jour réussie | Ouverture blanche depuis le centre, puis redémarrage |
| Échec de mise à jour | Double signal magenta et ambre; l’ancien horaire demeure |
| Protection électrique | Trois signaux ambre; le limiteur reste prioritaire |
| Reprise du service | Balayage unique dans la couleur de la ligne rétablie |

Les interruptions STM ont priorité sur les ralentissements, qui ont priorité
sur les avis techniques. Un avertissement Wi‑Fi ou GTFS ne peut donc jamais
recouvrir une ligne interrompue. Les avis techniques sont supprimés pendant le
mode nuit, sauf l’erreur critique qui empêche le programme de démarrer.

### DEL intégrée du Pico

- allumée : la dernière vérification STM a réussi, ou les alertes sont
  volontairement désactivées;
- éteinte : la dernière requête STM a échoué;
- clignotante avant l’animation : le Pico essaie de configurer le réseau ou
  signale un problème de configuration.

En cas d’échec de l’API STM, le dernier état valide est conservé et l’animation
GTFS continue.

## Architecture asynchrone

Deux tâches s’exécutent simultanément :

### `animate_loop`

- cadence : 40 ms, soit environ 25 images par seconde;
- calcule l’heure locale de Montréal;
- trouve les trains théoriques actifs;
- calcule leur progression sur chaque segment;
- place chaque train sur une seule station et le fait sauter à mi-segment;
- retire les trains des lignes interrompues;
- rafraîchit les 68 pixels.

### `api_monitor_loop`

- s’exécute immédiatement au démarrage;
- recommence toutes les 60 secondes après le début de la requête précédente;
- utilise une connexion HTTPS asynchrone;
- accepte jusqu’à 90 secondes pour parcourir une première grosse réponse STM;
- utilise ensuite l’ETag du serveur pour recevoir rapidement « inchangé »;
- réessaie après 15 secondes en cas d’échec et renouvelle la résolution DNS
  seulement après une erreur de transport ou une reconnexion Wi-Fi;
- met à jour `system_status`.

Le dictionnaire partagé ressemble à ceci :

```python
system_status = {
    "green": "ok",
    "orange": "interrupted",
    "yellow": "ok",
    "blue": "ok",
}
```

## Simulateur local

Le simulateur permet de vérifier la logique sans Pico.

Depuis le dossier du projet :

```bash
python3 simulator/server.py
```

Ouvrir ensuite :

```text
http://127.0.0.1:8765
```

Le bouton **Assistant initial** ouvre une copie interactive de la véritable
page de première configuration. Cette prévisualisation utilise 68 DEL simulées
et ne commande aucun matériel.

L’adresse `http://127.0.0.1:8765/admin-preview` ouvre aussi le véritable
panneau de contrôle avec le NIP `metro68`. Ses réglages restent en mémoire
jusqu’à l’arrêt du simulateur et ses commandes de redémarrage ou de maintenance
sont simulées; elles ne touchent jamais le Pico.

### Modes disponibles

| Mode | Utilité |
|---|---|
| Direct — style Metroboard | Marqueurs de trains estimés selon le GTFS, avec alertes STM |
| Mode nuit — respiration paisible | Prévisualise le cycle nocturne de 18 secondes; sa luminosité est amplifiée à l’écran |
| Tout normal | Affichage statique sans trains ni perturbations |
| Interruption verte | Test du clignotement rouge de la ligne verte |
| Interruption orange | Vérifie que l’orange s’arrête pendant que les autres lignes continuent |
| Ralentissement orange | Test de la pulsation ambre |
| Berri-UQAM fermée | Test d’une perturbation limitée à une station |
| Reprise de la ligne orange | Test du balayage de retour au service |
| Test séquentiel | Allume les 68 DEL virtuelles une à une |

Le menu contient aussi tous les états de mise en marche, de connexion, de mise
à jour et d’erreur. Ils reproduisent le même vocabulaire visuel que le Pico.

Dans le mode direct :

- les trains sont recalculés chaque seconde dans l’interface Web;
- l’état STM est actualisé toutes les 60 secondes;
- les alertes proviennent uniquement de STM i3 v2, comme sur le Pico; les
  alertes Transit ne sont pas fusionnées à l’affichage;
- si une lecture STM échoue, le dernier état valide est conservé, comme sur le
  Pico;
- le nombre de trains théoriques de chaque ligne est affiché;
- « alertes STM i3 v2 » confirme que la clé est active.

Pour afficher l’état dans le Terminal :

```bash
python3 simulator/live_status.py
python3 simulator/live_status.py --watch
```

Arrêter le serveur avec `Ctrl-C`.

## Panneau de contrôle du Pico

Le Pico sert une seconde interface Web pendant son fonctionnement normal. La
console affiche son adresse après la connexion, par exemple :

```text
Panneau de contrôle: http://192.168.68.107/admin
```

Le téléphone ou l’ordinateur doit être connecté au même réseau Wi‑Fi. Le NIP
provient de `CONTROL_PANEL_PIN` dans `secrets.py`; si la variable est absente,
le NIP de départ est `metro68`. Il est recommandé de le personnaliser.

Le panneau, disponible en français, anglais, espagnol et italien, permet de :

- voir l’heure montréalaise, le Wi‑Fi, l’adresse IP, les trains, la mémoire,
  le GTFS, les lignes et les échecs de lecture STM;
- régler séparément la luminosité de jour, de nuit et des signaux techniques;
- choisir le mode automatique, jour forcé, nuit forcée ou éteint;
- changer la fenêtre nocturne;
- lancer un test des 68 DEL, des quatre lignes ou de la carte entière;
- demander une lecture STM ou une vérification GTFS immédiate;
- reconnecter le Wi‑Fi ou redémarrer le Pico;
- effacer l’association des stations après une confirmation explicite.

Les réglages validés sont écrits dans `user_settings.json`. Les plafonds de
sécurité demeurent prioritaires : le panneau ne peut pas dépasser 20 % le jour,
1,2 % au sommet de la respiration nocturne ni 15 % pour les signaux. La page
`admin.html` est lue par petits morceaux seulement lorsqu’un navigateur la
demande; elle ne demeure pas en mémoire et l’animation à 25 images/seconde
continue dans sa tâche indépendante.

Le panneau est volontairement limité au réseau local et utilise HTTP. Il ne
doit pas être exposé directement sur Internet. Si le Pico n’a plus de Wi‑Fi ou
de courant, il faut intervenir localement.

## Réglages principaux

Les valeurs de départ se trouvent dans [`pico/config.py`](../pico/config.py).
Les changements effectués dans le panneau sont conservés séparément dans
`user_settings.json` et ont priorité au prochain démarrage.

```python
DATA_PIN = 0
NUMBER_OF_LEDS = 68
BRIGHTNESS = 0.20
TRAIN_BASE_LEVEL = 0.0
TRAIN_TIMING_VARIATION_SECONDS = 28
PIXEL_TIMING = 1

LED_CURRENT_LIMIT_MA = 1000
LED_MAX_CHANNEL_VALUE = 64

NIGHT_MODE_ENABLED = True
NIGHT_START_HOUR = 23
NIGHT_END_HOUR = 6
NIGHT_BRIGHTNESS = 0.03
NIGHT_AMBIENT_ENABLED = True
NIGHT_AMBIENT_PERIOD_MS = 18000
NIGHT_AMBIENT_MIN_LEVEL = 0.20
NIGHT_AMBIENT_MAX_LEVEL = 1.00

API_MONITOR_INTERVAL_SECONDS = 60
ANIMATION_FRAME_MS = 40
SLOW_PULSE_PERIOD_MS = 1800
STOP_BLINK_PERIOD_MS = 700
```

Ne pas augmenter `BRIGHTNESS`, `LED_MAX_CHANNEL_VALUE` ou
`LED_CURRENT_LIMIT_MA` sans vérifier la capacité de l’alimentation, des fils,
des connecteurs et des points d’injection.

## Mise à jour des horaires GTFS

Le fichier [`pico/metro_schedule_data.py`](../pico/metro_schedule_data.py) est une
version compacte du GTFS STM, adaptée à la mémoire du Pico.

La période actuellement incluse est inscrite dans sa constante `FEED`. Lorsque
la période expire, le Pico affiche un avertissement dans la console et il peut
ne plus trouver de trains actifs.

Pour télécharger et reconstruire l’horaire :

```bash
mkdir -p data
curl -L https://www.stm.info/sites/default/files/gtfs/gtfs_stm.zip \
  -o data/gtfs_stm.zip
python3 scripts/build_metro_schedule.py
```

Le générateur :

- conserve uniquement les quatre lignes de métro;
- transforme les stations en indices de DEL;
- valide chaque trajet par rapport à `stations_map.json`;
- regroupe les variantes semblables;
- crée un fichier suffisamment compact pour le Pico.

### Mise à jour automatique

Le projet contient maintenant une chaîne de mise à jour complète :

1. `.github/workflows/update-gtfs.yml` vérifie chaque lundi l’archive publique
   de la STM;
2. `scripts/build_metro_schedule.py` produit un candidat compact;
3. `scripts/publish_gtfs_update.py` ignore les reconstructions identiques et
   publie `updates/latest.json` avec le fichier et son empreinte SHA-256, puis
   synchronise la copie prête à déposer sur le Pico;
4. `scripts/update_package_manifest.py` recalcule les empreintes du livrable;
5. `pico/gtfs_updater.py` vérifie quotidiennement le manifeste, télécharge le
   fichier par blocs de 1 Ko, le valide, garde une sauvegarde, puis redémarre;
6. si le téléchargement ou l’écriture est interrompu, l’ancien horaire reste
   utilisable ou est restauré au démarrage suivant.

Les données sont publiées automatiquement dans le dépôt public séparé
[`nvldboy/cadre-metro-montreal-updates`](https://github.com/nvldboy/cadre-metro-montreal-updates).
Le dépôt principal peut donc rester privé. La configuration livrée contient :

```python
GTFS_AUTO_UPDATE_ENABLED = True
GTFS_UPDATE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/nvldboy/"
    "cadre-metro-montreal-updates/main/updates/latest.json"
)
```

Ne jamais ajouter `pico/secrets.py` au dépôt. Il est déjà exclu par
`.gitignore`. Le Pico vérifie le manifeste une fois par jour et conserve
l’horaire intégré si le service public est temporairement inaccessible.

## Tests du programme

Sur le Mac :

```bash
python3 -m unittest discover -s tests -v
```

Les tests vérifient notamment :

- la validation, l’inversion et la reprise de la correspondance des DEL;
- les heures de passage entre les modes jour et nuit;
- le plafonnement des canaux et du courant estimé;
- les quatre lignes;
- les interruptions;
- les ralentissements;
- les stations nommées dans les alertes;
- l’exclusion des simples fermetures d’accès;
- le saut indépendant des marqueurs entre deux stations;
- le changement d’heure de Montréal;
- l’arrêt ciblé d’une seule ligne;
- la cohérence entre `stations.py` et `stations_map.json`.

## Dépannage

| Problème | Vérifications |
|---|---|
| Aucune DEL ne s’allume | Vérifier le 5 V externe, le GND commun, GP0, la résistance et le sens `DATA IN` |
| Le premier pixel fonctionne, mais pas les suivants | Vérifier `DATA OUT → DATA IN` et chercher un pixel ou une jonction défectueuse |
| Seulement les 50 premiers fonctionnent | Vérifier la jonction entre les deux guirlandes et l’injection d’alimentation |
| Les pixels clignotent au hasard | Ajouter le GND commun, raccourcir DATA, utiliser un `74AHCT125` et injecter le 5 V à plusieurs endroits |
| La fin de la chaîne jaunit ou faiblit | Chute de tension : augmenter la section des fils et injecter le 5 V près du pixel 50 et à l’extrémité |
| Le réseau `Metro-Setup` n’apparaît pas au premier démarrage | Vérifier que `led_mapping.json` est absent et que `setup_assistant.py`, `setup.html` et `led_mapping.py` ont été copiés |
| Le téléphone quitte `Metro-Setup` | Désactiver temporairement le basculement vers les données cellulaires, rester sur ce réseau, puis ouvrir `http://192.168.4.1` |
| Une station incorrecte s’allume | Supprimer `led_mapping.json`, redémarrer et refaire l’association de la chaîne |
| Toutes les DEL sont magenta | Compléter le Wi‑Fi dans `secrets.py` |
| Le Pico reste avant l’animation | Vérifier le Wi‑Fi 2,4 GHz, Internet et la synchronisation NTP |
| Le panneau ne s’ouvre pas | Vérifier l’adresse IP imprimée dans Thonny et que le téléphone est sur le même Wi‑Fi; ouvrir `/admin` |
| Le NIP du panneau est refusé | Vérifier `CONTROL_PANEL_PIN` dans `secrets.py`; sans cette variable, utiliser `metro68` |
| Les trains sont visibles, mais pas les alertes STM | Vérifier la clé publique, l’API ajoutée à l’application et l’état publié de la clé |
| L’API répond `Invalid API Key` | Utiliser `API Key`, pas le secret partagé, puis enregistrer et publier la clé |
| Aucune position de train n’apparaît | Vérifier l’heure, la période GTFS et si le métro est normalement en service |
| Les couleurs rouge et verte semblent inversées | Faire un test RGB manuel; l’ordre des canaux du lot de pixels peut différer |
| La batterie s’éteint seule | Utiliser une sortie toujours active ou une alimentation sans coupure automatique à faible charge |

## Rôle des principaux fichiers

| Fichier | Rôle |
|---|---|
| `pico/main.py` | Démarrage, NTP et tâches `uasyncio` |
| `pico/led_display.py` | Couleurs, luminosité, pulsation et clignotement |
| `pico/led_mapping.py` | Validation et sauvegarde de la correspondance physique |
| `pico/night_mode.py` | Activation automatique du mode nuit |
| `pico/power_safety.py` | Plafond RGB et limiteur global de courant |
| `pico/setup_assistant.py` | Point d’accès et serveur Web de première configuration |
| `pico/setup.html` | Interface mobile de l’assistant |
| `pico/control_panel.py` | Serveur Web local protégé par NIP |
| `pico/admin.html` | Panneau de contrôle en quatre langues |
| `pico/runtime_settings.py` | Validation et sauvegarde des réglages Web |
| `user_settings.json` sur le Pico | Préférences persistantes du panneau |
| `pico/train_schedule.py` | Calcul et interpolation des trains |
| `pico/metro_schedule_data.py` | Horaire GTFS compact |
| `pico/stations.py` | Noms, couleurs et index logiques |
| `pico/stations_map.json` | Ordre logique des stations et tracé des quatre lignes |
| `led_mapping.json` sur le Pico | Correspondance physique créée par l’assistant |
| `pico/async_stm_api.py` | Requête HTTPS asynchrone vers la STM |
| `pico/stm_status.py` | Interprétation des alertes STM |
| `pico/wifi_manager.py` | Connexion Wi‑Fi et synchronisation NTP |
| `pico/gtfs_updater.py` | Mise à jour atomique de l’horaire compact |
| `pico/config.py` | Paramètres modifiables |
| `pico/secrets.py` | Wi‑Fi et clé API locale, ignorés par Git |
| `simulator/server.py` | Serveur du simulateur local |
| `simulator/index.html` | Carte Web et animations virtuelles |
| `scripts/build_metro_schedule.py` | Conversion du GTFS vers le format Pico |
| `scripts/publish_gtfs_update.py` | Manifeste, empreinte et publication |
| `.github/workflows/update-gtfs.yml` | Vérification automatique hebdomadaire |

## Données et limites

Les données planifiées proviennent de la Société de transport de Montréal et
sont offertes sous licence CC BY 4.0.

Les flux GTFS-Realtime de la STM fournissent les positions réelles des autobus,
pas celles des trains du métro. Le cadre ne doit donc pas être utilisé comme
source d’horaire garantie ou pour décider du moment où se présenter en station.

L’API STM est interrogée une fois par minute, soit environ 1 440 requêtes par
jour lorsque le cadre fonctionne pendant 24 heures.
