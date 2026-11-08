from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QImage
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import catalogue, supabase_client, theme
from app.barre_filtres import DOMAINES, RARETES
from app.collection import version_vide
from app.image_carte import ImageCarte
from app.images import (
    DELAI_MAX,
    LARGEUR_GRANDE,
    arrondir,
    fichier_grand,
    fichier_icone,
    fichier_miniature,
    url_redimensionnee,
)

COULEURS = dict(DOMAINES + RARETES)
DELAI_SAUVEGARDE = 700


class Compteur(QWidget):
    change = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.valeur = 0
        self.moins = QPushButton("−")
        self.plus = QPushButton("+")
        for bouton in (self.moins, self.plus):
            bouton.setObjectName("rond")
            bouton.setCursor(Qt.CursorShape.PointingHandCursor)
            bouton.setAutoRepeat(True)
        self.texte = QLabel("0")
        self.texte.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texte.setFixedWidth(26)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.moins)
        layout.addWidget(self.texte)
        layout.addWidget(self.plus)

        self.moins.clicked.connect(self.diminuer)
        self.plus.clicked.connect(self.augmenter)

    def diminuer(self):
        self.change.emit(self.valeur - 1)

    def augmenter(self):
        self.change.emit(self.valeur + 1)

    def definir(self, valeur, maximum):
        self.valeur = valeur
        self.texte.setText(str(valeur))
        self.moins.setEnabled(valeur > 0)
        self.plus.setEnabled(valeur < maximum)


