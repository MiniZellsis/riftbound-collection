from flask import Flask, render_template

from import_cartes import importer_cartes
from models import Carte, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///riftbound.db"
db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def accueil():
    nb_cartes = db.session.scalar(db.select(db.func.count(Carte.id)))
    apercu = db.session.scalars(
        db.select(Carte).order_by(Carte.set_code, Carte.numero).limit(12)
    ).all()
    return render_template(
        "index.html", pseudo="Melvyn", nb_cartes=nb_cartes, apercu=apercu
    )


@app.cli.command("import-cartes")
def commande_import_cartes():
    """Importe ou met à jour toutes les cartes depuis l'API Riftcodex."""
    importer_cartes()