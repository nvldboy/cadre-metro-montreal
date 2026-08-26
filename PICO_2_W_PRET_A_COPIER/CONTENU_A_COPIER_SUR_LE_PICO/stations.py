"""Correspondance entre les 68 stations, les lignes et les DEL.

L'indice de chaque nom dans STATION_ORDER est l'indice de sa DEL.
L'ordre ci-dessous est provisoire mais valide si le cadre est câblé dans
exactement cet ordre. Il peut être remplacé après le test séquentiel.
"""

GREEN = (
    "Honoré-Beaugrand", "Radisson", "Langelier", "Cadillac", "Assomption",
    "Viau", "Pie-IX", "Joliette", "Préfontaine", "Frontenac", "Papineau",
    "Beaudry", "Berri-UQAM", "Saint-Laurent", "Place-des-Arts", "McGill",
    "Peel", "Guy-Concordia", "Atwater", "Lionel-Groulx", "Charlevoix",
    "LaSalle", "De l’Église", "Verdun", "Jolicoeur", "Monk", "Angrignon",
)

ORANGE = (
    "Montmorency", "De la Concorde", "Cartier", "Henri-Bourassa", "Sauvé",
    "Crémazie", "Jarry", "Jean-Talon", "Beaubien", "Rosemont", "Laurier",
    "Mont-Royal", "Sherbrooke", "Berri-UQAM", "Champ-de-Mars",
    "Place-d’Armes", "Square-Victoria–OACI", "Bonaventure",
    "Lucien-L’Allier", "Georges-Vanier", "Lionel-Groulx",
    "Place-Saint-Henri", "Vendôme", "Villa-Maria", "Snowdon",
    "Côte-Sainte-Catherine", "Plamondon", "Namur", "De la Savane",
    "Du Collège", "Côte-Vertu",
)

YELLOW = (
    "Berri-UQAM", "Jean-Drapeau",
    "Longueuil–Université-de-Sherbrooke",
)

BLUE = (
    "Snowdon", "Côte-des-Neiges", "Université-de-Montréal",
    "Édouard-Montpetit", "Outremont", "Acadie", "Parc", "De Castelnau",
    "Jean-Talon", "Fabre", "D’Iberville", "Saint-Michel",
)

LINE_STATIONS = {
    "green": GREEN,
    "orange": ORANGE,
    "yellow": YELLOW,
    "blue": BLUE,
}

# Couleurs RVB de référence relevées dans le plan officiel du métro publié
# par la STM en mai 2026 (PM-C2436-B_FRA_WEB).
STM_SCREEN_COLORS = {
    "green": (0, 150, 81),       # #009651
    "orange": (216, 127, 63),    # #D87F3F
    "yellow": (249, 219, 79),    # #F9DB4F
    "blue": (0, 114, 171),       # #0072AB
}

# Palette calibrée pour les pixels WS2811 de 12 mm. Leurs primaires sont
# beaucoup plus saturées que celles d'un écran : reprendre les valeurs RVB
# ci-dessus rend le bleu et le vert cyan, et l'orange et le jaune trop blancs.
# Ces rapports compensent ce comportement tout en conservant l'identité STM.
LINE_COLORS = {
    "green": (0, 255, 10),
    "orange": (255, 65, 0),
    "yellow": (255, 170, 0),
    "blue": (0, 8, 255),
}

# Ordre de câblage proposé. Cette table est volontairement explicite pour
# pouvoir être réordonnée facilement après le test séquentiel.
STATION_ORDER = (
    "Honoré-Beaugrand",
    "Radisson",
    "Langelier",
    "Cadillac",
    "Assomption",
    "Viau",
    "Pie-IX",
    "Joliette",
    "Préfontaine",
    "Frontenac",
    "Papineau",
    "Beaudry",
    "Berri-UQAM",
    "Saint-Laurent",
    "Place-des-Arts",
    "McGill",
    "Peel",
    "Guy-Concordia",
    "Atwater",
    "Lionel-Groulx",
    "Charlevoix",
    "LaSalle",
    "De l’Église",
    "Verdun",
    "Jolicoeur",
    "Monk",
    "Angrignon",
    "Montmorency",
    "De la Concorde",
    "Cartier",
    "Henri-Bourassa",
    "Sauvé",
    "Crémazie",
    "Jarry",
    "Jean-Talon",
    "Beaubien",
    "Rosemont",
    "Laurier",
    "Mont-Royal",
    "Sherbrooke",
    "Champ-de-Mars",
    "Place-d’Armes",
    "Square-Victoria–OACI",
    "Bonaventure",
    "Lucien-L’Allier",
    "Georges-Vanier",
    "Place-Saint-Henri",
    "Vendôme",
    "Villa-Maria",
    "Snowdon",
    "Côte-Sainte-Catherine",
    "Plamondon",
    "Namur",
    "De la Savane",
    "Du Collège",
    "Côte-Vertu",
    "Jean-Drapeau",
    "Longueuil–Université-de-Sherbrooke",
    "Côte-des-Neiges",
    "Université-de-Montréal",
    "Édouard-Montpetit",
    "Outremont",
    "Acadie",
    "Parc",
    "De Castelnau",
    "Fabre",
    "D’Iberville",
    "Saint-Michel",
)
STATION_INDEX = {
    station_name: led_index
    for led_index, station_name in enumerate(STATION_ORDER)
}

STATION_LINES = {}
for _line_name, _station_names in LINE_STATIONS.items():
    for _station_name in _station_names:
        STATION_LINES.setdefault(_station_name, []).append(_line_name)

if len(STATION_ORDER) != 68:
    raise ValueError("La table doit contenir exactement 68 stations uniques")
if len(set(STATION_ORDER)) != 68:
    raise ValueError("Chaque station doit apparaître une seule fois")
