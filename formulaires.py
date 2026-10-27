from flask_wtf import FlaskForm
from wtforms import EmailField, IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Regexp,
    ValidationError,
)

OBLIGATOIRE = "Ce champ est obligatoire."


class FormulaireBase(FlaskForm):
    """Tous nos formulaires héritent de cette classe : messages en français."""

    class Meta:
        locales = ["fr"]


class FormulaireInscription(FormulaireBase):
    pseudo = StringField(
        "Pseudo",
        validators=[
            DataRequired(OBLIGATOIRE),
            Length(min=3, max=30, message="Entre 3 et 30 caractères."),
            Regexp(r"^[A-Za-z0-9_-]+$", message="Lettres, chiffres, _ et - uniquement."),
        ],
    )
    email = EmailField(
        "Email",
        validators=[
            DataRequired(OBLIGATOIRE),
            Email(message="Adresse email invalide."),
            Length(max=255),
        ],
    )
    mot_de_passe = PasswordField(
        "Mot de passe (12 caractères minimum)",
        validators=[
            DataRequired(OBLIGATOIRE),
            Length(min=12, max=128, message="Entre 12 et 128 caractères."),
        ],
    )
    confirmation = PasswordField(
        "Confirme le mot de passe",
        validators=[
            DataRequired(OBLIGATOIRE),
            EqualTo("mot_de_passe", message="Les mots de passe ne correspondent pas."),
        ],
    )
    valider = SubmitField("Créer mon compte")


class FormulaireConnexion(FormulaireBase):
    pseudo = StringField("Pseudo", validators=[DataRequired(OBLIGATOIRE)])
    mot_de_passe = PasswordField("Mot de passe", validators=[DataRequired(OBLIGATOIRE)])
    valider = SubmitField("Se connecter")


QUANTITE = [
    InputRequired(OBLIGATOIRE),
    NumberRange(min=0, max=999, message="Entre 0 et 999."),
]


class FormulaireCollection(FormulaireBase):
    normale = IntegerField("Normales possédées", validators=QUANTITE)
    normale_echange = IntegerField("Normales à échanger", validators=QUANTITE)
    foil = IntegerField("Foils possédées", validators=QUANTITE)
    foil_echange = IntegerField("Foils à échanger", validators=QUANTITE)
    recherche_normale = IntegerField("Normales recherchées", validators=QUANTITE)
    recherche_foil = IntegerField("Foils recherchées", validators=QUANTITE)
    valider = SubmitField("Enregistrer")

    # WTForms appelle automatiquement les méthodes validate_<nom du champ>
    def validate_normale_echange(self, champ):
        if (champ.data or 0) > (self.normale.data or 0):
            raise ValidationError("Tu ne peux pas échanger plus de cartes que tu n'en as.")

    def validate_foil_echange(self, champ):
        if (champ.data or 0) > (self.foil.data or 0):
            raise ValidationError("Tu ne peux pas échanger plus de cartes que tu n'en as.")