from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QMenu

from app.infos import DOSSIER_APPLI

DOSSIER_POLICES = DOSSIER_APPLI / "ressources" / "polices"
DOSSIER_ICONES = DOSSIER_APPLI / "ressources" / "icones"
POLICE_TEXTE = "Albert Sans"
POLICE_TITRES = "Cinzel"
TAILLE_TEXTE = 13
CHOIX = ("clair", "sombre", "systeme")
CHOIX_DEFAUT = "sombre"

PALETTES = {
    "sombre": {
        "FOND": "#0a0f1c",
        "BARRE": "#0c1323",
        "SURFACE": "#111a2c",
        "SURFACE_HAUTE": "#17223a",
        "MENU": "#16213a",
        "BORDURE": "#24314d",
        "TEXTE": "#eceef3",
        "TEXTE_DOUX": "#9aa5bb",
        "TEXTE_ETEINT": "#7a859c",
        "OR": "#d4ab57",
        "OR_HAUT": "#ecd08b",
        "OR_BAS": "#b48a3a",
        "OR_CLAIR": "#e3c37a",
        "ENCRE": "#1b1406",
        "ROUGE": "#f07a70",
        "VERT": "#5cc995",
        "AZUR": "#79b9f0",
        "VOILE": "#d4ab57",
        "TRAIT": "#d4ab57",
        "ALPHA_VOILE": 33,
        "ALPHA_TRAIT": 97,
        "BARRE_BAS": "#0a0f1c",
        "PISTE": "#17223a",
    },
    "clair": {
        "FOND": "#f3eee3",
        "BARRE": "#ebe3d2",
        "SURFACE": "#fbf8f2",
        "SURFACE_HAUTE": "#efe7d7",
        "MENU": "#fffdf8",
        "BORDURE": "#d9cbb0",
        "TEXTE": "#1c2333",
        "TEXTE_DOUX": "#565d6e",
        "TEXTE_ETEINT": "#666b77",
        "OR": "#c99a39",
        "OR_HAUT": "#e0b95e",
        "OR_BAS": "#b3852b",
        "OR_CLAIR": "#7a5813",
        "ENCRE": "#1d1405",
        "ROUGE": "#b83b32",
        "VERT": "#1f7a52",
        "AZUR": "#2667a8",
        "VOILE": "#b98c2e",
        "TRAIT": "#966e1e",
        "ALPHA_VOILE": 38,
        "ALPHA_TRAIT": 102,
        "BARRE_BAS": "#ebe3d2",
        "PISTE": "#d9cbb0",
    },
}

DOMAINES = [
    ("Fury", "#e0303a"),
    ("Calm", "#55a843"),
    ("Mind", "#2389c9"),
    ("Body", "#f08a1c"),
    ("Chaos", "#8b5cc4"),
    ("Order", "#d8bc2a"),
    ("Colorless", "#8f9bb3"),
]

RARETES = [
    ("Common", "#a4b8aa"),
    ("Uncommon", "#41b4b8"),
    ("Rare", "#c47bb4"),
    ("Epic", "#d0874f"),
    ("Showcase", "#d4b445"),
    ("Promo", "#f778ba"),
]

FOND = BARRE = SURFACE = SURFACE_HAUTE = MENU = BORDURE = ""
TEXTE = TEXTE_DOUX = TEXTE_ETEINT = ""
OR = OR_HAUT = OR_BAS = OR_CLAIR = ENCRE = ROUGE = VERT = AZUR = ""
globals().update(PALETTES["sombre"])

_choix = CHOIX_DEFAUT
_mode = "sombre"
_en_cours = False
_signaux = None


class Signaux(QObject):
    change = Signal()


def signaux():
    global _signaux
    if _signaux is None:
        _signaux = Signaux()
    return _signaux


def choix():
    return _choix


def mode():
    return _mode


def couleur(nom, alpha=None):
    resultat = QColor(globals()[nom])
    if alpha is not None:
        resultat.setAlpha(alpha)
    return resultat


def voile():
    return couleur("VOILE", PALETTES[_mode]["ALPHA_VOILE"])


def trait():
    return couleur("TRAIT", PALETTES[_mode]["ALPHA_TRAIT"])


