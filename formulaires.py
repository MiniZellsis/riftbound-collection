from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

OBLIGATOIRE = "Ce champ est obligatoire."


class FormulaireInscription(FlaskForm):
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


class FormulaireConnexion(FlaskForm):
    pseudo = StringField("Pseudo", validators=[DataRequired(OBLIGATOIRE)])
    mot_de_passe = PasswordField("Mot de passe", validators=[DataRequired(OBLIGATOIRE)])
    valider = SubmitField("Se connecter")