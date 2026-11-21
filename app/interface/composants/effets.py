import math

from PySide6.QtCore import QElapsedTimer, QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QConicalGradient,
    QGradient,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QMatrix4x4,
    QPainter,
    QPainterPath,
    QPixmap,
    QRadialGradient,
)

ANGLE_MAX = 14
VITESSE = 0.25
BORD = 2
ARC_EN_CIEL = ["#ff6b9a", "#ffd36b", "#7bffb1", "#6bd5ff", "#b48cff", "#ff6b9a"]
OMBRES = {}


class Inclinaison(QObject):
    change = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x = 0.0
        self.y = 0.0
        self.force = 0.0
        self.cible_x = 0.0
        self.cible_y = 0.0
        self.cible_force = 0.0
        self.chrono = QElapsedTimer()
        self.minuteur = QTimer(self)
        self.minuteur.setTimerType(Qt.TimerType.PreciseTimer)
        frequence = QGuiApplication.primaryScreen().refreshRate() or 60
        self.minuteur.setInterval(max(7, round(1000 / frequence)))
        self.minuteur.timeout.connect(self.avancer)

    def demarrer(self):
        if not self.minuteur.isActive():
            self.chrono.start()
            self.minuteur.start()

    def viser(self, zone, position):
        x = (position.x() - zone.center().x()) / (zone.width() / 2)
        y = (position.y() - zone.center().y()) / (zone.height() / 2)
        self.cible_x = max(-1.0, min(x, 1.0))
        self.cible_y = max(-1.0, min(y, 1.0))
        self.cible_force = 1.0
        self.demarrer()

    def relacher(self):
        self.cible_x = 0.0
        self.cible_y = 0.0
        self.cible_force = 0.0
        if not self.au_repos():
            self.demarrer()

    def remettre_a_zero(self):
        self.x = self.y = self.force = 0.0
        self.cible_x = self.cible_y = self.cible_force = 0.0
        self.minuteur.stop()

    def au_repos(self):
        return self.force == 0 and self.cible_force == 0

    def avancer(self):
        ecoule = min(self.chrono.restart(), 100)
        facteur = 1 - (1 - VITESSE) ** (ecoule / 16)
        self.x += (self.cible_x - self.x) * facteur
        self.y += (self.cible_y - self.y) * facteur
        self.force += (self.cible_force - self.force) * facteur
        ecart = abs(self.cible_x - self.x) + abs(self.cible_y - self.y) + abs(self.cible_force - self.force)
        if ecart < 0.01:
            self.x, self.y, self.force = self.cible_x, self.cible_y, self.cible_force
            self.minuteur.stop()
        self.change.emit()


def arc_en_ciel(centre):
    degrade = QConicalGradient(centre, 90)
    for position, couleur in enumerate(ARC_EN_CIEL):
        degrade.setColorAt(position / (len(ARC_EN_CIEL) - 1), QColor(couleur))
    return degrade


def dessiner_etoile(peintre, centre, rayon, pinceau):
    chemin = QPainterPath()
    for i in range(8):
        longueur = rayon if i % 2 == 0 else rayon * 0.35
        angle = math.pi / 4 * i - math.pi / 2
        point = QPointF(centre.x() + longueur * math.cos(angle), centre.y() + longueur * math.sin(angle))
        if i == 0:
            chemin.moveTo(point)
        else:
            chemin.lineTo(point)
    chemin.closeSubpath()
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(pinceau)
    peintre.drawPath(chemin)


