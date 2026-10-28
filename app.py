from urllib.parse import urlsplit

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

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
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

login_manager = LoginManager(app)
login_manager.login_view = "connexion"
login_manager.login_message = "Connecte-toi pour accéder à cette page."

CARTES_PAR_PAGE = 40

HASH_FACTICE = generate_password_hash("mot-de-passe-factice")

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


def est_lien_interne(url):
    """Vrai seulement pour un lien vers notre propre site, comme /cartes/12."""
    if not url or not url.startswith("/") or url.startswith("//"):
        return False
    if "\\" in url or any(caractere.isspace() for caractere in url):
        return False
    return urlsplit(url).netloc == ""


@app.after_request
def ajouter_entetes_securite(reponse):
    reponse.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' https://cmsassets.rgpub.io; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    reponse.headers["X-Content-Type-Options"] = "nosniff"
    reponse.headers["X-Frame-Options"] = "DENY"
    reponse.headers["Referrer-Policy"] = "same-origin"
    reponse.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return reponse


@app.errorhandler(404)
def page_introuvable(erreur):
    return render_template(
        "erreur.html", titre="Page introuvable", message="Cette page n'existe pas."
    ), 404


@app.errorhandler(429)
def trop_de_tentatives(erreur):
    return render_template(
        "erreur.html",
        titre="Trop de tentatives",
        message="Tu as fait trop d'essais. Attends un peu avant de réessayer.",
    ), 429


@app.errorhandler(CSRFError)
def formulaire_expire(erreur):
    return render_template(
        "erreur.html",
        titre="Formulaire expiré",
        message="Le formulaire a expiré. Recharge la page et réessaie.",
    ), 400


@app.errorhandler(500)
def erreur_serveur(erreur):
    db.session.rollback()
    return render_template(
        "erreur.html",
        titre="Erreur du serveur",
        message="Quelque chose s'est mal passé. Réessaie plus tard.",
    ), 500


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
@limiter.limit("5 per hour", methods=["POST"])
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
@limiter.limit("5 per minute; 20 per hour", methods=["POST"])
def connexion():
    if current_user.is_authenticated:
        return redirect(url_for("accueil"))

    form = FormulaireConnexion()
    if form.validate_on_submit():
        utilisateur = trouver_par_pseudo(form.pseudo.data.strip())

        if utilisateur is not None:
            mot_de_passe_ok = utilisateur.verifier_mot_de_passe(form.mot_de_passe.data)
        else:
            check_password_hash(HASH_FACTICE, form.mot_de_passe.data)
            mot_de_passe_ok = False

        if mot_de_passe_ok:
            login_user(utilisateur)
            flash(f"Content de te revoir, {utilisateur.pseudo} !")

            page_suivante = request.args.get("next")
            if not est_lien_interne(page_suivante):
                page_suivante = url_for("collection")
            return redirect(page_suivante)

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