import queue
import threading

from PySide6.QtCore import QObject, Qt, Signal

from app import journal
from app.donnees import supabase_client

ATTENTE_FERMETURE = 10


class Synchronisation(QObject):
    change = Signal()
    envoi_reussi = Signal()
    envoi_echoue = Signal(str)
    envoi_fini = Signal(str)
    message = Signal(str)

    titre = ""
    message_tables = ""

    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.chargee = False
        self.erreur = ""
        self.a_recharger = False
        self.file = queue.Queue()
        self.condition = threading.Condition()
        self.restants = 0
        self.echecs_non_vus = 0
        self.envoi_fini.connect(self.fin_envoi, Qt.ConnectionType.QueuedConnection)
        threading.Thread(target=self.envoyer, daemon=True).start()

    def lire(self):
        raise NotImplementedError

    def appliquer(self, *donnees):
        raise NotImplementedError

    def executer(self, operation, argument):
        raise NotImplementedError

    def signaler(self):
        self.change.emit()

    def charger(self):
        try:
            self.appliquer(*self.lire())
        except supabase_client.TableAbsente:
            self.erreur = self.message_tables
        except supabase_client.ErreurSupabase as erreur:
            self.erreur = f"{self.titre} indisponibles : {erreur}"
        except Exception as exception:
            journal.noter_erreur(type(exception), exception, exception.__traceback__)
            self.erreur = f"{self.titre} indisponibles : erreur inattendue (détails dans erreurs.log)."
        self.signaler()
        return self.chargee

    def resynchroniser(self):
        with self.condition:
            occupe = self.restants > 0
        if not self.a_recharger or occupe:
            return
        try:
            donnees = self.lire()
        except supabase_client.ErreurSupabase:
            return
        self.a_recharger = False
        self.appliquer(*donnees)
        self.signaler()

    def ajouter_envoi(self, *etapes):
        with self.condition:
            self.restants += 1
        self.file.put(list(etapes))

    def envoyer(self):
        while True:
            etapes = self.file.get()
            if etapes is None:
                return
            erreur = ""
            try:
                for operation, argument in etapes:
                    self.executer(operation, argument)
            except supabase_client.ErreurSupabase as exception:
                erreur = str(exception)
            except Exception as exception:
                journal.noter_erreur(type(exception), exception, exception.__traceback__)
                erreur = "erreur inattendue (détails dans erreurs.log)"
            with self.condition:
                self.restants -= 1
                if erreur:
                    self.echecs_non_vus += 1
                self.condition.notify_all()
            try:
                self.envoi_fini.emit(erreur)
            except RuntimeError:
                return

    def fin_envoi(self, erreur):
        if erreur:
            with self.condition:
                self.echecs_non_vus -= 1
            self.a_recharger = True
            self.envoi_echoue.emit(erreur)
        with self.condition:
            termine = self.restants == 0
        if not termine:
            return
        if self.a_recharger:
            self.resynchroniser()
        elif not erreur:
            self.envoi_reussi.emit()

    def attendre_envois(self):
        with self.condition:
            termine = self.condition.wait_for(lambda: self.restants == 0, timeout=ATTENTE_FERMETURE)
            return termine and self.echecs_non_vus == 0

    def arreter(self):
        self.file.put(None)