def image_ombre(largeur, hauteur, rayon, zoom):
    cle = (round(largeur), round(hauteur), zoom)
    if cle not in OMBRES:
        if len(OMBRES) > 8:
            OMBRES.clear()
        image = QImage(
            round((largeur + 16) * zoom),
            round((hauteur + 16) * zoom),
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        image.setDevicePixelRatio(zoom)
        image.fill(Qt.GlobalColor.transparent)
        peintre = QPainter(image)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(QColor(0, 0, 0, 16))
        carte = QRectF(8, 8, largeur, hauteur)
        for i in range(1, 9):
            peintre.drawRoundedRect(carte.adjusted(-i, -i, i, i), rayon + i, rayon + i)
        peintre.end()
        OMBRES[cle] = QPixmap.fromImage(image)
    return OMBRES[cle]


def dessiner_ombre(peintre, zone, rayon, opacite, decalage):
    ombre = image_ombre(zone.width(), zone.height(), rayon, peintre.device().devicePixelRatioF())
    peintre.save()
    peintre.setOpacity(opacite)
    peintre.drawPixmap(QPointF(zone.x() - 8, zone.y() - 8 + decalage), ombre)
    peintre.restore()


def transformation(zone, x, y, force, agrandissement):
    matrice = QMatrix4x4()
    matrice.rotate(x * ANGLE_MAX, 0, 1, 0)
    matrice.rotate(-y * ANGLE_MAX, 1, 0, 0)
    echelle = 1 + agrandissement * force
    matrice.scale(echelle, echelle)
    return matrice.toTransform(zone.width() * 3)


def incliner(peintre, zone, x, y, force, agrandissement=0):
    peintre.translate(zone.center())
    if force > 0:
        peintre.setTransform(transformation(zone, x, y, force, agrandissement), True)
    return QRectF(-zone.width() / 2, -zone.height() / 2, zone.width(), zone.height())


def ajouter_effets(pixmap, foil, x, y, force):
    source = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    source.setDevicePixelRatio(1)
    largeur, hauteur = source.width(), source.height()
    carte = QRectF(0, 0, largeur, hauteur)
    image = QImage(largeur + 2 * BORD, hauteur + 2 * BORD, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    peintre.translate(BORD, BORD)
    peintre.drawImage(0, 0, source)

    if foil:
        decalage = QPointF(x * largeur * 0.5, y * hauteur * 0.5)
        bandes = QLinearGradient(
            QPointF(largeur * 0.2, hauteur * 0.2) + decalage,
            QPointF(largeur * 0.5, hauteur * 0.42) + decalage,
        )
        bandes.setSpread(QGradient.Spread.RepeatSpread)
        for position, couleur in enumerate(ARC_EN_CIEL):
            teinte = QColor(couleur)
            teinte.setAlpha(60 + round(80 * force))
            bandes.setColorAt(position / (len(ARC_EN_CIEL) - 1), teinte)
        peintre.setCompositionMode(QPainter.CompositionMode.CompositionMode_Overlay)
        peintre.fillRect(carte, bandes)

    if force > 0:
        centre = QPointF((x + 1) / 2 * largeur, (y + 1) / 2 * hauteur)
        reflet = QRadialGradient(centre, largeur * 0.8)
        reflet.setColorAt(0, QColor(255, 255, 255, round(70 * force)))
        reflet.setColorAt(0.5, QColor(255, 255, 255, round(18 * force)))
        reflet.setColorAt(1, QColor(255, 255, 255, 0))
        peintre.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        peintre.fillRect(carte, reflet)

    peintre.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    peintre.drawImage(0, 0, source)
    peintre.end()

    resultat = QPixmap.fromImage(image)
    resultat.setDevicePixelRatio(pixmap.devicePixelRatio())
    return resultat


def dessiner_avec_bord(peintre, locale, pixmap):
    bord = BORD / pixmap.devicePixelRatio()
    peintre.save()
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    peintre.drawPixmap(locale.adjusted(-bord, -bord, bord, bord), pixmap, QRectF(pixmap.rect()))
    peintre.restore()


def dessiner_carte(peintre, zone, pixmap, foil, x, y, force):
    peintre.save()
    locale = incliner(peintre, zone, x, y, force)
    if foil or force > 0:
        dessiner_avec_bord(peintre, locale, ajouter_effets(pixmap, foil, x, y, force))
    else:
        peintre.drawPixmap(locale, pixmap, QRectF(pixmap.rect()))
    peintre.restore()
