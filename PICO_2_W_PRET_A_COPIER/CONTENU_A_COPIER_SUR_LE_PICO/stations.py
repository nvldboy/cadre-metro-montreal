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

LINE_COLORS = {
    "green": (0, 166, 81),
    "orange": (245, 130, 32),
    "yellow": (255, 210, 0),
    "blue": (0, 114, 188),
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
