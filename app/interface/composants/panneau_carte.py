from PySide6.QtCore import QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.donnees import catalogue
from app.donnees.collection import version_vide
from app.donnees.images import (
    DELAI_MAX,
    LARGEUR_GRANDE,
    arrondir,
    fichier_grand,
    fichier_icone,
    fichier_miniature,
    url_redimensionnee,
)
from app.interface import icones, theme
from app.interface.composants.elements import Filet, Flux, Interrupteur, Statut, Titre
from app.interface.composants.image_carte import ImageCarte

COULEURS = dict(theme.DOMAINES + theme.RARETES)
DELAI_SAUVEGARDE = 700
LARGEUR = 372
HAUTEUR_LIGNE = 24


def image_icone(nom, ratio):
    fichier = fichier_icone(nom)
    image = QPixmap(str(fichier)) if fichier.exists() else QPixmap()
    if not image.isNull():
        image = image.scaledToHeight(round(15 * ratio), Qt.TransformationMode.SmoothTransformation)
        image.setDevicePixelRatio(ratio)
        return image
    image = QPixmap(round(10 * ratio), round(10 * ratio))
    image.setDevicePixelRatio(ratio)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor(COULEURS.get(nom, theme.TEXTE_DOUX)))
    peintre.drawEllipse(QRectF(1, 1, 8, 8))
    peintre.end()
    return image


def etiquette(nom, texte=""):
    element = QLabel(texte)
    element.setObjectName(nom)
    element.setFixedHeight(HAUTEUR_LIGNE)
    return element


class Info(QFrame):
    def __init__(self, nom, parent=None):
        super().__init__(parent)
        self.setObjectName(nom)
        self.setFixedHeight(HAUTEUR_LIGNE)
        self.icone = QLabel()
        self.texte = QLabel()
        layout = QHBoxLayout(self)
        marge = 10 if nom == "puce_domaine" else 0
        layout.setContentsMargins(marge, 0, marge, 0)
        layout.setSpacing(6)
        layout.addWidget(self.icone)
        layout.addWidget(self.texte)

    def definir(self, texte):
        self.texte.setText(texte)
        self.icone.setPixmap(image_icone(texte, self.devicePixelRatioF()) if texte else QPixmap())
        self.setVisible(bool(texte))


