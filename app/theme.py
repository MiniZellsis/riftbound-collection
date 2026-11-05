from PySide6.QtGui import QColor, QPalette

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
    background: {FOND};
    color: {TEXTE};
    font-size: 13px;
}}
QWidget#barre_laterale {{
    background: {BARRE};
    border-right: 1px solid {BORDURE};
}}
QWidget#barre_laterale QLabel {{
    background: transparent;
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
QFrame#tuile {{
    background: {SURFACE};
    border: 1px solid {BORDURE};
    border-radius: 10px;
}}
QFrame#tuile QLabel {{
    background: transparent;
}}
QLabel#chiffre {{
    color: {OR_CLAIR};
    font-size: 26px;
    font-weight: bold;
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
    background: {FOND};
    border: none;
    outline: none;
}}
QListView::item:selected {{
    background: {SURFACE_HAUTE};
    border-radius: 8px;
    color: {OR_CLAIR};
}}
QListView::item:hover {{
    background: {SURFACE};
    border-radius: 8px;
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
QStatusBar QLabel {{
    background: transparent;
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
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {SURFACE_HAUTE};
    color: {OR_CLAIR};
}}
"""


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