class PanneauCarte(QFrame):
    ferme = Signal()
    modifiee = Signal(str)

    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.setObjectName("panneau")
        self.setFixedWidth(360)
        self.collection = collection
        self.carte = None
        self.seule_foil = False
        self.versions = {}
        self.compteurs = {}
        self.cases = {}
        self.lignes = {}
        self.reseau = QNetworkAccessManager(self)
        self.reponse = None

        bouton_fermer = QPushButton("×")
        bouton_fermer.setObjectName("fermer")
        bouton_fermer.setCursor(Qt.CursorShape.PointingHandCursor)
        bouton_fermer.setToolTip("Fermer (Échap)")
        bouton_fermer.clicked.connect(self.ferme)
        haut = QHBoxLayout()
        haut.addStretch()
        haut.addWidget(bouton_fermer)

        self.image = ImageCarte()
        self.nom = QLabel("")
        self.nom.setObjectName("nom_carte")
        self.nom.setWordWrap(True)
        self.details = QLabel("")
        self.details.setObjectName("sous_titre")
        self.details.setWordWrap(True)
        self.version = QLabel("")
        self.version.setObjectName("version_carte")

        section = QLabel("MA COLLECTION")
        section.setObjectName("section")
        self.etat = QLabel("")
        self.etat.setObjectName("etat")
        ligne_section = QHBoxLayout()
        ligne_section.addWidget(section)
        ligne_section.addStretch()
        ligne_section.addWidget(self.etat)

        tableau = QGridLayout()
        tableau.setHorizontalSpacing(10)
        tableau.setVerticalSpacing(8)
        for colonne, texte in enumerate(["Possédées", "À échanger", "Recherchée"], start=1):
            entete = QLabel(texte)
            entete.setObjectName("sous_titre")
            tableau.addWidget(entete, 0, colonne, alignment=Qt.AlignmentFlag.AlignCenter)
        self.creer_ligne(tableau, 1, False, "Normale")
        self.creer_ligne(tableau, 2, True, "Foil")

        self.info_foil = QLabel("Cette carte n'existe qu'en foil.")
        self.info_foil.setObjectName("sous_titre")
        self.info_foil.hide()

        self.message = QLabel("")
        self.message.setObjectName("erreur")
        self.message.setWordWrap(True)
        self.message.hide()

        self.bouton_prix = QPushButton("Voir le prix sur TCGplayer")
        self.bouton_prix.clicked.connect(self.ouvrir_tcgplayer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 16)
        layout.setSpacing(6)
        layout.addLayout(haut)
        layout.addWidget(self.image, stretch=1)
        layout.addSpacing(4)
        layout.addWidget(self.nom)
        layout.addWidget(self.details)
        layout.addWidget(self.version)
        layout.addSpacing(10)
        layout.addLayout(ligne_section)
        layout.addLayout(tableau)
        layout.addWidget(self.info_foil)
        layout.addWidget(self.message)
        layout.addSpacing(8)
        layout.addWidget(self.bouton_prix)

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(DELAI_SAUVEGARDE)
        self.minuteur.timeout.connect(self.enregistrer)

        self.minuteur_etat = QTimer(self)
        self.minuteur_etat.setSingleShot(True)
        self.minuteur_etat.setInterval(2500)
        self.minuteur_etat.timeout.connect(self.etat.clear)

    def creer_ligne(self, tableau, ligne, foil, texte):
        quantite = Compteur()
        a_echanger = Compteur()
        recherche = QCheckBox()
        quantite.change.connect(lambda valeur: self.changer(foil, "quantite", valeur))
        a_echanger.change.connect(lambda valeur: self.changer(foil, "a_echanger", valeur))
        recherche.toggled.connect(lambda coche: self.changer(foil, "recherche", coche))

        libelle = QLabel(texte)
        tableau.addWidget(libelle, ligne, 0)
        tableau.addWidget(quantite, ligne, 1)
        tableau.addWidget(a_echanger, ligne, 2)
        tableau.addWidget(recherche, ligne, 3, alignment=Qt.AlignmentFlag.AlignCenter)
        self.compteurs[foil] = (quantite, a_echanger)
        self.cases[foil] = recherche
        self.lignes[foil] = (libelle, quantite, a_echanger, recherche)

    def afficher(self, carte_id):
        if self.carte is not None and self.carte["carte_id"] == carte_id:
            return
        self.enregistrer_maintenant()
        self.carte = catalogue.lire_carte(carte_id)
        self.seule_foil = catalogue.toujours_foil(self.carte)
        self.nom.setText(self.carte["nom"])
        self.details.setText(self.texte_details())
        self.version.setText(self.texte_version())
        self.version.setVisible(bool(self.version.text()))
        self.bouton_prix.setEnabled(bool(self.carte["tcgplayer_id"]))
        self.etat.clear()
        self.message.hide()
        self.recharger()
        self.charger_image()

    def texte_details(self):
        carte = self.carte
        morceaux = [
            carte["set_nom"] or "-",
            f"n°{carte['numero']}",
            self.avec_icone(carte["rarete"] or "-"),
            carte["type"] or "-",
        ]
        domaines = [self.avec_icone(domaine) for domaine in (carte["domaines"] or "").split(", ") if domaine]
        return " · ".join(morceaux) + "<br>" + "&nbsp;&nbsp;&nbsp;".join(domaines)

    def avec_icone(self, nom):
        fichier = fichier_icone(nom)
        if fichier.exists():
            adresse = QUrl.fromLocalFile(fichier.as_posix()).toString()
            return f'<img src="{adresse}" height="16" style="vertical-align: middle"> {nom}'
        couleur = COULEURS.get(nom, theme.TEXTE_DOUX)
        return f'<span style="color:{couleur}">●</span> {nom}'

    def texte_version(self):
        versions = []
        if self.carte["art_alternatif"]:
            versions.append("Art alternatif")
        if self.carte["signature"]:
            versions.append("Signature")
        if self.carte["surnumerotee"]:
            versions.append("Surnumérotée")
        return " · ".join(versions)

    def recharger(self):
        if self.carte is None:
            return
        carte_id = self.carte["carte_id"]
        self.versions = {
            False: dict(self.collection.version(carte_id, False)),
            True: dict(self.collection.version(carte_id, True)),
        }
        normale_visible = not self.seule_foil or not version_vide(self.versions[False])
        for widget in self.lignes[False]:
            widget.setVisible(normale_visible)
        self.info_foil.setVisible(self.seule_foil)
        self.afficher_valeurs()
        if not self.collection.chargee:
            self.message.setText("Collection indisponible : vérifie ta connexion, puis reconnecte-toi.")
            self.message.show()

    def afficher_valeurs(self):
        for foil, (quantite, a_echanger) in self.compteurs.items():
            version = self.versions[foil]
            quantite.definir(version["quantite"], 99)
            a_echanger.definir(version["a_echanger"], version["quantite"])
            case = self.cases[foil]
            case.blockSignals(True)
            case.setChecked(version["recherche"])
            case.blockSignals(False)
            for controle in (quantite, a_echanger, case):
                controle.setEnabled(self.collection.chargee)
        self.image.definir_foil(self.seule_foil or self.versions[True]["quantite"] > 0)

    def changer(self, foil, champ, valeur):
        version = self.versions[foil]
        version[champ] = valeur
        version["a_echanger"] = min(version["a_echanger"], version["quantite"])
        self.afficher_valeurs()
        self.etat.clear()
        self.minuteur.start()

    def enregistrer_maintenant(self):
        if self.minuteur.isActive():
            self.minuteur.stop()
            self.enregistrer()

    def enregistrer(self):
        carte_id = self.carte["carte_id"]
        versions = [self.versions[False], self.versions[True]]
        if versions == [self.collection.version(carte_id, False), self.collection.version(carte_id, True)]:
            return
        self.etat.setText("Enregistrement…")
        self.etat.repaint()
        try:
            self.collection.enregistrer(carte_id, versions)
        except supabase_client.ErreurSupabase as erreur:
            self.etat.clear()
            self.message.setText(f"Pas enregistré : {erreur}")
            self.message.show()
            self.recharger()
            return
        self.message.hide()
        self.etat.setText("✓ Enregistré")
        self.minuteur_etat.start()
        self.modifiee.emit(carte_id)

    def ouvrir_tcgplayer(self):
        url = f"https://www.tcgplayer.com/product/{self.carte['tcgplayer_id']}"
        QDesktopServices.openUrl(QUrl(url))

    def charger_image(self):
        if self.reponse is not None:
            self.reponse.abort()
        url = self.carte["image_url"]
        if not url:
            self.image.definir(None)
            return
        if fichier_grand(url).exists():
            self.image.definir(QImage(str(fichier_grand(url))))
            return

        miniature = QImage(str(fichier_miniature(url)))
        self.image.definir(None if miniature.isNull() else arrondir(miniature))
        requete = QNetworkRequest(url_redimensionnee(url, LARGEUR_GRANDE, "webp"))
        requete.setTransferTimeout(DELAI_MAX)
        reponse = self.reseau.get(requete)
        self.reponse = reponse
        reponse.finished.connect(lambda: self.image_recue(reponse, url))

    def image_recue(self, reponse, url):
        reponse.deleteLater()
        if reponse is self.reponse:
            self.reponse = None
        if reponse.error() != QNetworkReply.NetworkError.NoError:
            return
        donnees = reponse.readAll()
        image = QImage()
        if image.loadFromData(donnees):
            fichier_grand(url).write_bytes(bytes(donnees))
            if self.carte is not None and self.carte["image_url"] == url:
                self.image.definir(image)
