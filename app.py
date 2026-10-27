from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf.csrf import CSRFProtect

from formulaires import FormulaireCollection, FormulaireConnexion, FormulaireInscription
from import_cartes import importer_cartes
from outils_collection import (
    STATUTS,
    condition_statut,
    enregistrer_possession,
    enregistrer_recherche,
    progression_par_set,
    quantites_possedees,
    statistiques,
    trouver_possession,
    trouver_recherche,
)
from models import Carte, Utilisateur, db

app = Flask(__name__)
app.config.from_prefixed_env()
if not app.config.get("SECRET_KEY"):
    raise RuntimeError("FLASK_SECRET_KEY manquant : ajoute-le dans le fichier .env")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///riftbound.db"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["WTF_I18N_ENABLED"] = False  # laisse WTForms afficher ses messages en français

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "connexion"
login_manager.login_message = "Connecte-toi pour accéder à cette page."

CARTES_PAR_PAGE = 40

with app.app_context():
    db.create_all()


@login_manager.user_loader
def charger_utilisateur(user_id):
    return db.session.get(Utilisateur, int(user_id))


def trouver_par_pseudo(pseudo):
    return db.session.scalar(
        db.select(Utilisateur).where(db.func.lower(Utilisateur.pseudo) == pseudo.lower())
    )


def trouver_par_email(email):
    return db.session.scalar(db.select(Utilisateur).filter_by(email=email))


@app.route("/")
def accueil():
    nb_cartes = db.session.scalar(db.select(db.func.count(Carte.id)))
    apercu = db.session.scalars(
        db.select(Carte).order_by(Carte.set_code, Carte.numero).limit(12)
    ).all()
    return render_template("index.html", nb_cartes=nb_cartes, apercu=apercu)


@app.route("/cartes")
def cartes():
    recherche = request.args.get("q", "").strip()
    set_code = request.args.get("set", "")
    rarete = request.args.get("rarete", "")
    statut = request.args.get("statut", "")
    page = request.args.get("page", 1, type=int)

    requete = db.select(Carte)
    if recherche:
        requete = requete.where(
            db.func.lower(Carte.nom).contains(recherche.lower(), autoescape=True)
        )
    if set_code:
        requete = requete.where(Carte.set_code == set_code)
    if rarete:
        requete = requete.where(Carte.rarete == rarete)
    if statut and current_user.is_authenticated:
        condition = condition_statut(statut)
        if condition is not None:
            requete = requete.where(condition)
    requete = requete.order_by(Carte.set_nom, Carte.numero, Carte.nom)

    pagination = db.paginate(
        requete, page=page, per_page=CARTES_PAR_PAGE, error_out=False
    )

    sets = db.session.execute(
        db.select(Carte.set_code, Carte.set_nom).distinct().order_by(Carte.set_nom)
    ).all()
    raretes = db.session.scalars(
        db.select(Carte.rarete).distinct().order_by(Carte.rarete)
    ).all()

    filtres = {"q": recherche, "set": set_code, "rarete": rarete, "statut": statut}
    filtres = {cle: valeur for cle, valeur in filtres.items() if valeur}

    possessions = {}
    if current_user.is_authenticated:
        possessions = quantites_possedees([carte.id for carte in pagination.items])

    return render_template(
        "cartes.html",
        pagination=pagination,
        sets=sets,
        raretes=raretes,
        filtres=filtres,
        statuts=STATUTS,
        possessions=possessions,
    )


@app.route("/cartes/<int:carte_id>", methods=["GET", "POST"])
def detail_carte(carte_id):
    carte = db.get_or_404(Carte, carte_id)

    if not current_user.is_authenticated:
        if request.method == "POST":
            return login_manager.unauthorized()
        return render_template("carte.html", carte=carte, form=None)

    form = FormulaireCollection()

    if form.validate_on_submit():
        enregistrer_possession(carte.id, False, form.normale.data, form.normale_echange.data)
        enregistrer_possession(carte.id, True, form.foil.data, form.foil_echange.data)
        enregistrer_recherche(carte.id, False, form.recherche_normale.data)
        enregistrer_recherche(carte.id, True, form.recherche_foil.data)
        db.session.commit()
        flash("Collection mise à jour.")
        return redirect(url_for("detail_carte", carte_id=carte.id))

    if request.method == "GET":
        normale = trouver_possession(carte.id, False)
        foil = trouver_possession(carte.id, True)
        recherche_normale = trouver_recherche(carte.id, False)
        recherche_foil = trouver_recherche(carte.id, True)

        form.normale.data = normale.quantite if normale else 0
        form.normale_echange.data = normale.a_echanger if normale else 0
        form.foil.data = foil.quantite if foil else 0
        form.foil_echange.data = foil.a_echanger if foil else 0
        form.recherche_normale.data = recherche_normale.quantite if recherche_normale else 0
        form.recherche_foil.data = recherche_foil.quantite if recherche_foil else 0

    return render_template("carte.html", carte=carte, form=form)


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if current_user.is_authenticated:
        return redirect(url_for("accueil"))

    form = FormulaireInscription()
    if form.validate_on_submit():
        pseudo = form.pseudo.data.strip()
        email = form.email.data.strip().lower()

        if trouver_par_pseudo(pseudo):
            form.pseudo.errors.append("Ce pseudo est déjà pris.")
        elif trouver_par_email(email):
            form.email.errors.append("Cet email est déjà utilisé.")
        else:
            utilisateur = Utilisateur(pseudo=pseudo, email=email)
            utilisateur.definir_mot_de_passe(form.mot_de_passe.data)
            db.session.add(utilisateur)
            db.session.commit()
            login_user(utilisateur)
            flash(f"Bienvenue {pseudo}, ton compte est créé !")
            return redirect(url_for("collection"))

    return render_template("inscription.html", form=form)


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    if current_user.is_authenticated:
        return redirect(url_for("accueil"))

    form = FormulaireConnexion()
    if form.validate_on_submit():
        utilisateur = trouver_par_pseudo(form.pseudo.data.strip())
        if utilisateur and utilisateur.verifier_mot_de_passe(form.mot_de_passe.data):
            login_user(utilisateur)
            flash(f"Content de te revoir, {utilisateur.pseudo} !")
            return redirect(url_for("collection"))
        flash("Pseudo ou mot de passe incorrect.", "erreur")

    return render_template("connexion.html", form=form)


@app.route("/deconnexion", methods=["POST"])
@login_required
def deconnexion():
    logout_user()
    flash("Tu es déconnecté.")
    return redirect(url_for("accueil"))


@app.route("/collection")
@login_required
def collection():
    return render_template(
        "collection.html", stats=statistiques(), progression=progression_par_set()
    )


@app.cli.command("import-cartes")
def commande_import_cartes():
    """Importe ou met à jour toutes les cartes depuis l'API Riftcodex."""
    importer_cartes()