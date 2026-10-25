from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Utilisateur(db.Model):
    __tablename__ = "utilisateurs"

    id = db.Column(db.Integer, primary_key=True)
    pseudo = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    mot_de_passe_hash = db.Column(db.String(255), nullable=False)
    cree_le = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Carte(db.Model):
    __tablename__ = "cartes"

    id = db.Column(db.Integer, primary_key=True)
    riftcodex_id = db.Column(db.String(64), unique=True, nullable=False)
    riftbound_id = db.Column(db.String(32))
    nom = db.Column(db.String(150), nullable=False, index=True)
    set_code = db.Column(db.String(10), nullable=False, index=True)
    set_nom = db.Column(db.String(80))
    numero = db.Column(db.Integer)
    rarete = db.Column(db.String(30))
    type_carte = db.Column(db.String(30))
    domaines = db.Column(db.String(100))
    image_url = db.Column(db.String(500))
    art_alternatif = db.Column(db.Boolean, default=False)
    signature = db.Column(db.Boolean, default=False)
    surnumerotee = db.Column(db.Boolean, default=False)
    tcgplayer_id = db.Column(db.String(20))


class Possession(db.Model):
    __tablename__ = "possessions"

    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    carte_id = db.Column(db.Integer, db.ForeignKey("cartes.id"), nullable=False)
    foil = db.Column(db.Boolean, nullable=False, default=False)
    quantite = db.Column(db.Integer, nullable=False, default=1)
    a_echanger = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (db.UniqueConstraint("utilisateur_id", "carte_id", "foil"),)


class Recherche(db.Model):
    __tablename__ = "recherches"

    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    carte_id = db.Column(db.Integer, db.ForeignKey("cartes.id"), nullable=False)
    foil = db.Column(db.Boolean, nullable=False, default=False)
    quantite = db.Column(db.Integer, nullable=False, default=1)

    __table_args__ = (db.UniqueConstraint("utilisateur_id", "carte_id", "foil"),)