from PySide6.QtCore import QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from app import theme
from app.effets import Inclinaison, dessiner_carte, dessiner_ombre
from app.images import ARRONDI


class ImageCarte(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.foil = False
        self.cache = None
        self.taille_cache = None
        self.inclinaison = Inclinaison(self)
        self.inclinaison.change.connect(self.update)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(150, 210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def definir(self, image):
        if image is not None and image.isNull():
            image = None
        self.image = image
        self.cache = None
        self.update()

    def definir_foil(self, foil):
        if foil != self.foil:
            self.foil = foil
            self.update()

    def zone_carte(self):
        taille = QSizeF(744, 1039) if self.image is None else QSizeF(self.image.size())
        cote = self.width() * 0.04
        haut = self.width() * 0.055
        cadre = QRectF(self.rect()).adjusted(cote, haut, -cote, -haut - 4)
        taille = taille.scaled(cadre.size(), Qt.AspectRatioMode.KeepAspectRatio)
        zone = QRectF(0, 0, taille.width(), taille.height())
        zone.moveCenter(cadre.center())
        return zone

    def mouseMoveEvent(self, event):
        zone = self.zone_carte()
        if self.image is not None and zone.contains(event.position()):
            self.inclinaison.viser(zone, event.position())
        else:
            self.inclinaison.relacher()

    def leaveEvent(self, event):
        self.inclinaison.relacher()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.inclinaison.remettre_a_zero()

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.fillRect(self.rect(), QColor(theme.SURFACE))
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        zone = self.zone_carte()
        rayon = min(zone.width(), zone.height()) * ARRONDI
        inclinaison = self.inclinaison
        dessiner_ombre(peintre, zone, rayon, 1, 6 + 4 * inclinaison.force)

        if self.image is None:
            peintre.setPen(Qt.PenStyle.NoPen)
            peintre.setBrush(QColor(theme.SURFACE_HAUTE))
            peintre.drawRoundedRect(zone, rayon, rayon)
            return

        zoom = self.devicePixelRatioF()
        taille = (zone.size() * zoom).toSize()
        if self.cache is None or self.taille_cache != taille:
            self.taille_cache = taille
            self.cache = QPixmap.fromImage(self.image.scaled(
                taille,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            self.cache.setDevicePixelRatio(zoom)
        dessiner_carte(
            peintre,
            zone,
            self.cache,
            self.foil,
            inclinaison.x,
            inclinaison.y,
            inclinaison.force,
        )
