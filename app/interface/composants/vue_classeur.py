import time

from PySide6.QtCore import QByteArray, QEvent, QMimeData, QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QFont, QFontMetrics, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton, QToolTip, QWidget

from app.donnees import catalogue
from app.donnees.classeurs import contenu_pile, decrire_position, par_page, quantites
from app.donnees.decks import normaliser
from app.donnees.images import ARRONDI, charger_miniature
from app.interface import icones, theme
from app.interface.composants.effets import ajouter_effets, dessiner_avec_bord
from app.interface.composants.elements import dessiner_losange
from app.interface.composants.grille_cartes import (
    OPACITE_MANQUANTE,
    RAPPORT,
    dessiner_anneau,
    dessiner_coeur,
    dessiner_pastille,
)

FORMAT_GLISSER = "application/x-riftbound-pochette"
BORD = 12
DOS = 44
MARGE_PAGE = 14
ECART = 9
ETIQUETTE = 30
FLECHES = 60
LARGEUR_MAX = 190
DELAI_FEUILLETAGE = 700
TEMPS_PAR_TOUR = 0.008
COULEUR_ANNEAUX = ["#f4f1ea", "#b9b4aa", "#7d786f", "#c9c4ba"]
CARTES_DERRIERE = 2


class VueClasseur(QWidget):
    pochette_choisie = Signal(int)
    pochette_activee = Signal(int)
    deplacement_demande = Signal(int, int)
    menu_demande = Signal(int, QPoint)
    suppression_demandee = Signal(int)
    double_page_changee = Signal()

    def __init__(self, collection, classeurs, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.classeurs = classeurs
        self.decks = None
        self.surlignage = {}
        self.nom_surlignage = ""
        self.classeur = None
        self.contenu = {}
        self.cartes = {}
        self.couleur = "#1d2b4f"
        self.double_page = 0
        self.choisie = -1
        self.survol = -1
        self.cible = -1
        self.glissee = -1
        self.appui = None
        self.molette = 0
        self.sens_feuilletage = 0
        self.images = {}
        self.images_foil = {}
        self.a_charger = []
        self.largeur_carte = 0
        self.zones = {}
        self.zones_pages = []
        self.couverture = QRectF()
        self.dos = QRectF()

        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(440, 300)

        self.precedente = self.creer_fleche("chevron-left", "Pages précédentes (Page préc.)")
        self.suivante = self.creer_fleche("chevron-right", "Pages suivantes (Page suiv.)")
        self.precedente.clicked.connect(lambda: self.tourner(-1))
        self.suivante.clicked.connect(lambda: self.tourner(1))

        self.chargeur = QTimer(self)
        self.chargeur.setInterval(0)
        self.chargeur.timeout.connect(self.charger_suite)
        self.minuteur_taille = QTimer(self)
        self.minuteur_taille.setSingleShot(True)
        self.minuteur_taille.setInterval(220)
        self.minuteur_taille.timeout.connect(self.recharger_images)
        self.feuilletage = QTimer(self)
        self.feuilletage.setSingleShot(True)
        self.feuilletage.setInterval(DELAI_FEUILLETAGE)
        self.feuilletage.timeout.connect(self.feuilleter)

        theme.signaux().change.connect(self.update)

    def creer_fleche(self, nom_icone, aide):
        bouton = QPushButton("", self)
        bouton.setObjectName("fleche")
        bouton.setCursor(Qt.CursorShape.PointingHandCursor)
        bouton.setToolTip(aide)
        bouton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        icones.lier(bouton, nom_icone, 20, "TEXTE", "OR")
        bouton.hide()
        return bouton

    def definir(self, classeur, contenu, cartes, couleur):
        nouveau = classeur is None or self.classeur is None or classeur["id"] != self.classeur["id"]
        self.classeur = classeur
        self.contenu = contenu
        self.cartes = cartes
        self.couleur = couleur
        if nouveau:
            self.double_page = 0
            self.choisie = -1
            self.survol = -1
        if classeur is not None:
            self.double_page = max(0, min(self.double_page, self.nombre_doubles_pages() - 1))
            if self.choisie >= 0 and self.choisie >= par_page(classeur) * classeur["pages"]:
                self.choisie = -1
        for fleche in (self.precedente, self.suivante):
            fleche.setVisible(classeur is not None)
        self.calculer()
        self.preparer_images()
        self.update()

    def nombre_doubles_pages(self):
        return self.classeur["pages"] // 2 + 1 if self.classeur else 0

    def pages_affichees(self):
        gauche = 2 * self.double_page
        droite = gauche + 1
        total = self.classeur["pages"]
        return (gauche if 1 <= gauche <= total else 0, droite if droite <= total else 0)

    def double_page_de(self, pochette):
        return (pochette // par_page(self.classeur) + 1) // 2

    def pochettes_visibles(self):
        return sorted(self.zones)

    def pile(self, pochette):
        if self.classeur is None or pochette not in self.contenu:
            return []
        return self.classeurs.pile(self.classeur["id"], pochette)

    def cartes_visibles(self):
        cartes = []
        for pochette in self.pochettes_visibles():
            cartes.extend(self.pile(pochette))
        return cartes

    def noms_pile(self, pochette):
        noms = set()
        for carte_id in self.pile(pochette):
            carte = self.cartes.get(carte_id)
            if carte is not None:
                noms.add(normaliser(carte["nom"]))
        return noms

    def surligner(self, besoins, nom=""):
        self.surlignage = dict(besoins)
        self.nom_surlignage = nom
        self.update()

    def montees(self):
        if self.decks is None or not self.decks.chargee:
            return {}
        return self.decks.cartes_montees()

    def toutes_les_cartes(self):
        return self.classeurs.cartes_du_classeur(self.classeur["id"]) if self.classeur else set()

    def calculer(self):
        self.zones = {}
        self.zones_pages = []
        if self.classeur is None:
            return
        colonnes = self.classeur["colonnes"]
        lignes = self.classeur["lignes"]
        largeur_dispo = self.width() - 2 * FLECHES
        hauteur_dispo = self.height() - ETIQUETTE
        fixe_largeur = 2 * (2 * MARGE_PAGE + (colonnes - 1) * ECART) + DOS + 2 * BORD
        fixe_hauteur = 2 * MARGE_PAGE + (lignes - 1) * ECART + 2 * BORD
        largeur = min(
            (largeur_dispo - fixe_largeur) / (2 * colonnes),
            (hauteur_dispo - fixe_hauteur) / (lignes * RAPPORT),
            LARGEUR_MAX,
        )
        largeur = max(24.0, largeur)
        hauteur = largeur * RAPPORT
        largeur_page = 2 * MARGE_PAGE + colonnes * largeur + (colonnes - 1) * ECART
        hauteur_page = 2 * MARGE_PAGE + lignes * hauteur + (lignes - 1) * ECART
        total_largeur = 2 * largeur_page + DOS + 2 * BORD
        total_hauteur = hauteur_page + 2 * BORD
        x = (self.width() - total_largeur) / 2
        y = max(0.0, (hauteur_dispo - total_hauteur) / 2)
        self.couverture = QRectF(x, y, total_largeur, total_hauteur)
        gauche = QRectF(x + BORD, y + BORD, largeur_page, hauteur_page)
        droite = QRectF(gauche.right() + DOS, y + BORD, largeur_page, hauteur_page)
        self.dos = QRectF(gauche.right(), y + BORD, DOS, hauteur_page)

        for numero, page in zip(self.pages_affichees(), (gauche, droite)):
            self.zones_pages.append((numero, page))
            if numero == 0:
                continue
            premiere = (numero - 1) * colonnes * lignes
            for position in range(colonnes * lignes):
                ligne, colonne = divmod(position, colonnes)
                self.zones[premiere + position] = QRectF(
                    page.x() + MARGE_PAGE + colonne * (largeur + ECART),
                    page.y() + MARGE_PAGE + ligne * (hauteur + ECART),
                    largeur,
                    hauteur,
                )

        nouvelle = round(largeur)
        if nouvelle != self.largeur_carte:
            ancienne = self.largeur_carte
            self.largeur_carte = nouvelle
            if ancienne == 0:
                self.recharger_images()
            else:
                self.minuteur_taille.start()

        milieu = round(y + total_hauteur / 2 - 20)
        self.precedente.move(round(x - 54), milieu)
        self.suivante.move(round(x + total_largeur + 14), milieu)
        self.precedente.setEnabled(self.double_page > 0)
        self.suivante.setEnabled(self.double_page < self.nombre_doubles_pages() - 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.calculer()

    def preparer_images(self):
        voulues = self.toutes_les_cartes()
        self.images = {carte_id: image for carte_id, image in self.images.items() if carte_id in voulues}
        self.images_foil = {carte_id: image for carte_id, image in self.images_foil.items() if carte_id in voulues}
        ordre = list(dict.fromkeys(self.cartes_visibles() + sorted(voulues)))
        self.a_charger = [carte_id for carte_id in ordre if carte_id not in self.images]
        if self.a_charger:
            self.chargeur.start()

    def recharger_images(self):
        self.a_charger = list(dict.fromkeys(self.cartes_visibles() + sorted(self.toutes_les_cartes())))
        self.chargeur.start()

    def charger_suite(self):
        if self.largeur_carte <= 0:
            self.chargeur.stop()
            return
        zoom = self.devicePixelRatioF()
        taille = QSize(round(self.largeur_carte * zoom), round(self.largeur_carte * RAPPORT * zoom))
        fin = time.perf_counter() + TEMPS_PAR_TOUR
        while self.a_charger and time.perf_counter() < fin:
            carte_id = self.a_charger.pop(0)
            carte = self.cartes.get(carte_id)
            image = charger_miniature(carte["image_url"], taille) if carte is not None else None
            if image is None:
                continue
            pixmap = QPixmap.fromImage(image)
            pixmap.setDevicePixelRatio(zoom)
            self.images[carte_id] = pixmap
            self.images_foil.pop(carte_id, None)
        if not self.a_charger:
            self.chargeur.stop()
        self.update()

    def image_telechargee(self, url):
        for carte_id in self.toutes_les_cartes():
            carte = self.cartes.get(carte_id)
            if carte is not None and carte["image_url"] == url and carte_id not in self.a_charger:
                self.a_charger.append(carte_id)
        if self.a_charger:
            self.chargeur.start()

    def image_foil(self, carte_id):
        if carte_id not in self.images_foil:
            self.images_foil[carte_id] = ajouter_effets(self.images[carte_id], True, 0, 0, 0)
        return self.images_foil[carte_id]

    def aller(self, double_page):
        if self.classeur is None:
            return
        double_page = max(0, min(double_page, self.nombre_doubles_pages() - 1))
        if double_page == self.double_page:
            return
        self.double_page = double_page
        self.survol = -1
        self.calculer()
        self.preparer_images()
        self.update()
        self.double_page_changee.emit()

    def tourner(self, sens):
        self.aller(self.double_page + sens)

    def choisir(self, pochette):
        if pochette == self.choisie:
            return
        self.choisie = pochette
        self.update()
        self.pochette_choisie.emit(pochette)

    def montrer(self, pochette):
        if self.classeur is None:
            return
        self.aller(self.double_page_de(pochette))
        self.choisir(pochette)

    def pochette_a(self, position):
        for pochette, zone in self.zones.items():
            if zone.adjusted(-ECART / 2, -ECART / 2, ECART / 2, ECART / 2).contains(position):
                return pochette
        return -1

    def changer_survol(self, pochette):
        if pochette != self.survol:
            self.survol = pochette
            self.setCursor(Qt.CursorShape.PointingHandCursor if pochette >= 0 else Qt.CursorShape.ArrowCursor)
            self.update()

    def changer_cible(self, pochette):
        if pochette != self.cible:
            self.cible = pochette
            self.update()

    def mousePressEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        pochette = self.pochette_a(event.position())
        if event.button() == Qt.MouseButton.LeftButton:
            self.choisir(pochette)
            if pochette in self.contenu:
                self.appui = (pochette, event.position())
        elif event.button() == Qt.MouseButton.RightButton and pochette >= 0:
            self.choisir(pochette)
            self.menu_demande.emit(pochette, event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        position = event.position()
        if self.appui is not None and event.buttons() & Qt.MouseButton.LeftButton:
            depart, origine = self.appui
            if (position - origine).manhattanLength() >= QApplication.startDragDistance():
                self.appui = None
                self.glisser(depart)
                return
        self.changer_survol(self.pochette_a(position))

    def mouseReleaseEvent(self, event):
        self.appui = None

    def mouseDoubleClickEvent(self, event):
        pochette = self.pochette_a(event.position())
        if event.button() == Qt.MouseButton.LeftButton and pochette >= 0:
            self.pochette_activee.emit(pochette)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.changer_survol(-1)

    def wheelEvent(self, event):
        self.molette += event.angleDelta().y()
        if abs(self.molette) >= 120:
            self.tourner(-1 if self.molette > 0 else 1)
            self.molette = 0
        event.accept()

    def keyPressEvent(self, event):
        touche = event.key()
        if self.classeur is None:
            super().keyPressEvent(event)
        elif touche == Qt.Key.Key_PageDown:
            self.tourner(1)
        elif touche == Qt.Key.Key_PageUp:
            self.tourner(-1)
        elif touche == Qt.Key.Key_Home:
            self.aller(0)
        elif touche == Qt.Key.Key_End:
            self.aller(self.nombre_doubles_pages() - 1)
        elif touche in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.deplacer_choix(touche)
        elif touche in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.choisie in self.contenu:
            self.suppression_demandee.emit(self.choisie)
        elif touche in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.choisie >= 0:
            self.pochette_activee.emit(self.choisie)
        else:
            super().keyPressEvent(event)

    def deplacer_choix(self, touche):
        colonnes = self.classeur["colonnes"]
        lignes = self.classeur["lignes"]
        total = par_page(self.classeur) * self.classeur["pages"]
        if self.choisie < 0:
            visibles = self.pochettes_visibles()
            if visibles:
                self.choisir(visibles[0])
            return
        page, reste = divmod(self.choisie, colonnes * lignes)
        ligne, colonne = divmod(reste, colonnes)
        x = colonne + (colonnes if (page + 1) % 2 else 0)
        if touche == Qt.Key.Key_Up:
            ligne = max(0, ligne - 1)
        elif touche == Qt.Key.Key_Down:
            ligne = min(lignes - 1, ligne + 1)
        elif touche == Qt.Key.Key_Left:
            x -= 1
        else:
            x += 1
        if x < 0:
            page -= 1
            x = 2 * colonnes - 1
        elif x >= 2 * colonnes:
            page += 1
            x = 0
        elif (x >= colonnes) != bool((page + 1) % 2):
            page += 1 if x >= colonnes else -1
        colonne = x % colonnes
        pochette = page * colonnes * lignes + ligne * colonnes + colonne
        if 0 <= page and 0 <= pochette < total:
            self.montrer(pochette)

    def glisser(self, depart):
        element = self.contenu.get(depart)
        if element is None:
            return
        donnees = QMimeData()
        donnees.setData(FORMAT_GLISSER, QByteArray(str(depart).encode()))
        glissement = QDrag(self)
        glissement.setMimeData(donnees)
        devant = contenu_pile(self.collection, self.pile(depart), element["version"])[2]
        image = self.images.get(devant)
        if image is not None:
            zoom = image.devicePixelRatio()
            apercu = image.scaledToWidth(round(84 * zoom), Qt.TransformationMode.SmoothTransformation)
            apercu.setDevicePixelRatio(zoom)
            glissement.setPixmap(apercu)
            glissement.setHotSpot(QPoint(42, round(apercu.height() / zoom / 2)))
        self.glissee = depart
        self.update()
        glissement.exec(Qt.DropAction.MoveAction)
        self.glissee = -1
        self.arreter_feuilletage()
        self.changer_cible(-1)
        self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(FORMAT_GLISSER) and event.source() is self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        position = event.position()
        self.changer_cible(self.pochette_a(position))
        if position.x() < self.couverture.left():
            sens = -1
        elif position.x() > self.couverture.right():
            sens = 1
        else:
            sens = 0
        if sens != self.sens_feuilletage:
            self.sens_feuilletage = sens
            if sens:
                self.feuilletage.start()
            else:
                self.feuilletage.stop()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.arreter_feuilletage()
        self.changer_cible(-1)

    def dropEvent(self, event):
        self.arreter_feuilletage()
        self.changer_cible(-1)
        depart = int(bytes(event.mimeData().data(FORMAT_GLISSER)).decode())
        if self.deposer(depart, self.pochette_a(event.position())):
            event.acceptProposedAction()
        else:
            event.ignore()

    def deposer(self, depart, arrivee):
        if arrivee < 0 or arrivee == depart:
            return False
        self.deplacement_demande.emit(depart, arrivee)
        self.choisir(arrivee)
        return True

    def feuilleter(self):
        if self.sens_feuilletage:
            self.tourner(self.sens_feuilletage)
            self.feuilletage.start()

    def arreter_feuilletage(self):
        self.sens_feuilletage = 0
        self.feuilletage.stop()

    def event(self, evenement):
        if evenement.type() == QEvent.Type.ToolTip:
            pochette = self.pochette_a(QPointF(evenement.pos()))
            texte = self.texte_aide(pochette)
            if texte:
                QToolTip.showText(evenement.globalPos(), texte, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(evenement)

    def texte_aide(self, pochette):
        if pochette < 0:
            return ""
        place = decrire_position(self.classeur, pochette).capitalize()
        element = self.contenu.get(pochette)
        if element is None:
            return f"{place}\nPochette vide : double-clic pour y placer une carte"
        lignes = []
        for carte_id in self.pile(pochette):
            carte = self.cartes.get(carte_id)
            quantite, foil = quantites(self.collection, carte_id, element["version"])
            if carte is None or (quantite == 0 and carte_id != element["carte_id"]):
                continue
            if quantite:
                etat = f"×{quantite}" + (" dont foil" if foil and element["version"] == "toutes" else "")
            else:
                etat = "pas encore dans ta collection"
            lignes.append(f"{carte['nom']} · {catalogue.code_affiche(carte)} · {etat}")
        if not lignes:
            lignes.append("Carte inconnue du catalogue")
        noms = self.noms_pile(pochette)
        if self.surlignage:
            besoin = sum(self.surlignage.get(nom, 0) for nom in noms)
            if besoin:
                lignes.append(f"Pour « {self.nom_surlignage} » : il en faut {besoin}")
        for nom in noms:
            for deck, quantite in self.montees().get(nom, []):
                lignes.append(f"Dans le deck monté « {deck['nom']} » : {quantite}")
        return "\n".join(lignes + [place])

    def paintEvent(self, event):
        if self.classeur is None:
            return
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.dessiner_couverture(peintre)
        for numero, page in self.zones_pages:
            if numero == 0:
                self.dessiner_interieur(peintre, page, page.center().x() < self.dos.center().x())
            else:
                self.dessiner_page(peintre, page, page.center().x() < self.dos.center().x())
        self.dessiner_dos(peintre)
        for pochette, zone in self.zones.items():
            self.dessiner_pochette(peintre, pochette, zone)
        self.dessiner_etiquettes(peintre)

    def dessiner_couverture(self, peintre):
        cadre = self.couverture
        peintre.setPen(Qt.PenStyle.NoPen)
        for ecart, alpha in ((14, 10), (8, 18), (3, 30)):
            peintre.setBrush(QColor(0, 0, 0, alpha))
            peintre.drawRoundedRect(cadre.adjusted(-ecart / 2, -ecart / 4, ecart / 2, ecart), 18 + ecart / 2, 18 + ecart / 2)
        couleur = QColor(self.couleur)
        degrade = QLinearGradient(0, cadre.top(), 0, cadre.bottom())
        degrade.setColorAt(0, couleur.lighter(118))
        degrade.setColorAt(1, couleur.darker(125))
        peintre.setBrush(degrade)
        peintre.setPen(QPen(couleur.darker(160), 1))
        peintre.drawRoundedRect(cadre, 16, 16)

    def dessiner_page(self, peintre, page, a_gauche):
        peintre.setPen(QPen(theme.couleur("BORDURE"), 1))
        peintre.setBrush(theme.couleur("SURFACE"))
        peintre.drawRoundedRect(page, 8, 8)
        ombre = QLinearGradient(page.right() if a_gauche else page.left(), 0, page.right() - 28 if a_gauche else page.left() + 28, 0)
        ombre.setColorAt(0, QColor(0, 0, 0, 46 if theme.mode() == "sombre" else 26))
        ombre.setColorAt(1, QColor(0, 0, 0, 0))
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(ombre)
        peintre.drawRoundedRect(page, 8, 8)

    def dessiner_interieur(self, peintre, page, a_gauche):
        couleur = QColor(self.couleur)
        degrade = QLinearGradient(page.topLeft(), page.bottomRight())
        degrade.setColorAt(0, couleur.darker(108))
        degrade.setColorAt(1, couleur.darker(135))
        peintre.setPen(QPen(couleur.darker(150), 1))
        peintre.setBrush(degrade)
        peintre.drawRoundedRect(page, 8, 8)
        encre = QColor(theme.OR_HAUT)
        encre.setAlpha(210)
        centre = page.center()
        if a_gauche:
            police = theme.police_titres(max(14, min(26, round(page.width() / 14))))
            police.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
            peintre.setFont(police)
            peintre.setPen(encre)
            zone_nom = QRectF(page.left() + 24, centre.y() - 60, page.width() - 48, 80)
            peintre.drawText(
                zone_nom,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom | Qt.TextFlag.TextWordWrap,
                self.classeur["nom"].upper(),
            )
            dessiner_losange(peintre, QPointF(centre.x(), centre.y() + 34), 5, theme.OR_HAUT)
            for decalage in (-1, 1):
                filet = QLinearGradient(centre.x(), 0, centre.x() + decalage * 70, 0)
                filet.setColorAt(0, encre)
                filet.setColorAt(1, QColor(0, 0, 0, 0))
                peintre.fillRect(QRectF(min(centre.x() + decalage * 12, centre.x() + decalage * 70), centre.y() + 33.5, 58, 1), filet)
            petite = QFont(self.font())
            petite.setPixelSize(11)
            petite.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
            peintre.setFont(petite)
            encre.setAlpha(150)
            peintre.setPen(encre)
            peintre.drawText(
                QRectF(page.left(), centre.y() + 50, page.width(), 20),
                Qt.AlignmentFlag.AlignHCenter,
                "RIFTBOUND COLLECTION",
            )
        else:
            dessiner_losange(peintre, centre, 5, theme.OR_HAUT, lueur=False)

    def dessiner_dos(self, peintre):
        couleur = QColor(self.couleur)
        degrade = QLinearGradient(self.dos.left(), 0, self.dos.right(), 0)
        degrade.setColorAt(0, couleur.darker(150))
        degrade.setColorAt(0.5, couleur.darker(115))
        degrade.setColorAt(1, couleur.darker(150))
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(degrade)
        peintre.drawRect(self.dos.adjusted(-1, 0, 1, 0))
        hauteur = self.dos.height()
        for proportion in (0.18, 0.5, 0.82):
            y = self.dos.top() + hauteur * proportion
            anneau = QRectF(self.dos.left() - 10, y - 7, self.dos.width() + 20, 14)
            metal = QLinearGradient(0, anneau.top(), 0, anneau.bottom())
            for position, teinte in zip((0, 0.35, 0.75, 1), COULEUR_ANNEAUX):
                metal.setColorAt(position, QColor(teinte))
            peintre.setBrush(QColor(0, 0, 0, 70))
            peintre.drawRoundedRect(anneau.translated(0, 2), 7, 7)
            peintre.setBrush(metal)
            peintre.setPen(QPen(QColor(0, 0, 0, 90), 1))
            peintre.drawRoundedRect(anneau, 7, 7)
            peintre.setPen(Qt.PenStyle.NoPen)

    def dessiner_pochette(self, peintre, pochette, zone):
        rayon = zone.width() * ARRONDI
        poche = zone.adjusted(-3, -3, 3, 3)
        peintre.setPen(QPen(theme.couleur("BORDURE"), 1))
        peintre.setBrush(theme.couleur("FOND", 150 if theme.mode() == "sombre" else 90))
        peintre.drawRoundedRect(poche, rayon + 3, rayon + 3)

        element = self.contenu.get(pochette)
        if element is None:
            stylo = QPen(theme.couleur("TEXTE_ETEINT", 70), 1.2)
            stylo.setDashPattern([3, 4])
            peintre.setPen(stylo)
            peintre.setBrush(Qt.BrushStyle.NoBrush)
            peintre.drawRoundedRect(zone.adjusted(4, 4, -4, -4), rayon, rayon)
            if pochette in (self.survol, self.cible, self.choisie):
                taille = max(14, min(28, round(zone.width() * 0.22)))
                plus = icones.pixmap("plus", theme.OR_CLAIR if pochette == self.choisie else theme.TEXTE_ETEINT, taille)
                peintre.drawPixmap(QPointF(zone.center().x() - taille / 2, zone.center().y() - taille / 2), plus)
        else:
            self.dessiner_carte(peintre, pochette, element, zone, rayon)

        if self.surlignage:
            besoin = sum(self.surlignage.get(nom, 0) for nom in self.noms_pile(pochette)) if element else 0
            if besoin:
                peintre.setPen(QPen(theme.couleur("OR"), 2.5))
                peintre.setBrush(Qt.BrushStyle.NoBrush)
                peintre.drawRoundedRect(poche.adjusted(-1, -1, 1, 1), rayon + 4, rayon + 4)
                self.dessiner_badge(peintre, zone, True)
            else:
                peintre.setPen(Qt.PenStyle.NoPen)
                peintre.setBrush(theme.couleur("FOND", 175))
                peintre.drawRoundedRect(poche.adjusted(-1, -1, 1, 1), rayon + 4, rayon + 4)
        elif element is not None:
            montees = self.montees()
            if montees and any(nom in montees for nom in self.noms_pile(pochette)):
                self.dessiner_badge(peintre, zone, False)

        if pochette == self.cible and self.cible != self.glissee:
            stylo = QPen(theme.couleur("OR"), 2)
            stylo.setDashPattern([4, 3])
            peintre.setPen(stylo)
            peintre.setBrush(theme.voile())
            peintre.drawRoundedRect(zone.adjusted(-3, -3, 3, 3), rayon + 3, rayon + 3)
        elif pochette == self.choisie:
            dessiner_anneau(peintre, zone)
        elif pochette == self.survol:
            peintre.setPen(QPen(theme.couleur("TEXTE_ETEINT"), 1.5))
            peintre.setBrush(Qt.BrushStyle.NoBrush)
            peintre.drawRoundedRect(poche, rayon + 3, rayon + 3)

    def dessiner_badge(self, peintre, zone, plein):
        cote = max(18.0, zone.width() * 0.17)
        rond = QRectF(zone.left() - cote * 0.22, zone.top() - cote * 0.22, cote, cote)
        peintre.setPen(QPen(theme.couleur("OR" if plein else "OR_BAS"), 1.2))
        peintre.setBrush(theme.couleur("OR") if plein else theme.couleur("FOND", 235))
        peintre.drawEllipse(rond)
        taille = round(cote * 0.58)
        image = icones.pixmap("layers", theme.ENCRE if plein else theme.OR_CLAIR, taille)
        peintre.drawPixmap(QPointF(rond.center().x() - taille / 2, rond.center().y() - taille / 2), image)

    def dessiner_derriere(self, peintre, nombre, zone, rayon):
        decalage = max(4.0, min(7.0, zone.width() * 0.05))
        echelle = (zone.width() - decalage * nombre) / zone.width()
        devant = QRectF(
            zone.left(),
            zone.bottom() - zone.height() * echelle,
            zone.width() * echelle,
            zone.height() * echelle,
        )
        for rang in range(nombre, 0, -1):
            place = devant.translated(decalage * rang, -decalage * rang)
            peintre.setPen(QPen(theme.couleur("TEXTE_DOUX", 230 - 60 * (rang - 1)), 1.2))
            peintre.setBrush(theme.couleur("SURFACE_HAUTE"))
            peintre.drawRoundedRect(place.adjusted(0.6, 0.6, -0.6, -0.6), rayon, rayon)
        peintre.setPen(QPen(QColor(0, 0, 0, 160), 1.5))
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.drawRoundedRect(devant.adjusted(-0.75, -0.75, 0.75, 0.75), rayon, rayon)
        return devant, rayon * echelle

    def dessiner_carte(self, peintre, pochette, element, zone, rayon):
        pile = self.pile(pochette)
        quantite, foil, carte_id, possedees = contenu_pile(self.collection, pile, element["version"])
        image = self.images.get(carte_id)
        if possedees > 1 and pochette != self.glissee:
            zone, rayon = self.dessiner_derriere(peintre, min(possedees - 1, CARTES_DERRIERE), zone, rayon)
        foil_devant = quantites(self.collection, carte_id, element["version"])[1]
        peintre.save()
        if pochette == self.glissee:
            peintre.setOpacity(0.3)
        elif quantite == 0:
            peintre.setOpacity(OPACITE_MANQUANTE)
        if image is None:
            peintre.setPen(Qt.PenStyle.NoPen)
            peintre.setBrush(theme.couleur("SURFACE_HAUTE"))
            peintre.drawRoundedRect(zone, rayon, rayon)
            carte = self.cartes.get(carte_id)
            peintre.setPen(theme.couleur("TEXTE_DOUX"))
            police = QFont(self.font())
            police.setPixelSize(max(9, min(12, round(zone.width() / 10))))
            peintre.setFont(police)
            texte = carte["nom"] if carte is not None else "?"
            peintre.drawText(zone.adjusted(6, 6, -6, -6), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, texte)
        elif foil_devant and quantite:
            dessiner_avec_bord(peintre, zone, self.image_foil(carte_id))
        else:
            peintre.drawPixmap(zone, image, QRectF(image.rect()))
        peintre.restore()
        if pochette == self.glissee:
            return
        if quantite > 0:
            dessiner_pastille(peintre, zone, quantite, foil)
        elif any(self.collection.correspond(membre, "recherchees") for membre in pile):
            dessiner_coeur(peintre, zone)

    def dessiner_etiquettes(self, peintre):
        police = theme.police_titres(11)
        police.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        petite = QFont(self.font())
        petite.setPixelSize(11)
        par = par_page(self.classeur)
        for numero, page in self.zones_pages:
            if numero == 0:
                continue
            premiere = (numero - 1) * par
            remplies = sum(1 for pochette in range(premiere, premiere + par) if pochette in self.contenu)
            titre = f"PAGE {numero}"
            detail = f"   {remplies} / {par}"
            largeur_titre = QFontMetrics(police).horizontalAdvance(titre)
            largeur_detail = QFontMetrics(petite).horizontalAdvance(detail)
            x = page.center().x() - (largeur_titre + largeur_detail) / 2
            y = self.couverture.bottom() + 20
            peintre.setFont(police)
            peintre.setPen(theme.couleur("TEXTE_DOUX"))
            peintre.drawText(QPointF(x, y), titre)
            peintre.setFont(petite)
            peintre.setPen(theme.couleur("TEXTE_ETEINT"))
            peintre.drawText(QPointF(x + largeur_titre, y), detail)
