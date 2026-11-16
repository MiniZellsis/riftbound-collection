import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import supabase_client

ADRESSE_VALIDE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PSEUDO_MIN = 3
PSEUDO_MAX = 20
MOT_DE_PASSE_MIN = 6


def verifier_inscription(email, pseudo, mot_de_passe, confirmation):
    if not ADRESSE_VALIDE.fullmatch(email):
        return "Entre une adresse e-mail valide."
    if not PSEUDO_MIN <= len(pseudo) <= PSEUDO_MAX:
        return f"Ton pseudo doit faire entre {PSEUDO_MIN} et {PSEUDO_MAX} caractères."
    if len(mot_de_passe) < MOT_DE_PASSE_MIN:
        return f"Ton mot de passe doit faire au moins {MOT_DE_PASSE_MIN} caractères."
    if mot_de_passe != confirmation:
        return "Les deux mots de passe ne sont pas identiques."
    return ""


class FenetreConnexion(QWidget):
    connexion_reussie = Signal(str)

    def __init__(self):
        super().__init__()
        self.inscription = False

        self.titre = QLabel("")
        self.titre.setObjectName("titre")
        self.titre.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.champ_email = QLineEdit()
        self.champ_email.setPlaceholderText("E-mail")

        self.champ_pseudo = QLineEdit()
        self.champ_pseudo.setPlaceholderText("Pseudo (visible par les autres joueurs)")
        self.champ_pseudo.setMaxLength(PSEUDO_MAX)

        self.champ_mdp = QLineEdit()
        self.champ_mdp.setEchoMode(QLineEdit.EchoMode.Password)

        self.champ_confirmation = QLineEdit()
        self.champ_confirmation.setPlaceholderText("Mot de passe, encore une fois")
        self.champ_confirmation.setEchoMode(QLineEdit.EchoMode.Password)

        self.case_rester = QCheckBox("Rester connecté")
        self.case_rester.setChecked(True)

        self.bouton = QPushButton("")
        self.bouton.setObjectName("principal")

        self.lien = QPushButton("")
        self.lien.setObjectName("lien")
        self.lien.setCursor(Qt.CursorShape.PointingHandCursor)

        self.message = QLabel("")
        self.message.setObjectName("erreur")
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)
        layout.addWidget(self.titre)
        layout.addSpacing(10)
        layout.addWidget(self.champ_email)
        layout.addWidget(self.champ_pseudo)
        layout.addWidget(self.champ_mdp)
        layout.addWidget(self.champ_confirmation)
        layout.addWidget(self.case_rester)
        layout.addWidget(self.bouton)
        layout.addWidget(self.lien, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.message)

        self.setFixedWidth(380)
        self.afficher_mode()

        self.bouton.clicked.connect(self.valider)
        self.lien.clicked.connect(self.changer_mode)
        for champ in (self.champ_email, self.champ_pseudo, self.champ_mdp, self.champ_confirmation):
            champ.returnPressed.connect(self.valider)

    def afficher_mode(self):
        inscription = self.inscription
        self.setWindowTitle(
            "Riftbound Collection - Créer un compte" if inscription else "Riftbound Collection - Connexion"
        )
        self.titre.setText("Créer un compte" if inscription else "Riftbound Collection")
        self.champ_pseudo.setVisible(inscription)
        self.champ_confirmation.setVisible(inscription)
        self.champ_mdp.setPlaceholderText(
            f"Mot de passe ({MOT_DE_PASSE_MIN} caractères minimum)" if inscription else "Mot de passe"
        )
        self.bouton.setText("Créer mon compte" if inscription else "Se connecter")
        self.lien.setText("J'ai déjà un compte" if inscription else "Pas encore de compte ? Créer un compte")
        self.ajuster_hauteur()

    def ajuster_hauteur(self):
        largeur = self.width() - 60
        hauteur = self.message.heightForWidth(largeur) if self.message.text() else 0
        self.message.setFixedHeight(max(hauteur, 40))
        self.layout().activate()
        self.setFixedHeight(self.sizeHint().height())

    def afficher_message(self, texte, erreur=True):
        self.message.setObjectName("erreur" if erreur else "succes")
        self.message.style().unpolish(self.message)
        self.message.style().polish(self.message)
        self.message.setText(texte)
        self.ajuster_hauteur()

    def changer_mode(self):
        self.inscription = not self.inscription
        self.champ_mdp.clear()
        self.champ_confirmation.clear()
        self.afficher_message("")
        self.afficher_mode()
        champ = self.champ_pseudo if self.inscription and self.champ_email.text() else self.champ_email
        champ.setFocus()

    def valider(self):
        if self.inscription:
            self.inscrire()
        else:
            self.connecter()

    def patienter(self, texte):
        self.afficher_message("")
        self.bouton.setEnabled(False)
        self.bouton.setText(texte)
        QApplication.processEvents()

    def connecter(self):
        email = self.champ_email.text().strip()
        mot_de_passe = self.champ_mdp.text()
        if not email or not mot_de_passe:
            self.afficher_message("Remplis les deux champs.")
            return

        self.patienter("Connexion...")
        try:
            user_id = supabase_client.se_connecter(
                email, mot_de_passe, self.case_rester.isChecked()
            )
        except supabase_client.ErreurSupabase as erreur:
            self.afficher_message(str(erreur))
            return
        finally:
            self.bouton.setEnabled(True)
            self.afficher_mode()

        self.champ_mdp.clear()
        self.connexion_reussie.emit(user_id)

    def inscrire(self):
        email = self.champ_email.text().strip()
        pseudo = self.champ_pseudo.text().strip()
        mot_de_passe = self.champ_mdp.text()
        probleme = verifier_inscription(email, pseudo, mot_de_passe, self.champ_confirmation.text())
        if probleme:
            self.afficher_message(probleme)
            return

        self.patienter("Création du compte...")
        try:
            user_id = supabase_client.creer_compte(
                email, pseudo, mot_de_passe, self.case_rester.isChecked()
            )
        except supabase_client.ErreurSupabase as erreur:
            self.afficher_message(str(erreur))
            return
        finally:
            self.bouton.setEnabled(True)
            self.afficher_mode()

        self.inscription = False
        self.champ_pseudo.clear()
        self.champ_mdp.clear()
        self.champ_confirmation.clear()
        self.afficher_mode()
        if user_id:
            self.connexion_reussie.emit(user_id)
            return
        self.afficher_message(
            f"Compte créé ! Ouvre le mail envoyé à {email} et clique sur le lien de confirmation. "
            "Ensuite, connecte-toi ici.",
            erreur=False,
        )
        self.champ_mdp.setFocus()