class Compteur(QWidget):
    change = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.valeur = 0
        self.moins = QPushButton("")
        self.moins.setObjectName("rond")
        icones.lier(self.moins, "minus", 13, "TEXTE", "TEXTE")
        self.plus = QPushButton("")
        self.plus.setObjectName("rond_or")
        icones.lier(self.plus, "plus", 13, "OR_CLAIR", "OR_CLAIR")
        for bouton in (self.moins, self.plus):
            bouton.setCursor(Qt.CursorShape.PointingHandCursor)
            bouton.setAutoRepeat(True)
        self.texte = QLabel("0")
        self.texte.setObjectName("nombre_compteur")
        self.texte.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texte.setFixedWidth(24)

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
        self.setFixedWidth(LARGEUR)
        self.collection = collection
        self.carte = None
        self.seule_foil = False
        self.versions = {}
        self.compteurs = {}
        self.interrupteurs = {}
        self.lignes = {}
        self.reseau = QNetworkAccessManager(self)
        self.reponse = None

        self.code = QLabel("")
        self.code.setObjectName("code_carte")
        bouton_fermer = QPushButton("")
        bouton_fermer.setObjectName("fermer")
        icones.lier(bouton_fermer, "x", 17, "TEXTE_DOUX", "TEXTE")
        bouton_fermer.setCursor(Qt.CursorShape.PointingHandCursor)
        bouton_fermer.setToolTip("Fermer (Échap)")
        bouton_fermer.clicked.connect(self.ferme)
        haut = QHBoxLayout()
        haut.addWidget(self.code)
        haut.addStretch()
        haut.addWidget(bouton_fermer)

        self.image = ImageCarte()
        self.nom = QLabel("")
        self.nom.setObjectName("nom_carte")
        self.nom.setWordWrap(True)

        self.rarete = Info("meta_carte")
        self.separateur_type = etiquette("meta_sep", "·")
        self.type = etiquette("meta_carte")
        self.separateur_domaines = etiquette("meta_sep", "·")
        self.domaines = [Info("puce_domaine") for _ in range(3)]
        self.version = etiquette("puce_version")
        meta = Flux(8, 6)
        for element in (self.rarete, self.separateur_type, self.type, self.separateur_domaines, *self.domaines, self.version):
            meta.addWidget(element)

        section = QHBoxLayout()
        section.setSpacing(10)
        section.addWidget(Titre("Dans ma collection", "titre_section"))
        section.addWidget(Filet(), stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

        tableau = QGridLayout()
        tableau.setHorizontalSpacing(8)
        tableau.setVerticalSpacing(6)
        tableau.setColumnStretch(0, 1)
        for colonne, texte in enumerate(["Exemplaires", "À l'échange", "Recherchée"], start=1):
            entete = QLabel(texte)
            entete.setObjectName("entete_tableau")
            tableau.addWidget(entete, 0, colonne, alignment=Qt.AlignmentFlag.AlignCenter)
        self.creer_ligne(tableau, 1, False, "Normale", None)
        self.creer_ligne(tableau, 2, True, "Foil", "sparkles")

        self.info_foil = QLabel("Cette carte n'existe qu'en foil.")
        self.info_foil.setObjectName("aide")
        self.info_foil.hide()

        self.statut = Statut()
        self.message = QLabel("")
        self.message.setObjectName("erreur")
        self.message.setWordWrap(True)
        self.message.hide()

        self.bouton_prix = QPushButton("Voir le prix sur TCGplayer")
        self.bouton_prix.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_prix.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        icones.lier(self.bouton_prix, "external-link", 15, "OR_CLAIR", "OR_CLAIR")
        self.bouton_prix.clicked.connect(self.ouvrir_tcgplayer)

        contenu = QWidget()
        contenu.setObjectName("contenu_defilement")
        layout = QVBoxLayout(contenu)
        layout.setContentsMargins(20, 6, 16, 12)
        layout.setSpacing(12)
        layout.addLayout(haut)
        layout.addWidget(self.image, stretch=1)
        layout.addWidget(self.nom)
        layout.addLayout(meta)
        layout.addSpacing(4)
        layout.addLayout(section)
        layout.addLayout(tableau)
        layout.addWidget(self.info_foil)
        layout.addWidget(self.statut)
        layout.addWidget(self.message)
        layout.addStretch()
        layout.addWidget(self.bouton_prix)

        defilement = QScrollArea()
        defilement.setObjectName("defilement")
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QScrollArea.Shape.NoFrame)
        defilement.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        defilement.viewport().setAutoFillBackground(False)
        defilement.setWidget(contenu)

        cadre = QVBoxLayout(self)
        cadre.setContentsMargins(0, 8, 4, 8)
        cadre.addWidget(defilement)

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(DELAI_SAUVEGARDE)
        self.minuteur.timeout.connect(self.enregistrer)

        self.minuteur_etat = QTimer(self)
        self.minuteur_etat.setSingleShot(True)
        self.minuteur_etat.setInterval(2500)
        self.minuteur_etat.timeout.connect(self.effacer_statut)

        self.collection.envoi_reussi.connect(self.envoi_reussi)
        self.collection.envoi_echoue.connect(self.envoi_echoue)

    def creer_ligne(self, tableau, ligne, foil, texte, nom_icone):
        quantite = Compteur()
        a_echanger = Compteur()
        recherche = Interrupteur()
        quantite.change.connect(lambda valeur: self.changer(foil, "quantite", valeur))
        a_echanger.change.connect(lambda valeur: self.changer(foil, "a_echanger", valeur))
        recherche.toggled.connect(lambda coche: self.changer(foil, "recherche", coche))

        libelle = QWidget()
        disposition = QHBoxLayout(libelle)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(6)
        if nom_icone:
            icone = QLabel()
            icones.lier_image(icone, nom_icone, 15, "OR_CLAIR")
            disposition.addWidget(icone)
        nom = QLabel(texte)
        nom.setObjectName("libelle_ligne")
        disposition.addWidget(nom)
        disposition.addStretch()

        tableau.addWidget(libelle, ligne, 0)
        tableau.addWidget(quantite, ligne, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        tableau.addWidget(a_echanger, ligne, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        tableau.addWidget(recherche, ligne, 3, alignment=Qt.AlignmentFlag.AlignCenter)
        self.compteurs[foil] = (quantite, a_echanger)
        self.interrupteurs[foil] = recherche
        self.lignes[foil] = (libelle, quantite, a_echanger, recherche)

    def afficher(self, carte_id):
        if self.carte is not None and self.carte["carte_id"] == carte_id:
            return
        self.enregistrer_maintenant()
        self.carte = catalogue.lire_carte(carte_id)
        self.seule_foil = catalogue.toujours_foil(self.carte)
        self.code.setText(catalogue.code_affiche(self.carte, True))
        self.nom.setText(self.carte["nom"].upper())
        self.afficher_meta()
        self.bouton_prix.setEnabled(bool(self.carte["tcgplayer_id"]))
        self.effacer_statut()
        self.message.hide()
        self.recharger()
        self.charger_image()

    def afficher_meta(self):
        carte = self.carte
        rarete = carte["rarete"] or ""
        type_carte = carte["type"] or ""
        domaines = [domaine for domaine in (carte["domaines"] or "").split(", ") if domaine]
        self.rarete.definir(rarete)
        self.type.setText(type_carte)
        self.type.setVisible(bool(type_carte))
        self.separateur_type.setVisible(bool(rarete and type_carte))
        self.separateur_domaines.setVisible(bool(domaines) and bool(rarete or type_carte))
        for position, element in enumerate(self.domaines):
            element.definir(domaines[position] if position < len(domaines) else "")
        version = self.texte_version()
        self.version.setText(version)
        self.version.setVisible(bool(version))

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
            interrupteur = self.interrupteurs[foil]
            if interrupteur.isChecked() != version["recherche"]:
                interrupteur.definir(version["recherche"])
            for controle in (quantite, a_echanger, interrupteur):
                controle.setEnabled(self.collection.chargee)
        self.image.definir_foil(self.seule_foil or self.versions[True]["quantite"] > 0)

    def changer(self, foil, champ, valeur):
        version = self.versions[foil]
        version[champ] = valeur
        version["a_echanger"] = min(version["a_echanger"], version["quantite"])
        self.afficher_valeurs()
        self.effacer_statut()
        self.minuteur.start()

    def effacer_statut(self):
        self.minuteur_etat.stop()
        self.statut.definir(None)

    def enregistrer_maintenant(self):
        if self.minuteur.isActive():
            self.minuteur.stop()
            self.enregistrer()

    def enregistrer(self):
        carte_id = self.carte["carte_id"]
        if not self.collection.enregistrer(carte_id, [self.versions[False], self.versions[True]]):
            return
        self.message.hide()
        self.minuteur_etat.stop()
        self.statut.definir("envoi", "Enregistrement…")
        self.modifiee.emit(carte_id)

    def montre(self, carte_id):
        return self.carte is not None and self.carte["carte_id"] == carte_id

    def envoi_reussi(self, carte_id):
        if self.montre(carte_id) and self.statut.etat == "envoi":
            self.statut.definir("ok", "Enregistré")
            self.minuteur_etat.start()

    def envoi_echoue(self, carte_id, erreur):
        if not self.montre(carte_id):
            return
        self.effacer_statut()
        self.message.setText(f"Pas enregistré : {erreur}")
        self.message.show()
        if not self.minuteur.isActive():
            self.recharger()

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
