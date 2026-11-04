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


class FenetreConnexion(QWidget):
    connexion_reussie = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Riftbound Collection - Connexion")

        titre = QLabel("Riftbound Collection")
        titre.setObjectName("titre")
        titre.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.champ_email = QLineEdit()
        self.champ_email.setPlaceholderText("E-mail")

        self.champ_mdp = QLineEdit()
        self.champ_mdp.setPlaceholderText("Mot de passe")
        self.champ_mdp.setEchoMode(QLineEdit.EchoMode.Password)

        self.case_rester = QCheckBox("Rester connecté")
        self.case_rester.setChecked(True)

        self.bouton = QPushButton("Se connecter")

        self.message = QLabel("")
        self.message.setObjectName("erreur")
        self.message.setWordWrap(True)
        self.message.setMinimumHeight(40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)
        layout.addWidget(titre)
        layout.addSpacing(10)
        layout.addWidget(self.champ_email)
        layout.addWidget(self.champ_mdp)
        layout.addWidget(self.case_rester)
        layout.addWidget(self.bouton)
        layout.addWidget(self.message)

        self.setFixedWidth(380)
        self.setFixedHeight(self.sizeHint().height())

        self.bouton.clicked.connect(self.connecter)
        self.champ_email.returnPressed.connect(self.connecter)
        self.champ_mdp.returnPressed.connect(self.connecter)

    def connecter(self):
        email = self.champ_email.text().strip()
        mot_de_passe = self.champ_mdp.text()
        if not email or not mot_de_passe:
            self.message.setText("Remplis les deux champs.")
            return

        self.message.setText("")
        self.bouton.setEnabled(False)
        self.bouton.setText("Connexion...")
        QApplication.processEvents()

        try:
            user_id = supabase_client.se_connecter(
                email, mot_de_passe, self.case_rester.isChecked()
            )
        except supabase_client.ErreurSupabase as erreur:
            self.message.setText(str(erreur))
            return
        finally:
            self.bouton.setEnabled(True)
            self.bouton.setText("Se connecter")

        self.champ_mdp.clear()
        self.connexion_reussie.emit(user_id)