from PySide6.QtCore import QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from app import theme
from app.images import ARRONDI


class ImageCarte(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.cache = None
        self.taille_cache = None
        self.setMinimumSize(150, 210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def definir(self, image):
        if image is not None and image.isNull():
            image = None
        self.image = image
        self.cache = None
        self.update()

    def zone_carte(self):
        taille = QSizeF(744, 1039) if self.image is None else QSizeF(self.image.size())
        cadre = QRectF(self.rect()).adjusted(12, 4, -12, -16)
        taille = taille.scaled(cadre.size(), Qt.AspectRatioMode.KeepAspectRatio)
        zone = QRectF(0, 0, taille.width(), taille.height())
        zone.moveCenter(cadre.center())
        return zone

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        zone = self.zone_carte()
        rayon = min(zone.width(), zone.height()) * ARRONDI

        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(QColor(0, 0, 0, 16))
        for i in range(1, 9):
            peintre.drawRoundedRect(zone.adjusted(-i, -i + 6, i, i + 6), rayon + i, rayon + i)

        if self.image is None:
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
        peintre.drawPixmap(zone, self.cache, QRectF(self.cache.rect()))
