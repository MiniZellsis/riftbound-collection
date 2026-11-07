from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QMenu

FOND = "#0b1220"
SURFACE = "#121b2e"
SURFACE_HAUTE = "#1a2540"
BARRE = "#0e1628"
BORDURE = "#263352"
TEXTE = "#e8ecf4"
TEXTE_DOUX = "#8f9bb3"
TEXTE_ETEINT = "#56607a"
OR = "#c9a44c"
OR_CLAIR = "#e3c06a"
ROUGE = "#e5534b"
VERT = "#3fb950"

STYLE = f"""
QWidget {{
    color: {TEXTE};
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background: {FOND};
}}
QWidget#barre_laterale {{
    background: {BARRE};
    border-right: 1px solid {BORDURE};
}}
QLabel#logo {{
    color: {OR_CLAIR};
    font-size: 18px;
    font-weight: bold;
    letter-spacing: 3px;
    padding: 18px 16px 24px 16px;
}}
QLabel#titre {{
    font-size: 22px;
    font-weight: bold;
}}
QLabel#sous_titre {{
    color: {TEXTE_DOUX};
}}
QLabel#erreur {{
    color: {ROUGE};
}}
QLabel#pseudo {{
    color: {TEXTE};
    font-weight: bold;
    padding: 0 20px;
}}
QLabel#section {{
    color: {TEXTE_ETEINT};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}
QLabel#etat {{
    color: {VERT};
    font-size: 12px;
}}
QLabel#nom_carte {{
    font-size: 20px;
    font-weight: bold;
}}
QLabel#version_carte {{
    color: {OR_CLAIR};
    font-size: 12px;
}}
QFrame#tuile {{
    background: {SURFACE};
    border: 1px solid {BORDURE};
    border-radius: 10px;
}}
QLabel#chiffre {{
    color: {OR_CLAIR};
    font-size: 26px;
    font-weight: bold;
}}
QFrame#panneau {{
    background: {SURFACE};
    border: 1px solid {BORDURE};
    border-radius: 14px;
}}
QPushButton {{
    background: {SURFACE_HAUTE};
    border: 1px solid {BORDURE};
    border-radius: 6px;
    padding: 7px 14px;
}}
QPushButton:hover {{
    border-color: {OR};
}}
QPushButton:pressed {{
    background: {SURFACE};
}}
QPushButton:disabled {{
    color: {TEXTE_ETEINT};
    border-color: {SURFACE_HAUTE};
}}
QPushButton#principal {{
    background: {OR};
    color: {FOND};
    border: none;
    font-weight: bold;
}}
QPushButton#principal:hover {{
    background: {OR_CLAIR};
}}
QPushButton#menu {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {TEXTE_DOUX};
    font-size: 14px;
    padding: 10px 16px;
    margin: 0 8px;
    text-align: left;
}}
QPushButton#menu:hover {{
    background: {SURFACE};
    color: {TEXTE};
}}
QPushButton#menu:checked {{
    background: {SURFACE_HAUTE};
    color: {OR_CLAIR};
    font-weight: bold;
}}
QPushButton#menu:disabled {{
    color: {TEXTE_ETEINT};
}}
QPushButton#discret {{
    background: transparent;
    border: none;
    color: {TEXTE_DOUX};
    text-align: left;
    padding: 6px 16px;
    margin: 0 8px;
}}
QPushButton#discret:hover {{
    color: {ROUGE};
}}
QPushButton#filtre {{
    background: {SURFACE};
    border: 1px solid {BORDURE};
    border-radius: 16px;
    min-height: 20px;
    padding: 5px 34px 5px 14px;
    color: {TEXTE_DOUX};
    text-align: left;
}}
QPushButton#filtre:hover {{
    border-color: {TEXTE_ETEINT};
    color: {TEXTE};
}}
QPushButton#filtre[actif="true"] {{
    background: rgba(201, 164, 76, 30);
    border-color: {OR};
    color: {OR_CLAIR};
}}
QPushButton#lien {{
    background: transparent;
    border: none;
    padding: 4px 6px;
    color: {OR};
}}
QPushButton#lien:hover {{
    color: {OR_CLAIR};
    text-decoration: underline;
}}
QPushButton#rond {{
    background: {SURFACE_HAUTE};
    border: none;
    border-radius: 13px;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
    padding: 0;
    font-size: 15px;
    font-weight: bold;
}}
QPushButton#rond:hover {{
    background: {OR};
    color: {FOND};
}}
QPushButton#rond:disabled {{
    background: transparent;
    color: {TEXTE_ETEINT};
}}
QPushButton#fermer {{
    background: transparent;
    border: none;
    border-radius: 15px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
    font-size: 18px;
    color: {TEXTE_DOUX};
}}
QPushButton#fermer:hover {{
    background: {SURFACE_HAUTE};
    color: {TEXTE};
}}
QLineEdit, QSpinBox, QComboBox {{
    background: {SURFACE};
    border: 1px solid {BORDURE};
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: {OR};
    selection-color: {FOND};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {OR};
}}
QLineEdit#recherche {{
    border-radius: 16px;
    min-height: 20px;
    padding: 5px 12px;
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDURE};
    border-radius: 4px;
    background: {SURFACE};
}}
QCheckBox::indicator:hover {{
    border-color: {OR};
}}
QCheckBox::indicator:checked {{
    background: {OR};
    border-color: {OR};
}}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDURE};
    selection-background-color: {SURFACE_HAUTE};
    selection-color: {OR_CLAIR};
}}
QListView {{
    background: transparent;
    border: none;
    outline: none;
}}
QTableView {{
    background: {FOND};
    border: 1px solid {BORDURE};
    border-radius: 8px;
    gridline-color: {BORDURE};
    selection-background-color: {SURFACE_HAUTE};
    selection-color: {OR_CLAIR};
}}
QHeaderView::section {{
    background: {SURFACE};
    color: {TEXTE_DOUX};
    border: none;
    border-bottom: 1px solid {BORDURE};
    padding: 6px;
}}
QTabWidget::pane {{
    border: none;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXTE_DOUX};
    padding: 8px 16px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {OR_CLAIR};
    border-bottom-color: {OR};
}}
QTabBar::tab:hover {{
    color: {TEXTE};
}}
QProgressBar {{
    background: {SURFACE};
    border: 1px solid {BORDURE};
    border-radius: 6px;
    min-height: 18px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {OR};
    border-radius: 5px;
}}
QProgressBar#fine {{
    min-height: 6px;
    max-height: 6px;
    border: none;
    border-radius: 3px;
    background: {SURFACE_HAUTE};
}}
QProgressBar#fine::chunk {{
    border-radius: 3px;
}}
QGroupBox {{
    border: 1px solid {BORDURE};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    color: {OR_CLAIR};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {SURFACE_HAUTE};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {OR};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {OR_CLAIR};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDURE};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #3a4a70;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0;
    background: transparent;
}}
QStatusBar {{
    background: {BARRE};
    color: {TEXTE_DOUX};
    border-top: 1px solid {BORDURE};
}}
QToolTip {{
    background: {SURFACE_HAUTE};
    color: {TEXTE};
    border: 1px solid {OR};
    padding: 4px;
}}
QMenu {{
    background: {SURFACE};
    border: 1px solid {BORDURE};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 18px 7px 12px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background: {SURFACE_HAUTE};
    color: {OR_CLAIR};
}}
QMenu::item:disabled {{
    color: {TEXTE_ETEINT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDURE};
    margin: 5px 8px;
}}
QMenu::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDURE};
    border-radius: 4px;
    background: {SURFACE_HAUTE};
    margin-left: 8px;
}}
QMenu::indicator:checked {{
    background: {OR};
    border-color: {OR};
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


def appliquer_theme(application):
    application.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(FOND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXTE))
    palette.setColor(QPalette.ColorRole.Base, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE_HAUTE))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXTE))
    palette.setColor(QPalette.ColorRole.Button, QColor(SURFACE_HAUTE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXTE))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(OR))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(FOND))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(SURFACE_HAUTE))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXTE))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXTE_ETEINT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(TEXTE_ETEINT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(TEXTE_ETEINT))
    application.setPalette(palette)

    application.setStyleSheet(STYLE)