def mode_pour(valeur):
    if valeur != "systeme":
        return valeur
    schema = QGuiApplication.styleHints().colorScheme()
    return "clair" if schema == Qt.ColorScheme.Light else "sombre"


def charger_polices():
    for fichier in sorted(DOSSIER_POLICES.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(fichier))


def police_titres(taille):
    police = QFont(POLICE_TITRES)
    police.setPixelSize(taille)
    police.setWeight(QFont.Weight.ExtraBold)
    return police


def appliquer_theme(application):
    charger_polices()
    application.setStyle("Fusion")
    police = QFont(POLICE_TEXTE)
    police.setPixelSize(TAILLE_TEXTE)
    application.setFont(police)
    application.styleHints().colorSchemeChanged.connect(_schema_systeme_change)
    valeur = QSettings().value("theme", CHOIX_DEFAUT)
    choisir(valeur if valeur in CHOIX else CHOIX_DEFAUT, sauver=False)


def choisir(valeur, sauver=True):
    global _choix, _en_cours
    _choix = valeur
    if sauver:
        QSettings().setValue("theme", valeur)
    indications = QGuiApplication.styleHints()
    if hasattr(indications, "setColorScheme"):
        schemas = {"clair": Qt.ColorScheme.Light, "sombre": Qt.ColorScheme.Dark}
        _en_cours = True
        try:
            indications.setColorScheme(schemas.get(valeur, Qt.ColorScheme.Unknown))
        finally:
            _en_cours = False
    _appliquer(mode_pour(valeur))


def _schema_systeme_change(schema):
    if _en_cours or _choix != "systeme":
        return
    nouveau = mode_pour("systeme")
    if nouveau != _mode:
        _appliquer(nouveau)


def _appliquer(nouveau_mode):
    global _mode
    _mode = nouveau_mode
    palette = PALETTES[nouveau_mode]
    globals().update({cle: valeur for cle, valeur in palette.items() if isinstance(valeur, str)})
    application = QApplication.instance()
    application.setPalette(_palette(palette))
    application.setStyleSheet(_feuille(palette))
    signaux().change.emit()


def _palette(p):
    palette = QPalette()
    roles = QPalette.ColorRole
    for role, valeur in (
        (roles.Window, p["FOND"]),
        (roles.WindowText, p["TEXTE"]),
        (roles.Base, p["SURFACE"]),
        (roles.AlternateBase, p["SURFACE_HAUTE"]),
        (roles.Text, p["TEXTE"]),
        (roles.Button, p["SURFACE_HAUTE"]),
        (roles.ButtonText, p["TEXTE"]),
        (roles.BrightText, p["TEXTE"]),
        (roles.Highlight, p["OR"]),
        (roles.HighlightedText, p["ENCRE"]),
        (roles.ToolTipBase, p["MENU"]),
        (roles.ToolTipText, p["TEXTE"]),
        (roles.PlaceholderText, p["TEXTE_ETEINT"]),
        (roles.Link, p["OR_CLAIR"]),
        (roles.LinkVisited, p["OR_CLAIR"]),
        (roles.Light, p["SURFACE_HAUTE"]),
        (roles.Midlight, p["SURFACE_HAUTE"]),
        (roles.Mid, p["BORDURE"]),
        (roles.Dark, p["BORDURE"]),
        (roles.Shadow, p["FOND"]),
    ):
        palette.setColor(role, QColor(valeur))
    for role in (roles.Text, roles.ButtonText, roles.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(p["TEXTE_ETEINT"]))
    return palette


def _rgba(hexa, alpha):
    teinte = QColor(hexa)
    return f"rgba({teinte.red()}, {teinte.green()}, {teinte.blue()}, {alpha})"


