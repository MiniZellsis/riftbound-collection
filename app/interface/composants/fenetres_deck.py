from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout

from app.donnees.decks import NOM_MAX, NOMS_ZONES, ZONES, totaux
from app.donnees.import_deck import lire
from app.interface import theme
from app.interface.composants.fenetres_classeur import FenetreDialogue, libelle

INCONNUES_MONTREES = 6


class FenetreNomDeck(FenetreDialogue):
    def __init__(self, titre, sous_titre, texte_bouton, nom="", parent=None):
        super().__init__(titre, sous_titre, texte_bouton, parent)
        self.nom = QLineEdit(nom)
        self.nom.setPlaceholderText("Ex. Jinx agressif")
        self.nom.setMaxLength(NOM_MAX)
        self.contenu.addWidget(libelle("Nom du deck"))
        self.contenu.addWidget(self.nom)
        self.setMinimumWidth(460)
        self.nom.selectAll()
        self.nom.setFocus()

    def valider(self):
        if not self.nom.text().strip():
            self.montrer_erreur("Donne un nom au deck.")
            return
        self.accept()

    def resultat(self):
        return self.nom.text().strip()


class FenetreImportDeck(FenetreDialogue):
    def __init__(self, decks, parent=None):
        super().__init__(
            "Importer un deck",
            "Colle la liste copiée depuis un site de decks (Piltover Archive, les « Top Decks » de Riot…) "
            "ou un code de deck. Le nouveau deck sera créé avec ces cartes.",
            "Importer",
            parent,
        )
        self.decks = decks
        self.lecture = None
        self.nom_touche = False

        self.nom = QLineEdit("")
        self.nom.setPlaceholderText("Nom du deck")
        self.nom.setMaxLength(NOM_MAX)
        self.nom.textEdited.connect(self.nom_modifie)
        self.texte = QPlainTextEdit()
        self.texte.setObjectName("liste_deck")
        self.texte.setPlaceholderText(
            "Legend:\n1 Jinx, Loose Cannon\n\nChampion:\n1 Jinx, Demolitionist\n\nMain Deck:\n3 …\n\n"
            "Battlefields:\n1 …\n\nRune Pool:\n6 Fury Rune\n6 Chaos Rune"
        )
        police = QFont("Consolas")
        police.setStyleHint(QFont.StyleHint.Monospace)
        police.setPixelSize(13)
        self.texte.setFont(police)
        self.texte.setMinimumHeight(240)

        self.resume = QLabel("")
        self.resume.setWordWrap(True)
        self.resume.setMinimumHeight(self.resume.fontMetrics().lineSpacing() * 4 + 6)
        cadre = QFrame()
        cadre.setObjectName("resume_remplir")
        disposition = QVBoxLayout(cadre)
        disposition.setContentsMargins(14, 10, 14, 10)
        disposition.addWidget(self.resume)

        self.contenu.addWidget(libelle("Nom du deck"))
        self.contenu.addWidget(self.nom)
        self.contenu.addSpacing(4)
        self.contenu.addWidget(libelle("Liste ou code"))
        self.contenu.addWidget(self.texte, stretch=1)
        self.contenu.addWidget(cadre)

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(250)
        self.minuteur.timeout.connect(self.analyser)
        self.texte.textChanged.connect(self.minuteur.start)
        self.resize(640, 680)
        self.analyser()
        self.texte.setFocus()

    def nom_modifie(self):
        self.nom_touche = True

    def analyser(self):
        texte = self.texte.toPlainText().strip()
        self.montrer_erreur("")
        if not texte:
            self.lecture = None
            self.resume.setText("Colle une liste pour voir ce qui sera importé.")
            self.bouton_valider.setEnabled(False)
            return
        self.lecture = lire(texte, self.decks)
        if self.lecture.erreur:
            self.resume.setText(f'<span style="color:{theme.ROUGE}">{self.lecture.erreur}</span>')
            self.bouton_valider.setEnabled(False)
            return
        nombres = totaux(self.lecture.contenu)
        cartes = self.decks.cartes()
        legende = next((cartes[carte_id] for zone, carte_id in self.lecture.contenu if zone == "legende"), None)
        if legende is not None and not self.nom_touche:
            self.nom.setText(legende["nom"])
        morceaux = []
        for zone in ZONES:
            if zone == "principal":
                morceaux.append(f"{NOMS_ZONES[zone]} : <b>{nombres['principal'] + nombres['champion']}</b>")
            elif zone not in ("legende", "champion") and nombres[zone]:
                morceaux.append(f"{NOMS_ZONES[zone]} : <b>{nombres[zone]}</b>")
        if legende is not None:
            lignes = [f"Légende : <b>{legende['nom']}</b>"]
        else:
            lignes = ["Pas de légende dans cette liste : tu pourras la choisir après."]
        lignes.append("  ·  ".join(morceaux))
        inconnues = self.lecture.inconnues
        if inconnues:
            exemples = ", ".join(f"« {ligne} »" for ligne in inconnues[:INCONNUES_MONTREES])
            reste = len(inconnues) - INCONNUES_MONTREES
            if reste > 0:
                exemples += f" et {reste} autre{'s' if reste > 1 else ''}"
            lignes.append(
                f'<span style="color:{theme.ROUGE}">{len(inconnues)} ligne{"s" if len(inconnues) > 1 else ""} '
                f"pas reconnue{'s' if len(inconnues) > 1 else ''} : {exemples}. "
                "Si une carte récente manque, mets à jour le catalogue dans Réglages.</span>"
            )
        self.resume.setText("<br>".join(lignes))
        self.bouton_valider.setEnabled(bool(self.lecture.contenu))

    def valider(self):
        self.minuteur.stop()
        self.analyser()
        if self.lecture is None or not self.lecture.contenu:
            return
        if not self.nom.text().strip():
            self.montrer_erreur("Donne un nom au deck.")
            return
        self.accept()

    def resultat(self):
        return self.nom.text().strip(), dict(self.lecture.contenu)
