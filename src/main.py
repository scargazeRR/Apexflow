import sys
import traceback
import datetime
import os

def resource_path(relative_path):
    """ Hilfsfunktion für PyInstaller: Gibt den absoluten Pfad zur Ressource zurück. """
    try:
        # PyInstaller erstellt einen temporären Ordner und speichert den Pfad in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def log_error(exc_type, exc_value, exc_tb):
    """Fängt jeden fatalen Fehler ab, BEVOR die App abstürzt."""
    with open("apexflow_error.txt", "a") as f:
        f.write(f"\n--- CRASH {datetime.datetime.now()} ---\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)

# Globales Sicherheitsnetz sofort aktivieren
sys.excepthook = log_error

if __name__ == "__main__":
    with open("apexflow_log.txt", "w") as f:
        f.write(f"Starte APEXFLOW v2.0 - {datetime.datetime.now()}\n")
    
    # Lazy Import: Die GUI wird erst geladen, wenn das Logging steht.
    from gui import start_gui
    start_gui()
