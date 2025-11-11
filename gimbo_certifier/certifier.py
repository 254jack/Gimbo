import os
import subprocess
import webbrowser
from threading import Timer

def open_browser():
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gimbo_certifier.settings")

    Timer(2.0, open_browser).start()

    subprocess.call(["python", "manage.py", "runserver", "0.0.0.0:8000"])