def _feuille(p):
    voile_or = _rgba(p["VOILE"], p["ALPHA_VOILE"])
    voile_fort = _rgba(p["VOILE"], p["ALPHA_VOILE"] * 2)
    trait_or = _rgba(p["TRAIT"], p["ALPHA_TRAIT"])
    rouge_trait = _rgba(p["ROUGE"], 115)
    rouge_voile = _rgba(p["ROUGE"], 32)
    coche = (DOSSIER_ICONES / "check.svg").as_posix()
    degrade_or = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {p['OR_HAUT']}, stop:1 {p['OR_BAS']})"
    degrade_or_survol = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {p['OR_HAUT']}, stop:1 {p['OR']})"
    return f"""
QWidget {{
    color: {p['TEXTE']};
    font-family: "{POLICE_TEXTE}";
    font-size: {TAILLE_TEXTE}px;
}}
QMainWindow, QDialog {{
    background: {p['FOND']};
}}
QWidget#barre_laterale {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {p['BARRE']}, stop:1 {p['BARRE_BAS']});
    border-right: 1px solid {p['BORDURE']};
}}
QLabel#logo {{
    font-family: "{POLICE_TITRES}";
    font-weight: 800;
    font-size: 16px;
    letter-spacing: 2px;
    color: {p['OR_CLAIR']};
}}
QLabel#logo_sous {{
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 3px;
    color: {p['TEXTE_ETEINT']};
}}
QLabel#titre {{
    font-family: "{POLICE_TITRES}";
    font-weight: 800;
    font-size: 26px;
    letter-spacing: 1px;
    color: {p['TEXTE']};
}}
QLabel#titre_connexion {{
    font-family: "{POLICE_TITRES}";
    font-weight: 800;
    font-size: 20px;
    letter-spacing: 1px;
    color: {p['TEXTE']};
}}
QLabel#titre_section {{
    font-family: "{POLICE_TITRES}";
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 2px;
    color: {p['OR_CLAIR']};
}}
QLabel#titre_vide {{
    font-family: "{POLICE_TITRES}";
    font-weight: 800;
    font-size: 17px;
}}
QLabel#sous_titre {{
    color: {p['TEXTE_DOUX']};
}}
QLabel#libelle {{
    font-size: 14px;
    font-weight: 600;
}}
QLabel#aide {{
    font-size: 12px;
    color: {p['TEXTE_DOUX']};
}}
QLabel#chemin {{
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 12px;
    color: {p['TEXTE_DOUX']};
}}
QLabel#puce {{
    background: {voile_or};
    border: 1px solid {trait_or};
    border-radius: 10px;
    padding: 1px 8px;
    color: {p['OR_CLAIR']};
    font-size: 12px;
    font-weight: 700;
}}
QLabel#pseudo {{
    font-size: 14px;
    font-weight: 700;
}}
QLabel#touche {{
    background: {p['SURFACE_HAUTE']};
    border: 1px solid {p['BORDURE']};
    border-bottom-width: 2px;
    border-radius: 6px;
    color: {p['TEXTE']};
    font-size: 12px;
    font-weight: 700;
    padding: 2px 8px;
}}
QFrame#bandeau {{
    background: {p['SURFACE_HAUTE']};
    border-bottom: 1px solid {p['OR']};
}}
QLabel#erreur {{
    color: {p['ROUGE']};
}}
QLabel#succes {{
    color: {p['VERT']};
}}
QLabel#section {{
    color: {p['TEXTE_ETEINT']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#etat {{
    color: {p['VERT']};
    font-size: 12px;
}}
QLabel#nom_carte {{
    font-family: "{POLICE_TITRES}";
    font-weight: 800;
    font-size: 19px;
    letter-spacing: 1px;
}}
QLabel#version_carte {{
    color: {p['OR_CLAIR']};
    font-size: 12px;
}}
QFrame#tuile, QFrame#carte {{
    background: {p['SURFACE']};
    border: 1px solid {p['BORDURE']};
    border-top-color: {trait_or};
    border-radius: 14px;
}}
QLabel#chiffre {{
    font-family: "{POLICE_TITRES}";
    font-weight: 800;
    font-size: 26px;
    color: {p['OR_CLAIR']};
}}
QFrame#panneau {{
    background: {p['SURFACE']};
    border: 1px solid {p['BORDURE']};
    border-top-color: {trait_or};
    border-radius: 14px;
}}
QFrame#carte_joueur {{
    background: {p['SURFACE']};
    border: 1px solid {p['BORDURE']};
    border-radius: 10px;
}}
QFrame#segments {{
    background: {p['FOND']};
    border: 1px solid {p['BORDURE']};
    border-radius: 10px;
}}
QScrollArea#defilement, QWidget#contenu_defilement {{
    background: transparent;
    border: none;
}}
QPushButton {{
    background: transparent;
    color: {p['OR_CLAIR']};
    border: 1px solid {trait_or};
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {voile_or};
    border-color: {p['OR']};
}}
QPushButton:pressed {{
    background: {voile_fort};
}}
QPushButton:disabled {{
    background: transparent;
    color: {p['TEXTE_ETEINT']};
    border-color: {p['BORDURE']};
}}
QPushButton#principal {{
    background: {degrade_or};
    color: {p['ENCRE']};
    border: 1px solid {p['OR_BAS']};
    font-weight: 700;
}}
QPushButton#principal:hover {{
    background: {degrade_or_survol};
    border-color: {p['OR']};
}}
QPushButton#principal:pressed {{
    background: {p['OR_BAS']};
}}
QPushButton#principal:disabled {{
    background: {p['SURFACE_HAUTE']};
    color: {p['TEXTE_ETEINT']};
    border-color: {p['BORDURE']};
}}
QPushButton#discret {{
    background: transparent;
    border: 1px solid transparent;
    color: {p['TEXTE_DOUX']};
}}
QPushButton#discret:hover {{
    background: {p['SURFACE_HAUTE']};
    color: {p['TEXTE']};
}}
QPushButton#danger {{
    background: transparent;
    color: {p['ROUGE']};
    border: 1px solid {rouge_trait};
}}
QPushButton#danger:hover {{
    background: {rouge_voile};
    border-color: {p['ROUGE']};
}}
QPushButton#menu {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {p['TEXTE_DOUX']};
    font-size: 14px;
    font-weight: 500;
    padding: 9px 12px 9px 20px;
    text-align: left;
}}
QPushButton#menu:hover {{
    background: {p['SURFACE']};
    color: {p['TEXTE']};
}}
QPushButton#menu:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {voile_or}, stop:1 transparent);
    color: {p['TEXTE']};
    font-weight: 700;
}}
QPushButton#menu:disabled {{
    color: {p['TEXTE_ETEINT']};
}}
QPushButton#segment {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 4px 6px;
}}
QPushButton#segment:hover {{
    background: {p['SURFACE']};
}}
QPushButton#segment:checked {{
    background: {p['SURFACE_HAUTE']};
    border-color: {trait_or};
}}
QPushButton#filtre {{
    background: {p['SURFACE']};
    border: 1px solid {p['BORDURE']};
    border-radius: 8px;
    min-height: 20px;
    padding: 6px 34px 6px 12px;
    color: {p['TEXTE_DOUX']};
    font-weight: 500;
    text-align: left;
}}
QPushButton#filtre:hover {{
    border-color: {p['TEXTE_ETEINT']};
    color: {p['TEXTE']};
}}
QPushButton#filtre[actif="true"] {{
    background: {voile_or};
    border-color: {trait_or};
    color: {p['OR_CLAIR']};
    font-weight: 700;
}}
QPushButton#lien {{
    background: transparent;
    border: none;
    padding: 4px 6px;
    color: {p['OR_CLAIR']};
    font-weight: 600;
}}
QPushButton#lien:hover {{
    text-decoration: underline;
}}
QPushButton#rond {{
    background: {p['SURFACE_HAUTE']};
    border: 1px solid {p['BORDURE']};
    border-radius: 14px;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
    padding: 0;
    color: {p['TEXTE']};
}}
QPushButton#rond:hover {{
    border-color: {p['OR']};
}}
QPushButton#rond:disabled {{
    background: transparent;
    border-color: {p['BORDURE']};
}}
QPushButton#fermer, QPushButton#icone {{
    background: transparent;
    border: none;
    border-radius: 15px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
}}
QPushButton#fermer:hover, QPushButton#icone:hover {{
    background: {p['SURFACE_HAUTE']};
}}
QLineEdit, QSpinBox, QComboBox {{
    background: {p['SURFACE']};
    border: 1px solid {p['BORDURE']};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {p['OR']};
    selection-color: {p['ENCRE']};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {p['OR']};
}}
QLineEdit#recherche {{
    min-height: 20px;
    padding: 6px 10px;
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p['BORDURE']};
    border-radius: 5px;
    background: {p['SURFACE']};
}}
QCheckBox::indicator:hover {{
    border-color: {p['OR']};
}}
QCheckBox::indicator:checked {{
    background: {degrade_or};
    border-color: {p['OR_BAS']};
    image: url("{coche}");
}}
QComboBox QAbstractItemView {{
    background: {p['MENU']};
    border: 1px solid {trait_or};
    selection-background-color: {voile_or};
    selection-color: {p['OR_CLAIR']};
}}
QListView {{
    background: transparent;
    border: none;
    outline: none;
}}
QTableView {{
    background: {p['SURFACE']};
    border: 1px solid {p['BORDURE']};
    border-radius: 10px;
    gridline-color: {p['BORDURE']};
    selection-background-color: {voile_or};
    selection-color: {p['TEXTE']};
}}
QHeaderView::section {{
    background: {p['SURFACE_HAUTE']};
    color: {p['TEXTE_DOUX']};
    border: none;
    border-bottom: 1px solid {p['BORDURE']};
    padding: 8px;
    font-weight: 700;
}}
QTabWidget::pane {{
    border: none;
}}
QTabBar::tab {{
    background: transparent;
    color: {p['TEXTE_DOUX']};
    padding: 10px 14px;
    border: none;
    border-bottom: 2px solid transparent;
    font-family: "{POLICE_TITRES}";
    font-weight: 800;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    color: {p['OR_CLAIR']};
    border-bottom: 2px solid {p['OR']};
}}
QTabBar::tab:hover {{
    color: {p['TEXTE']};
}}
QProgressBar {{
    background: {p['SURFACE']};
    border: 1px solid {p['BORDURE']};
    border-radius: 7px;
    min-height: 18px;
    text-align: center;
    color: {p['TEXTE']};
    font-weight: 600;
}}
QProgressBar::chunk {{
    background: {degrade_or};
    border-radius: 6px;
}}
QProgressBar#fine {{
    min-height: 6px;
    max-height: 6px;
    border: none;
    border-radius: 3px;
    background: {p['SURFACE_HAUTE']};
}}
QProgressBar#fine::chunk {{
    border-radius: 3px;
}}
QGroupBox {{
    border: 1px solid {p['BORDURE']};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    color: {p['OR_CLAIR']};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {p['PISTE']};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {p['OR']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {p['OR_HAUT']};
    border: 2px solid {p['FOND']};
    width: 12px;
    height: 12px;
    margin: -6px 0;
    border-radius: 8px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p['BORDURE']};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p['TEXTE_ETEINT']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0;
    background: transparent;
}}
QStatusBar {{
    background: {p['BARRE']};
    color: {p['TEXTE_DOUX']};
    border-top: 1px solid {p['BORDURE']};
}}
QToolTip {{
    background: {p['MENU']};
    color: {p['TEXTE']};
    border: 1px solid {trait_or};
    padding: 5px 8px;
}}
QMenu {{
    background: {p['MENU']};
    border: 1px solid {trait_or};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 22px 8px 12px;
    border-radius: 7px;
    color: {p['TEXTE']};
}}
QMenu::item:selected {{
    background: {voile_or};
    color: {p['OR_CLAIR']};
}}
QMenu::item:disabled {{
    color: {p['TEXTE_ETEINT']};
}}
QMenu::icon {{
    padding-left: 10px;
}}
QMenu::separator {{
    height: 1px;
    background: {p['BORDURE']};
    margin: 5px 8px;
}}
QMenu::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {p['BORDURE']};
    border-radius: 4px;
    background: {p['SURFACE_HAUTE']};
    margin-left: 8px;
}}
QMenu::indicator:checked {{
    background: {degrade_or};
    border-color: {p['OR_BAS']};
    image: url("{coche}");
}}
QMenu#popover {{
    border-radius: 14px;
    padding: 14px;
}}
"""


def creer_menu(parent=None):
    menu = QMenu(parent)
    menu.setWindowFlags(
        menu.windowFlags()
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.NoDropShadowWindowHint
    )
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    return menu
