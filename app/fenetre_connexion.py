"""Fenêtre de connexion : e-mail, mot de passe, bouton."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import supabase_client


class FenetreConnexion(QWidget):
    # Un "signal" : la fenêtre prévient le reste du logiciel qu'il s'est
    # passé quelque chose. Celui-ci transporte l'id de l'utilisateur.
    connexion_reussie = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Riftbound Collection - Connexion")
        self.setFixedWidth(380)

        # 1. Les widgets (les éléments visibles)
        titre = QLabel("Riftbound Collection")
        titre.setObjectName("titre")  # nom utilisé par la feuille de style
        titre.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.champ_email = QLineEdit()
        self.champ_email.setPlaceholderText("E-mail")

        self.champ_mdp = QLineEdit()
        self.champ_mdp.setPlaceholderText("Mot de passe")
        self.champ_mdp.setEchoMode(QLineEdit.EchoMode.Password)  # affiche des points

        self.bouton = QPushButton("Se connecter")

        self.message = QLabel("")
        self.message.setObjectName("erreur")
        self.message.setWordWrap(True)  # passe à la ligne si le message est long
        self.message.setMinimumHeight(40)  # garde la place pour 2 lignes

        # 2. Le layout : il range les widgets les uns sous les autres
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)
        layout.addWidget(titre)
        layout.addSpacing(10)
        layout.addWidget(self.champ_email)
        layout.addWidget(self.champ_mdp)
        layout.addWidget(self.bouton)
        layout.addWidget(self.message)

        # 3. Les connexions : quand X se produit, lancer la méthode Y
        self.bouton.clicked.connect(self.connecter)
        self.champ_email.returnPressed.connect(self.connecter)  # touche Entrée
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
        # Redessine la fenêtre tout de suite, avant d'attendre la réponse du serveur
        QApplication.processEvents()

        try:
            user_id = supabase_client.se_connecter(email, mot_de_passe)
        except supabase_client.ErreurSupabase as erreur:
            self.message.setText(str(erreur))
            return
        finally:
            # "finally" s'exécute toujours, que la connexion ait réussi ou non
            self.bouton.setEnabled(True)
            self.bouton.setText("Se connecter")

        self.champ_mdp.clear()  # on ne garde pas le mot de passe à l'écran
        self.connexion_reussie.emit(user_id)