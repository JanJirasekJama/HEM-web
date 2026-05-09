import os
import sys
import json
from datetime import datetime, timedelta
import shutil
import csv
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import tempfile
from pathlib import Path
import zipfile
import subprocess
import winreg

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QVBoxLayout, QFormLayout,
    QHBoxLayout, QDialog, QTabWidget, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu,
    QGroupBox, QTextEdit, QSpinBox, QDateEdit,
    QFileDialog, QTreeWidget, QTreeWidgetItem,
    QSplitter, QStatusBar, QToolBar, QListWidget, QListWidgetItem,
    QRadioButton, QButtonGroup, QInputDialog, QDialogButtonBox,
    QStackedWidget, QCalendarWidget, QFrame, QScrollArea,
    QGridLayout, QSizePolicy, QColorDialog, QToolButton,
    QSystemTrayIcon
)
from PySide6.QtCore import (
    Qt, QTimer, QDateTime, QDate, QTime, QThread, Signal,
    QSettings, QPoint, QSize, QRect, QEvent, QPropertyAnimation,
    QEasingCurve, QDir
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import (
    QPalette, QColor, QIcon, QAction, QFont, QFontMetrics,
    QPainter, QBrush, QPen, QLinearGradient, QPixmap, QImage,
    QKeySequence, QShortcut, QCursor, QMouseEvent, QKeyEvent,
    QDesktopServices, QTextCharFormat
)

# ================= CESTY =================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APP_DIR = os.path.join(os.environ["LOCALAPPDATA"], "HEM_Komunikace")
os.makedirs(APP_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
USERS_FILE = os.path.join(APP_DIR, "users.json")
MESSAGES_FILE = os.path.join(APP_DIR, "messages.json")
TASKS_FILE = os.path.join(APP_DIR, "tasks.json")
CASH_DIARY_FILE = os.path.join(APP_DIR, "cash_diary.json")
EMAIL_RECIPIENTS_FILE = os.path.join(APP_DIR, "email_recipients.json")
SHIFT_LOG_FILE = os.path.join(APP_DIR, "shift_log.json")
INTEGRITY_HASH_FILE = os.path.join(APP_DIR, "integrity.hash")
TASK_COMPLETIONS_FILE = os.path.join(APP_DIR, "task_completions.json")

# ================= DEFAULT NASTAVENÍ =================
DEFAULT_SETTINGS = {
    "theme": "system",
    "email_notifications": True,
    "auto_save": True,
    "save_interval": 5,
    "company_name": "Wellness Hotel Beethoven",
    "email_smtp_server": "smtp.gmail.com",
    "email_smtp_port": 587,
    "email_smtp_username": "",
    "email_smtp_password": "",
    "email_sender": "recepce@hotelbeethoven.cz",
    "email_subject": "Vzkazy z recepce - {date} | Příjezdy: {arrivals} | Průběhy: {stayovers} | Odjezdy: {departures} | Wellness: {wellnesses}",
    "email_template": "Dobrý den,\n\nzde jsou vzkazy z dnešní směny:\n\n{messages}\n\nS pozdravem,\n{user_name}",
    "backup_enabled": True,
    "backup_keep_days": 10,
    "backup_path": os.path.join(os.path.expanduser("~"), "Documents", "HEM_Backups"),
}

# ================= DEFAULT PŘÍJEMCI EMAILŮ =================
DEFAULT_EMAIL_RECIPIENTS = [
    {"name": "Recepce", "email": "recepce@hotelbeethoven.cz", "active": True},
    {"name": "Ředitel", "email": "reditel@hotelbeethoven.cz", "active": True},
    {"name": "Ubytování", "email": "ubytovani@hotelbeethoven.cz", "active": True}
]

# ================= POMOCNÉ FUNKCE =================
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2, ensure_ascii=False)
        return DEFAULT_SETTINGS.copy()
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

settings = load_settings()

def load_email_recipients():
    if not os.path.exists(EMAIL_RECIPIENTS_FILE):
        with open(EMAIL_RECIPIENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_EMAIL_RECIPIENTS, f, indent=2, ensure_ascii=False)
        return DEFAULT_EMAIL_RECIPIENTS.copy()
    with open(EMAIL_RECIPIENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_email_recipients(data):
    with open(EMAIL_RECIPIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def convert_old_messages(old_messages):
    from collections import defaultdict
    grouped = defaultdict(list)
    for msg in old_messages:
        dt = datetime.strptime(msg["timestamp"], "%Y-%m-%d %H:%M:%S")
        date_key = dt.strftime("%d.%m.%Y")
        user = msg["user"]
        grouped[(date_key, user)].append(msg["message"])
    
    new_messages = []
    for (date_key, user), messages in grouped.items():
        content = "\n".join([f"- {m}" for m in messages])
        new_messages.append({
            "date": date_key,
            "user": user,
            "content": content
        })
    return new_messages

def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        return []
    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data and isinstance(data, list) and len(data) > 0 and "timestamp" in data[0]:
        data = convert_old_messages(data)
        save_messages(data)
    return data

def save_messages(data):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tasks(data):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_task_completions():
    if not os.path.exists(TASK_COMPLETIONS_FILE):
        return {}
    with open(TASK_COMPLETIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_task_completions(data):
    with open(TASK_COMPLETIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_cash_diary():
    if not os.path.exists(CASH_DIARY_FILE):
        return []
    with open(CASH_DIARY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cash_diary(data):
    with open(CASH_DIARY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_shift_log():
    if not os.path.exists(SHIFT_LOG_FILE):
        return []
    with open(SHIFT_LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_shift_log(data):
    with open(SHIFT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ================= FUNKCE PRO ZÁLOHOVÁNÍ =================
def create_backup():
    if not settings.get("backup_enabled", True):
        return None
    
    backup_path = settings.get("backup_path", os.path.join(os.path.expanduser("~"), "Documents", "HEM_Backups"))
    os.makedirs(backup_path, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_path, f"HEM_backup_{timestamp}.zip")
    
    files_to_backup = [
        SETTINGS_FILE,
        USERS_FILE,
        MESSAGES_FILE,
        TASKS_FILE,
        CASH_DIARY_FILE,
        EMAIL_RECIPIENTS_FILE,
        SHIFT_LOG_FILE,
        TASK_COMPLETIONS_FILE
    ]
    
    try:
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files_to_backup:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
        
        keep_days = settings.get("backup_keep_days", 10)
        cutoff_time = datetime.now() - timedelta(days=keep_days)
        
        for file in os.listdir(backup_path):
            file_path = os.path.join(backup_path, file)
            if os.path.isfile(file_path) and file.startswith("HEM_backup_") and file.endswith(".zip"):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
        
        return backup_file
    except Exception as e:
        print(f"Chyba při vytváření zálohy: {e}")
        return None

# ================= FUNKCE PRO AUTOMATICKÉ URČENÍ SMĚNY =================
def determine_shift_type(date_str, user):
    shift_log = load_shift_log()
    
    day_shifts = []
    for shift in shift_log:
        try:
            shift_date = datetime.strptime(shift.get("start_time", ""), "%d.%m.%Y %H:%M").strftime("%d.%m.%Y")
            if shift_date == date_str:
                day_shifts.append(shift)
        except:
            continue
    
    day_shifts.sort(key=lambda x: datetime.strptime(x.get("start_time", "00:00"), "%d.%m.%Y %H:%M"))
    
    user_shifts = [s for s in day_shifts if s.get("user") == user]
    if not user_shifts:
        return "Celodenní"
    
    if day_shifts and day_shifts[0].get("user") == user:
        if len(day_shifts) > 1:
            return "Ranní"
    
    if len(day_shifts) > 1 and day_shifts[1].get("user") == user:
        return "Odpolední"
    
    return "Celodenní"

# ================= FUNKCE PRO KONTROLU STAVU ZAPSÁNÍ =================
def check_cash_status():
    today = datetime.now().strftime("%d.%m.%Y")
    now_hour = datetime.now().hour
    
    cash_diary = load_cash_diary()
    
    today_entries = [e for e in cash_diary if e["date"] == today]
    
    if not today_entries:
        return {
            "zapsáno_ráno": False,
            "zapsáno_večer": False,
            "stav": "Nezapsáno",
            "barva": "red",
            "popis": "Dnešní peněžní deník ještě nebyl zapsán!"
        }
    
    morning_recorded = any(e.get("cash_start", 0) != 0 for e in today_entries)
    evening_recorded = any(e.get("cash_end", 0) != 0 for e in today_entries)
    
    if not morning_recorded:
        return {
            "zapsáno_ráno": False,
            "zapsáno_večer": False,
            "stav": "Nezapsáno ráno",
            "barva": "red",
            "popis": "Ranní hotovost ještě nebyla zapsána!"
        }
    elif not evening_recorded and now_hour >= 20:
        return {
            "zapsáno_ráno": True,
            "zapsáno_večer": False,
            "stav": "Čeká na zapsání hotovosti na konci",
            "barva": "orange",
            "popis": "Večerní hotovost čeká na zapsání (po 20:00)"
        }
    elif not evening_recorded:
        return {
            "zapsáno_ráno": True,
            "zapsáno_večer": False,
            "stav": "Zapsáno ráno",
            "barva": "green",
            "popis": "Ranní hotovost zapsána, čeká se na večerní"
        }
    else:
        return {
            "zapsáno_ráno": True,
            "zapsáno_večer": True,
            "stav": "Kompletně zapsáno",
            "barva": "green",
            "popis": "Dnešní peněžní deník je kompletní"
        }

# ================= NASTAVENÍ TÉMAT =================
def setup_theme(app, theme_name):
    if theme_name == "dark":
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)
    elif theme_name == "light":
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, Qt.white)
        palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.black)
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(0, 100, 200))
        palette.setColor(QPalette.Highlight, QColor(0, 100, 200))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        app.setPalette(palette)
    else:
        app.setStyle("")

# ================= BEZPEČNOSTNÍ SYSTÉM PROTI VTIPÁLKŮM =================
def get_current_file_hash():
    if getattr(sys, 'frozen', False):
        file_path = sys.executable
    else:
        file_path = os.path.abspath(__file__)
    
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        return file_hash
    except Exception as e:
        print(f"Chyba při výpočtu hashe: {e}")
        return None

def check_integrity():
    current_hash = get_current_file_hash()
    if current_hash is None:
        return
    
    if os.path.exists(INTEGRITY_HASH_FILE):
        with open(INTEGRITY_HASH_FILE, 'r', encoding='utf-8') as f:
            stored_hash = f.read().strip()
        
        if current_hash != stored_hash:
            QMessageBox.critical(
                None,
                "Bezpečnostní varování",
                "Program byl pozměněn nebo poškozen!\n\n"
                "Z bezpečnostních důvodů bude aplikace ukončena.\n"
                "Kontaktujte správce systému."
            )
            sys.exit(1)
    else:
        with open(INTEGRITY_HASH_FILE, 'w', encoding='utf-8') as f:
            f.write(current_hash)

# ================= FUNKCE PRO VYTVOŘENÍ ZÁSTUPCE NA PLOŠE =================
def create_desktop_shortcut():
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    shortcut_name = "KOMUNIKACE"
    
    lnk_path = os.path.join(desktop, f"{shortcut_name}.lnk")
    bat_path = os.path.join(desktop, f"{shortcut_name}.bat")
    
    if os.path.exists(lnk_path) or os.path.exists(bat_path):
        return
    
    if getattr(sys, 'frozen', False):
        target_path = sys.executable
        working_dir = os.path.dirname(target_path)
        ps_script = f'''
        $WScriptShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WScriptShell.CreateShortcut("{lnk_path}")
        $Shortcut.TargetPath = "{target_path}"
        $Shortcut.WorkingDirectory = "{working_dir}"
        $Shortcut.Save()
        '''
        try:
            subprocess.run(["powershell.exe", "-Command", ps_script], check=True, capture_output=True)
            print(f"Zástupce vytvořen: {lnk_path}")
        except Exception as e:
            print(f"Chyba při vytváření zástupce pomocí PowerShell: {e}")
            create_bat_shortcut(bat_path, target_path, working_dir)
    else:
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        create_bat_shortcut(bat_path, python_exe, working_dir=os.path.dirname(script_path), arguments=f'"{script_path}"')
    
    if os.path.exists(lnk_path) and os.path.exists(bat_path):
        os.remove(bat_path)

def create_bat_shortcut(bat_path, target_path, working_dir, arguments=""):
    bat_content = f'''@echo off
cd /d "{working_dir}"
start "" "{target_path}" {arguments}
'''
    try:
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        print(f"BAT zástupce vytvořen: {bat_path}")
    except Exception as e:
        print(f"Chyba při vytváření BAT zástupce: {e}")

# ================= FUNKCE PRO SPRÁVU SPOUŠTĚNÍ PŘI STARTU PC =================
def add_to_startup():
    """Přidá program do spouštěcích složek Windows pomocí registru."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        if getattr(sys, 'frozen', False):
            winreg.SetValueEx(key, "HEM_Komunikace", 0, winreg.REG_SZ, sys.executable)
        else:
            cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
            winreg.SetValueEx(key, "HEM_Komunikace", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Chyba při přidávání do startup (registr): {e}")
        return False

def is_in_startup():
    """Zkontroluje, zda je program již ve spouštěcích složkách (registr)."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_READ)
        winreg.QueryValueEx(key, "HEM_Komunikace")
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

def ensure_startup_entry():
    """Zajistí, že program je zaregistrován pro automatické spouštění s Windows."""
    if not is_in_startup():
        add_to_startup()

# ================= JEDNODUCHÁ INSTANCE (SYSTRAY A PŘEPNUTÍ) =================
class SingleInstanceManager:
    """Zajišťuje, že běží pouze jedna instance aplikace. Pokud se pokusí spustit druhá,
       pošle zprávu existující instanci a ukončí se."""
    def __init__(self, app_name="HEM_Komunikace"):
        self.server_name = app_name
        self.server = None
        self.existing_instance = False

    def try_to_become_server(self):
        """Pokusí se stát lokálním serverem. Pokud se to podaří, vrátí True (jsme první instance)."""
        self.server = QLocalServer()
        # Pokud server již existuje, listen() selže
        if not self.server.listen(self.server_name):
            # Server již běží, jsme druhá instance
            self.existing_instance = True
            return False
        # Jsme první instance
        self.server.newConnection.connect(self.handle_new_connection)
        return True

    def handle_new_connection(self):
        """Při příchozí zprávě od druhé instance se pokusí zobrazit hlavní okno."""
        if hasattr(self, 'window_callback') and self.window_callback:
            self.window_callback()

    def send_show_message(self):
        """Pokusí se poslat zprávu existující instanci, aby se zobrazila."""
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if socket.waitForConnected(1000):
            socket.write(b"show")
            socket.flush()
            socket.waitForBytesWritten(1000)
            socket.close()
            return True
        return False

    def set_window_callback(self, callback):
        self.window_callback = callback

# ================= MULTI-USER PODPORA =================
class UserManager:
    def __init__(self):
        self.users_file = USERS_FILE
        self.current_user = None
        self.load_users()
    
    def load_users(self):
        if not os.path.exists(self.users_file):
            self.users = {
                "admin": {
                    "password": hashlib.sha256("061004".encode()).hexdigest(),
                    "role": "admin",
                    "name": "Administrátor",
                    "created": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "last_login": None,
                    "cannot_delete": True,
                    "comment_color": "#FF0000"
                },
                "recepce1": {
                    "password": hashlib.sha256("recepce1".encode()).hexdigest(),
                    "role": "recepční",
                    "name": "Recepční 1",
                    "created": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "last_login": None,
                    "cannot_delete": False,
                    "comment_color": "#0000FF"
                },
                "recepce2": {
                    "password": hashlib.sha256("recepce2".encode()).hexdigest(),
                    "role": "recepční",
                    "name": "Recepční 2",
                    "created": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "last_login": None,
                    "cannot_delete": False,
                    "comment_color": "#008000"
                },
                "recepce3": {
                    "password": hashlib.sha256("recepce3".encode()).hexdigest(),
                    "role": "recepční",
                    "name": "Recepční 3",
                    "created": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "last_login": None,
                    "cannot_delete": False,
                    "comment_color": "#800080"
                }
            }
            self.save_users()
        else:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                self.users = json.load(f)
    
    def save_users(self):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)
    
    def authenticate(self, username, password):
        if username in self.users:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if self.users[username]["password"] == hashed_password:
                self.current_user = username
                self.users[username]["last_login"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                self.save_users()
                return True
        return False
    
    def has_permission(self, permission):
        if not self.current_user:
            return False
        user_data = self.users.get(self.current_user, {})
        if user_data.get("role") == "admin":
            return True
        return permission in user_data.get("permissions", [])
    
    def add_user(self, username, password, role, name):
        if username in self.users:
            return False
        self.users[username] = {
            "password": hashlib.sha256(password.encode()).hexdigest(),
            "role": role,
            "name": name,
            "created": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "last_login": None,
            "cannot_delete": False,
            "comment_color": "#000000"
        }
        self.save_users()
        return True
    
    def delete_user(self, username):
        if username in self.users and not self.users[username].get("cannot_delete", False):
            del self.users[username]
            self.save_users()
            return True
        return False

class LoginDialog(QDialog):
    def __init__(self, user_manager):
        super().__init__()
        self.user_manager = user_manager
        self.setWindowTitle("Přihlášení - HEM Komunikace")
        self.setFixedWidth(400)
        self.setFixedHeight(300)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        header_label = QLabel("HEM - Komunikační modul")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        version_label = QLabel("Verze 0.4.2")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: gray;")
        layout.addWidget(version_label)
        
        layout.addSpacing(20)
        
        layout.addWidget(QLabel("Uživatelské jméno:"))
        self.username_edit = QLineEdit()
        layout.addWidget(self.username_edit)
        
        layout.addWidget(QLabel("Heslo:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.returnPressed.connect(self.login)
        layout.addWidget(self.password_edit)
        
        layout.addSpacing(20)
        
        button_layout = QHBoxLayout()
        login_button = QPushButton("Přihlásit")
        cancel_button = QPushButton("Zrušit")
        
        login_button.setDefault(True)
        login_button.setAutoDefault(True)
        login_button.clicked.connect(self.login)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(login_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.username_edit.setFocus()
    
    def login(self):
        username = self.username_edit.text()
        password = self.password_edit.text()
        
        if self.user_manager.authenticate(username, password):
            self.accept()
        else:
            QMessageBox.warning(self, "Chyba", "Neplatné přihlašovací údaje")
            self.password_edit.clear()
            self.password_edit.setFocus()

# ================= NOVÁ FUNKCE PRO OPAKOVÁNÍ ÚKOLŮ (OPRAVENO) =================
def is_task_due_on_date(task, date_qdate):
    """Rozhodne, zda má být úkol (s novým formátem opakování) zobrazen k danému datu.
       Opraveno: kontroluje, zda je recurrence platný slovník s klíčem 'type'."""
    rec = task.get("recurrence")
    if not rec or not isinstance(rec, dict) or "type" not in rec:
        # Pokud chybí validní opakování, chová se jako jednorázový úkol
        return task.get("due_date") == date_qdate.toString("dd.MM.yyyy")
    
    start_date = datetime.strptime(task["due_date"], "%d.%m.%Y").date()
    target_date = date_qdate.toPython()
    
    if target_date < start_date:
        return False
    
    end_date = None
    if rec.get("end_date"):
        end_date = datetime.strptime(rec["end_date"], "%d.%m.%Y").date()
        if target_date > end_date:
            return False
    
    if rec["type"] == "weekly":
        weekdays = rec.get("days", [])
        if not weekdays:
            return False
        if target_date.weekday() not in weekdays:
            return False
        return True
    elif rec["type"] == "interval":
        interval = rec.get("interval", 1)
        if interval <= 0:
            interval = 1
        delta = (target_date - start_date).days
        return delta % interval == 0
    
    return False

def get_tasks_for_date(date_qdate, tasks, completions):
    """Vrátí seznam úkolů (včetně opakovaných) pro dané datum. Každý úkol je slovník obsahující
       původní data plus 'occurrence_date' a 'completed' (podle completions)."""
    result = []
    date_str = date_qdate.toString("dd.MM.yyyy")
    for task in tasks:
        if not task.get("recurrence") or not isinstance(task.get("recurrence"), dict):
            if task["due_date"] == date_str:
                completed = task.get("completed", False)
                result.append({
                    "id": task["id"],
                    "title": task["title"],
                    "description": task.get("description", ""),
                    "assigned_to": task.get("assigned_to", "all"),
                    "priority": task.get("priority", "Normální"),
                    "due_date": date_str,
                    "completed": completed,
                    "recurrence": None,
                    "occurrence_date": date_str,
                    "original_task": task
                })
        else:
            if is_task_due_on_date(task, date_qdate):
                occ_id = f"{task['id']}_{date_str}"
                sid = str(task["id"])
                completed = occ_id in completions.get(sid, {})
                result.append({
                    "id": task["id"],
                    "title": task["title"],
                    "description": task.get("description", ""),
                    "assigned_to": task.get("assigned_to", "all"),
                    "priority": task.get("priority", "Normální"),
                    "due_date": date_str,
                    "completed": completed,
                    "recurrence": task["recurrence"],
                    "occurrence_date": date_str,
                    "original_task": task
                })
    return result

def toggle_task_completion(task_occ, user_manager):
    """Změna stavu splnění výskytu úkolu (jednorázového nebo opakovaného)."""
    tasks = load_tasks()
    completions = load_task_completions()
    if task_occ["recurrence"] is None:
        for t in tasks:
            if t["id"] == task_occ["id"]:
                t["completed"] = not t.get("completed", False)
                if t["completed"]:
                    t["completed_date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                    t["completed_by"] = user_manager.current_user
                else:
                    t["completed_date"] = None
                    t["completed_by"] = None
                break
        save_tasks(tasks)
    else:
        task_id = str(task_occ["id"])
        occ_date = task_occ["occurrence_date"]
        if task_id not in completions:
            completions[task_id] = {}
        if occ_date in completions[task_id]:
            del completions[task_id][occ_date]
        else:
            completions[task_id][occ_date] = {
                "completed_by": user_manager.current_user,
                "completed_at": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
        save_task_completions(completions)

def delete_task_permanently(task_id, is_recurring):
    """Odstraní úkol (jednorázový nebo celý opakovaný) včetně všech záznamů o splnění."""
    tasks = load_tasks()
    tasks = [t for t in tasks if t["id"] != task_id]
    save_tasks(tasks)
    if is_recurring:
        completions = load_task_completions()
        if str(task_id) in completions:
            del completions[str(task_id)]
            save_task_completions(completions)

# ================= 1. KALENDÁŘ S ÚKOLY =================
class CalendarDialog(QDialog):
    def __init__(self, user_manager):
        super().__init__()
        self.user_manager = user_manager
        self.setWindowTitle("Kalendář s úkoly")
        self.setMinimumSize(900, 500)
        
        self.current_date = QDate.currentDate()
        self.selected_date = QDate.currentDate()
        self.init_ui()
        self.load_calendar()
        self.load_tasks_for_date(self.selected_date)
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        
        self.prev_month_btn = QPushButton("◀")
        self.prev_month_btn.clicked.connect(self.prev_month)
        
        self.month_label = QLabel()
        self.month_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        self.next_month_btn = QPushButton("▶")
        self.next_month_btn.clicked.connect(self.next_month)
        
        self.today_btn = QPushButton("Dnes")
        self.today_btn.clicked.connect(self.go_to_today)
        
        header_layout.addWidget(self.prev_month_btn)
        header_layout.addWidget(self.month_label)
        header_layout.addWidget(self.next_month_btn)
        header_layout.addStretch()
        header_layout.addWidget(self.today_btn)
        
        layout.addLayout(header_layout)
        
        splitter = QSplitter(Qt.Horizontal)
        
        calendar_widget = QWidget()
        calendar_layout = QVBoxLayout()
        
        self.calendar_table = QTableWidget()
        self.calendar_table.setColumnCount(7)
        self.calendar_table.setHorizontalHeaderLabels(["Po", "Út", "St", "Čt", "Pá", "So", "Ne"])
        self.calendar_table.verticalHeader().setVisible(False)
        self.calendar_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.calendar_table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        for i in range(7):
            self.calendar_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        
        self.calendar_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.calendar_table.cellClicked.connect(self.on_date_clicked)
        self.calendar_table.cellDoubleClicked.connect(self.on_date_double_clicked)
        
        calendar_layout.addWidget(self.calendar_table, 1)
        
        self.add_task_btn = QPushButton("➕ Přidat úkol pro vybraný den")
        self.add_task_btn.clicked.connect(self.add_task_for_selected_date)
        self.add_task_btn.setEnabled(False)
        calendar_layout.addWidget(self.add_task_btn)
        
        calendar_widget.setLayout(calendar_layout)
        
        tasks_widget = QWidget()
        tasks_layout = QVBoxLayout()
        
        self.selected_date_label = QLabel("Vyberte datum")
        self.selected_date_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        tasks_layout.addWidget(self.selected_date_label)
        
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(3)  # Pouze Stav, Název, Akce
        self.tasks_table.setHorizontalHeaderLabels(["Stav", "Název", "Akce"])
        self.tasks_table.horizontalHeader().setStretchLastSection(True)
        self.tasks_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tasks_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tasks_table.cellDoubleClicked.connect(self.on_task_double_clicked)  # Otevření detailu
        tasks_layout.addWidget(self.tasks_table, 1)
        
        stats_label = QLabel("Statistiky:")
        stats_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        tasks_layout.addWidget(stats_label)
        
        self.stats_label = QLabel("Vyberte datum pro zobrazení statistik")
        tasks_layout.addWidget(self.stats_label)
        
        tasks_widget.setLayout(tasks_layout)
        
        splitter.addWidget(calendar_widget)
        splitter.addWidget(tasks_widget)
        splitter.setSizes([600, 300])
        
        layout.addWidget(splitter, 1)
        self.setLayout(layout)
    
    def load_calendar(self):
        month_names = ["Leden", "Únor", "Březen", "Duben", "Květen", "Červen", 
                      "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]
        month_name = month_names[self.current_date.month() - 1]
        self.month_label.setText(f"{month_name} {self.current_date.year()}")
        
        first_day = QDate(self.current_date.year(), self.current_date.month(), 1)
        first_day_weekday = first_day.dayOfWeek()
        days_in_month = self.current_date.daysInMonth()
        
        rows_needed = 6
        self.calendar_table.setRowCount(rows_needed)
        self.calendar_table.setColumnCount(7)
        
        for row in range(rows_needed):
            self.calendar_table.setRowHeight(row, 80)
        
        for row in range(rows_needed):
            for col in range(7):
                if self.calendar_table.item(row, col):
                    self.calendar_table.setItem(row, col, None)
        
        day = 1
        tasks = load_tasks()
        completions = load_task_completions()
        for row in range(rows_needed):
            for col in range(7):
                if row == 0 and col < first_day_weekday - 1:
                    continue
                
                if day > days_in_month:
                    break
                
                current_qdate = QDate(self.current_date.year(), self.current_date.month(), day)
                day_tasks = get_tasks_for_date(current_qdate, tasks, completions)
                
                day_item = QTableWidgetItem(str(day))
                day_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
                
                if day_tasks:
                    task_text = f"{day}\n"
                    for t in day_tasks[:3]:
                        task_text += f"• {t['title']}\n"
                    if len(day_tasks) > 3:
                        task_text += "..."
                    day_item.setText(task_text)
                
                today = QDate.currentDate()
                if (self.current_date.year() == today.year() and 
                    self.current_date.month() == today.month() and 
                    day == today.day()):
                    day_item.setBackground(QColor(230, 247, 255))
                    day_item.setForeground(QColor(0, 0, 0))
                
                if (self.current_date.year() == self.selected_date.year() and 
                    self.current_date.month() == self.selected_date.month() and 
                    day == self.selected_date.day()):
                    day_item.setBackground(QColor(200, 230, 255))
                
                self.calendar_table.setItem(row, col, day_item)
                day += 1
        
        for row in range(rows_needed):
            empty = True
            for col in range(7):
                if self.calendar_table.item(row, col) and self.calendar_table.item(row, col).text():
                    empty = False
                    break
            self.calendar_table.setRowHidden(row, empty)
    
    def get_tasks_for_day(self, day):
        date_qdate = QDate(self.current_date.year(), self.current_date.month(), day)
        tasks = load_tasks()
        completions = load_task_completions()
        day_tasks = get_tasks_for_date(date_qdate, tasks, completions)
        result = []
        for t in day_tasks:
            title = t["title"]
            if len(title) > 15:
                title = title[:15] + "..."
            status = "✓" if t["completed"] else "✗"
            result.append(f"{status} {title}")
        return result
    
    def on_date_clicked(self, row, col):
        item = self.calendar_table.item(row, col)
        if item and item.text():
            day_text = item.text().split('\n')[0]
            try:
                day = int(day_text)
                self.selected_date = QDate(self.current_date.year(), self.current_date.month(), day)
                self.add_task_btn.setEnabled(True)
                self.load_tasks_for_date(self.selected_date)
                self.load_calendar()
            except:
                pass
    
    def on_date_double_clicked(self, row, col):
        item = self.calendar_table.item(row, col)
        if item and item.text():
            day_text = item.text().split('\n')[0]
            try:
                day = int(day_text)
                self.selected_date = QDate(self.current_date.year(), self.current_date.month(), day)
                self.add_task_for_selected_date()
            except:
                pass
    
    def load_tasks_for_date(self, date):
        date_str = date.toString("dd.MM.yyyy")
        self.selected_date_label.setText(f"Úkoly na {date_str}")
        
        tasks = load_tasks()
        completions = load_task_completions()
        date_tasks = get_tasks_for_date(date, tasks, completions)
        
        date_tasks.sort(key=lambda x: (
            x["completed"],
            {"Kritická": 0, "Vysoká": 1, "Normální": 2, "Nízká": 3}.get(x["priority"], 2)
        ))
        
        self.tasks_table.setRowCount(len(date_tasks))
        
        for i, task_occ in enumerate(date_tasks):
            status_item = QTableWidgetItem()
            if task_occ["completed"]:
                status_item.setText("✓")
                status_item.setForeground(QColor("green"))
            else:
                status_item.setText("✗")
                status_item.setForeground(QColor("red"))
            self.tasks_table.setItem(i, 0, status_item)
            
            title_text = task_occ["title"]
            if task_occ.get("recurrence"):
                title_text += " (opak.)"
            title_item = QTableWidgetItem(title_text)
            title_item.setData(Qt.UserRole, task_occ)  # Uložíme data pro detail
            self.tasks_table.setItem(i, 1, title_item)
            
            # Akční tlačítka: pouze toggle a delete
            button_widget = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(2, 2, 2, 2)
            
            toggle_btn = QPushButton("✓" if not task_occ["completed"] else "✗")
            toggle_btn.setFixedSize(30, 25)
            toggle_btn.clicked.connect(lambda checked, occ=task_occ: self.toggle_task_status(occ))
            
            delete_btn = QPushButton("🗑")
            delete_btn.setFixedSize(30, 25)
            delete_btn.clicked.connect(lambda checked, occ=task_occ: self.delete_task(occ))
            
            button_layout.addWidget(toggle_btn)
            button_layout.addWidget(delete_btn)
            button_widget.setLayout(button_layout)
            
            self.tasks_table.setCellWidget(i, 2, button_widget)
        
        self.tasks_table.resizeColumnsToContents()
        self.update_stats(date_tasks)
    
    def on_task_double_clicked(self, row, col):
        """Otevře detail úkolu v samostatném okně."""
        item = self.tasks_table.item(row, 1)  # Sloupec s názvem
        if item:
            task_occ = item.data(Qt.UserRole)
            if task_occ:
                dialog = TaskDetailDialog(task_occ, self.user_manager, self)
                if dialog.exec():
                    self.load_tasks_for_date(self.selected_date)
                    self.load_calendar()
    
    def update_stats(self, tasks):
        if not tasks:
            self.stats_label.setText("Žádné úkoly pro tento den")
            return
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t["completed"])
        pending = total - completed
        
        stats_text = f"Celkem: {total} | Splněno: {completed} | Čekající: {pending}"
        
        priorities = {}
        for task in tasks:
            priority = task["priority"]
            priorities[priority] = priorities.get(priority, 0) + 1
        
        if priorities:
            stats_text += "\nPriorita: "
            stats_text += ", ".join([f"{k}: {v}" for k, v in priorities.items()])
        
        self.stats_label.setText(stats_text)
    
    def toggle_task_status(self, task_occ):
        toggle_task_completion(task_occ, self.user_manager)
        self.load_tasks_for_date(self.selected_date)
        self.load_calendar()
    
    def delete_task(self, task_occ):
        is_recurring = task_occ.get("recurrence") is not None
        reply = QMessageBox.question(
            self, "Smazat úkol",
            f"Opravdu chcete smazat úkol '{task_occ['title']}'? (Pokud je opakovaný, smažou se všechny jeho výskyty)",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_task_permanently(task_occ["id"], is_recurring)
            self.load_tasks_for_date(self.selected_date)
            self.load_calendar()
    
    def add_task_for_selected_date(self):
        if not self.selected_date:
            QMessageBox.warning(self, "Chyba", "Vyberte nejprve datum")
            return
        
        dialog = TaskEditDialog(self.selected_date, self.user_manager, None)
        if dialog.exec():
            self.load_tasks_for_date(self.selected_date)
            self.load_calendar()
    
    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.load_calendar()
        self.add_task_btn.setEnabled(False)
        self.selected_date_label.setText("Vyberte datum")
        self.tasks_table.setRowCount(0)
        self.stats_label.setText("Vyberte datum pro zobrazení statistik")
    
    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.load_calendar()
        self.add_task_btn.setEnabled(False)
        self.selected_date_label.setText("Vyberte datum")
        self.tasks_table.setRowCount(0)
        self.stats_label.setText("Vyberte datum pro zobrazení statistik")
    
    def go_to_today(self):
        self.current_date = QDate.currentDate()
        self.selected_date = QDate.currentDate()
        self.load_calendar()
        self.add_task_btn.setEnabled(True)
        self.load_tasks_for_date(self.selected_date)


class TaskDetailDialog(QDialog):
    """Dialog pro zobrazení detailu úkolu s základními akcemi."""
    def __init__(self, task_occ, user_manager, parent_calendar):
        super().__init__(parent_calendar)
        self.task_occ = task_occ
        self.user_manager = user_manager
        self.calendar = parent_calendar
        self.setWindowTitle(f"Detail úkolu: {task_occ['title']}")
        self.setMinimumSize(450, 350)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        title_label = QLabel(self.task_occ["title"])
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        info_layout = QFormLayout()
        
        # Priorita
        priority = self.task_occ.get("priority", "Normální")
        info_layout.addRow("Priorita:", QLabel(priority))
        
        # Přiřazeno
        assigned_to = self.task_occ.get("assigned_to", "all")
        if assigned_to == "all":
            assigned_text = "Všichni"
        else:
            assigned_text = self.user_manager.users.get(assigned_to, {}).get("name", assigned_to)
        info_layout.addRow("Přiřazeno:", QLabel(assigned_text))
        
        # Opakování
        recurrence = self.task_occ.get("recurrence")
        if recurrence:
            if recurrence["type"] == "weekly":
                days = recurrence.get("days", [])
                day_names = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
                days_text = ", ".join([day_names[d] for d in days])
                rec_text = f"Každý týden: {days_text}"
                if recurrence.get("end_date"):
                    rec_text += f" (do {recurrence['end_date']})"
            elif recurrence["type"] == "interval":
                interval = recurrence.get("interval", 1)
                rec_text = f"Každých {interval} dní"
                if recurrence.get("end_date"):
                    rec_text += f" (do {recurrence['end_date']})"
        else:
            rec_text = "Jednorázový úkol"
        info_layout.addRow("Opakování:", QLabel(rec_text))
        
        layout.addLayout(info_layout)
        
        # Poznámka (popis)
        note_label = QLabel("Poznámka:")
        note_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(note_label)
        self.note_edit = QTextEdit()
        self.note_edit.setPlainText(self.task_occ.get("description", ""))
        self.note_edit.setReadOnly(True)
        layout.addWidget(self.note_edit)
        
        # Tlačítka akcí
        btn_layout = QHBoxLayout()
        
        self.toggle_btn = QPushButton("✓ Splnit" if not self.task_occ["completed"] else "✗ Zrušit splnění")
        self.toggle_btn.clicked.connect(self.toggle_status)
        
        self.delete_btn = QPushButton("🗑 Smazat")
        self.delete_btn.clicked.connect(self.delete_task)
        
        close_btn = QPushButton("Zavřít")
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.toggle_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def toggle_status(self):
        toggle_task_completion(self.task_occ, self.user_manager)
        self.calendar.load_tasks_for_date(self.calendar.selected_date)
        self.calendar.load_calendar()
        self.accept()  # Zavřít po změně
    
    def delete_task(self):
        is_recurring = self.task_occ.get("recurrence") is not None
        reply = QMessageBox.question(
            self, "Smazat úkol",
            f"Opravdu chcete smazat úkol '{self.task_occ['title']}'?\n(Pokud je opakovaný, smažou se všechny výskyty)",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_task_permanently(self.task_occ["id"], is_recurring)
            self.calendar.load_tasks_for_date(self.calendar.selected_date)
            self.calendar.load_calendar()
            self.accept()


# ================= 2. VZKAZY S FORMÁTOVÁNÍM TEXTU =================
class EmailInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Informace pro další den")
        self.setFixedWidth(300)
        layout = QFormLayout()
        
        self.breakfasts_spin = QSpinBox()
        self.breakfasts_spin.setRange(0, 500)
        self.breakfasts_spin.setValue(0)
        layout.addRow("Počet snídaní:", self.breakfasts_spin)
        
        self.arrivals_spin = QSpinBox()
        self.arrivals_spin.setRange(0, 100)
        self.arrivals_spin.setValue(0)
        layout.addRow("Počet příjezdů:", self.arrivals_spin)
        
        self.departures_spin = QSpinBox()
        self.departures_spin.setRange(0, 100)
        self.departures_spin.setValue(0)
        layout.addRow("Počet odjezdů:", self.departures_spin)
        
        self.stayovers_spin = QSpinBox()
        self.stayovers_spin.setRange(0, 100)
        self.stayovers_spin.setValue(0)
        layout.addRow("Počet průběhů:", self.stayovers_spin)
        
        self.wellnesses_spin = QSpinBox()
        self.wellnesses_spin.setRange(0, 100)
        self.wellnesses_spin.setValue(0)
        layout.addRow("Počet wellness:", self.wellnesses_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def get_arrivals(self):
        return self.arrivals_spin.value()
    
    def get_departures(self):
        return self.departures_spin.value()
    
    def get_stayovers(self):
        return self.stayovers_spin.value()
    
    def get_wellnesses(self):
        return self.wellnesses_spin.value()
    
    def get_breakfasts(self):
        return self.breakfasts_spin.value()

class MessagesDialog(QDialog):
    def __init__(self, user_manager, parent_window=None):
        super().__init__()
        self.user_manager = user_manager
        self.parent_window = parent_window
        self.setWindowTitle("Vzkazy")
        self.setMinimumSize(800, 400)
        
        self.messages = load_messages()
        self.init_ui()
        self.load_today_message()
        self.load_history()
        
        self.failsafe_timer = QTimer()
        self.failsafe_timer.timeout.connect(self.failsafe_save)
        self.failsafe_timer.start(60000)
        
        self.last_saved_text = self.today_edit.toPlainText()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        today_group = QGroupBox(f"Dnešní vzkaz ({datetime.now().strftime('%d.%m.%Y')})")
        today_layout = QVBoxLayout()
        
        self.today_edit = QTextEdit()
        self.today_edit.setPlaceholderText("Napište vzkaz pro dnešní den...")
        
        format_toolbar = QHBoxLayout()
        
        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setToolTip("Tučné (Ctrl+B)")
        self.bold_btn.setCheckable(True)
        self.bold_btn.clicked.connect(self.toggle_bold)
        
        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setToolTip("Kurzíva (Ctrl+I)")
        self.italic_btn.setCheckable(True)
        self.italic_btn.clicked.connect(self.toggle_italic)
        
        self.underline_btn = QToolButton()
        self.underline_btn.setText("U")
        self.underline_btn.setToolTip("Podtržení (Ctrl+U)")
        self.underline_btn.setCheckable(True)
        self.underline_btn.clicked.connect(self.toggle_underline)
        
        self.color_btn = QPushButton("🎨")
        self.color_btn.setToolTip("Barva textu")
        self.color_btn.clicked.connect(self.format_color)
        
        self.clear_format_btn = QPushButton("🧹")
        self.clear_format_btn.setToolTip("Vymazat formátování")
        self.clear_format_btn.clicked.connect(self.clear_formatting)
        
        self.emoji_btn = QToolButton()
        self.emoji_btn.setText("😀")
        self.emoji_btn.setToolTip("Vložit smajlík")
        self.emoji_btn.setPopupMode(QToolButton.InstantPopup)
        emoji_menu = QMenu(self.emoji_btn)
        
        emojis = ["🙂", "😀", "😁", "🤣", "☹️", "🙃", "😢", "💩", "👽", "🤮"]
        for emoji in emojis:
            action = QAction(emoji, self)
            action.triggered.connect(lambda checked, e=emoji: self.insert_emoji(e))
            emoji_menu.addAction(action)
        
        self.emoji_btn.setMenu(emoji_menu)
        
        format_toolbar.addWidget(self.bold_btn)
        format_toolbar.addWidget(self.italic_btn)
        format_toolbar.addWidget(self.underline_btn)
        format_toolbar.addWidget(self.color_btn)
        format_toolbar.addWidget(self.clear_format_btn)
        format_toolbar.addWidget(self.emoji_btn)
        format_toolbar.addStretch()
        
        today_layout.addLayout(format_toolbar)
        today_layout.addWidget(self.today_edit)
        
        bold_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        bold_shortcut.activated.connect(self.toggle_bold_shortcut)
        
        italic_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        italic_shortcut.activated.connect(self.toggle_italic_shortcut)
        
        underline_shortcut = QShortcut(QKeySequence("Ctrl+U"), self)
        underline_shortcut.activated.connect(self.toggle_underline_shortcut)
        
        self.today_edit.cursorPositionChanged.connect(self.update_format_buttons)
        
        today_buttons = QHBoxLayout()
        self.btn_save_today = QPushButton("Uložit dnešní vzkaz")
        
        self.btn_save_today.clicked.connect(self.save_today_message)
        
        today_buttons.addWidget(self.btn_save_today)
        today_buttons.addStretch()
        
        today_layout.addLayout(today_buttons)
        today_group.setLayout(today_layout)
        layout.addWidget(today_group)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Vyhledávání:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte klíčové slovo (host, rezervace, jméno...)")
        self.search_edit.textChanged.connect(self.search_messages)
        search_layout.addWidget(self.search_edit, 1)
        
        clear_search_btn = QPushButton("X")
        clear_search_btn.setToolTip("Vymazat vyhledávání")
        clear_search_btn.setFixedWidth(30)
        clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_search_btn)
        
        layout.addLayout(search_layout)
        
        history_group = QGroupBox("Historie vzkazů (nejnovější nahoře)")
        history_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["Datum", "Uživatel", "Náhled"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.doubleClicked.connect(self.load_selected_message)
        
        history_layout.addWidget(self.history_table, 1)
        
        history_buttons = QHBoxLayout()
        self.btn_copy_to_today = QPushButton("Kopírovat do dnešního")
        self.btn_delete_history = QPushButton("Smazat vybraný")
        self.btn_email = QPushButton("Odeslat e-mailem")
        self.btn_export = QPushButton("Exportovat do textu")
        
        self.btn_copy_to_today.clicked.connect(self.copy_to_today)
        self.btn_delete_history.clicked.connect(self.delete_history_message)
        self.btn_email.clicked.connect(self.send_email)
        self.btn_export.clicked.connect(self.export_messages)
        
        history_buttons.addWidget(self.btn_copy_to_today)
        history_buttons.addWidget(self.btn_delete_history)
        history_buttons.addWidget(self.btn_email)
        history_buttons.addStretch()
        history_buttons.addWidget(self.btn_export)
        
        history_layout.addLayout(history_buttons)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group, 1)
        
        self.setLayout(layout)
    
    def insert_emoji(self, emoji):
        cursor = self.today_edit.textCursor()
        cursor.insertText(emoji)
        self.today_edit.setTextCursor(cursor)
    
    def failsafe_save(self):
        current_text = self.today_edit.toPlainText().strip()
        if current_text != self.last_saved_text and current_text:
            self.save_today_message(silent=True)
            self.last_saved_text = current_text
    
    def search_messages(self):
        search_text = self.search_edit.text().strip().lower()
        if not search_text:
            self.load_history()
            return
        
        filtered_messages = []
        for msg in self.messages:
            search_fields = [
                msg["date"],
                msg["user"],
                msg["content"].lower()
            ]
            
            if any(search_text in field for field in search_fields):
                filtered_messages.append(msg)
        
        self.history_table.setRowCount(len(filtered_messages))
        for i, msg in enumerate(filtered_messages):
            self.history_table.setItem(i, 0, QTableWidgetItem(msg["date"]))
            self.history_table.setItem(i, 1, QTableWidgetItem(msg["user"]))
            
            preview = msg["content"]
            if len(preview) > 100:
                preview = preview[:100] + "..."
            
            if search_text in preview.lower():
                preview = preview.replace(search_text, f"<b>{search_text}</b>")
            
            self.history_table.setItem(i, 2, QTableWidgetItem(preview))
        
        self.history_table.resizeColumnsToContents()
    
    def clear_search(self):
        self.search_edit.clear()
        self.load_history()
    
    def update_format_buttons(self):
        cursor = self.today_edit.textCursor()
        format = cursor.charFormat()
        
        self.bold_btn.setChecked(format.fontWeight() == QFont.Bold)
        self.italic_btn.setChecked(format.fontItalic())
        self.underline_btn.setChecked(format.fontUnderline())
    
    def toggle_bold(self):
        cursor = self.today_edit.textCursor()
        format = cursor.charFormat()
        
        if cursor.hasSelection():
            new_format = QTextCharFormat()
            new_format.setFontWeight(QFont.Bold if format.fontWeight() != QFont.Bold else QFont.Normal)
            cursor.mergeCharFormat(new_format)
        else:
            format.setFontWeight(QFont.Bold if format.fontWeight() != QFont.Bold else QFont.Normal)
            cursor.setCharFormat(format)
            self.today_edit.setTextCursor(cursor)
        
        self.update_format_buttons()
    
    def toggle_italic(self):
        cursor = self.today_edit.textCursor()
        format = cursor.charFormat()
        
        if cursor.hasSelection():
            new_format = QTextCharFormat()
            new_format.setFontItalic(not format.fontItalic())
            cursor.mergeCharFormat(new_format)
        else:
            format.setFontItalic(not format.fontItalic())
            cursor.setCharFormat(format)
            self.today_edit.setTextCursor(cursor)
        
        self.update_format_buttons()
    
    def toggle_underline(self):
        cursor = self.today_edit.textCursor()
        format = cursor.charFormat()
        
        if cursor.hasSelection():
            new_format = QTextCharFormat()
            new_format.setFontUnderline(not format.fontUnderline())
            cursor.mergeCharFormat(new_format)
        else:
            format.setFontUnderline(not format.fontUnderline())
            cursor.setCharFormat(format)
            self.today_edit.setTextCursor(cursor)
        
        self.update_format_buttons()
    
    def toggle_bold_shortcut(self):
        self.bold_btn.click()
    
    def toggle_italic_shortcut(self):
        self.italic_btn.click()
    
    def toggle_underline_shortcut(self):
        self.underline_btn.click()
    
    def format_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            cursor = self.today_edit.textCursor()
            
            if cursor.hasSelection():
                new_format = QTextCharFormat()
                new_format.setForeground(color)
                cursor.mergeCharFormat(new_format)
            else:
                format = cursor.charFormat()
                format.setForeground(color)
                cursor.setCharFormat(format)
                self.today_edit.setTextCursor(cursor)
    
    def clear_formatting(self):
        cursor = self.today_edit.textCursor()
        
        if cursor.hasSelection():
            new_format = QTextCharFormat()
            cursor.mergeCharFormat(new_format)
        else:
            format = QTextCharFormat()
            cursor.setCharFormat(format)
            self.today_edit.setTextCursor(cursor)
        
        self.update_format_buttons()
    
    def load_today_message(self):
        today = datetime.now().strftime("%d.%m.%Y")
        user = self.user_manager.current_user
        for msg in self.messages:
            if msg["date"] == today and msg["user"] == user:
                self.today_edit.setHtml(msg.get("content_html", msg["content"]))
                self.last_saved_text = self.today_edit.toPlainText()
                return
        self.today_edit.clear()
        self.last_saved_text = ""
    
    def save_today_message(self, silent=False):
        today = datetime.now().strftime("%d.%m.%Y")
        user = self.user_manager.current_user
        content_html = self.today_edit.toHtml()
        content_plain = self.today_edit.toPlainText().strip()
        
        self.messages = [msg for msg in self.messages if not (msg["date"] == today and msg["user"] == user)]
        
        if content_plain:
            new_msg = {
                "date": today,
                "user": user,
                "content": content_plain,
                "content_html": content_html
            }
            self.messages.append(new_msg)
        
        save_messages(self.messages)
        self.load_history()
        self.last_saved_text = content_plain
        
        if self.parent_window and hasattr(self.parent_window, 'dashboard'):
            self.parent_window.dashboard.load_data()
        
        if not silent:
            QMessageBox.information(self, "Hotovo", "Dnešní vzkaz byl uložen.")
    
    def load_history(self):
        sorted_messages = sorted(self.messages, key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"), reverse=True)
        
        self.history_table.setRowCount(len(sorted_messages))
        for i, msg in enumerate(sorted_messages):
            self.history_table.setItem(i, 0, QTableWidgetItem(msg["date"]))
            self.history_table.setItem(i, 1, QTableWidgetItem(msg["user"]))
            
            preview = msg["content"]
            if len(preview) > 100:
                preview = preview[:100] + "..."
            
            if "💬" in preview:
                preview = "💬 " + preview
            
            self.history_table.setItem(i, 2, QTableWidgetItem(preview))
        
        self.history_table.resizeColumnsToContents()
    
    def load_selected_message(self):
        selected = self.history_table.currentRow()
        if selected >= 0:
            date_item = self.history_table.item(selected, 0)
            user_item = self.history_table.item(selected, 1)
            if date_item and user_item:
                date = date_item.text()
                user = user_item.text()
                for msg in self.messages:
                    if msg["date"] == date and msg["user"] == user:
                        self.show_message_dialog(msg, date, user)
                        break
    
    def show_message_dialog(self, msg, date, user):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Vzkaz z {date} - {user}")
        dlg.setFixedSize(700, 500)
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setHtml(msg.get("content_html", msg["content"]))
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit, 1)
        
        comments_group = QGroupBox("Komentáře")
        comments_layout = QVBoxLayout()
        
        self.comments_list = QListWidget()
        
        content = msg.get("content", "")
        comments = []
        lines = content.split('\n')
        for line in lines:
            if '💬' in line:
                comments.append(line)
        
        if comments:
            for comment in comments:
                self.comments_list.addItem(comment)
        else:
            self.comments_list.addItem("Žádné komentáře")
        
        comments_layout.addWidget(self.comments_list)
        
        comment_buttons = QHBoxLayout()
        
        btn_add_comment = QPushButton("Přidat komentář")
        btn_edit_comment = QPushButton("Upravit komentář")
        btn_delete_comment = QPushButton("Smazat komentář")
        
        btn_add_comment.clicked.connect(lambda: self.add_comment_to_message(msg, dlg))
        btn_edit_comment.clicked.connect(lambda: self.edit_selected_comment(msg, dlg))
        btn_delete_comment.clicked.connect(lambda: self.delete_selected_comment(msg, dlg))
        
        comment_buttons.addWidget(btn_add_comment)
        comment_buttons.addWidget(btn_edit_comment)
        comment_buttons.addWidget(btn_delete_comment)
        
        comments_layout.addLayout(comment_buttons)
        comments_group.setLayout(comments_layout)
        layout.addWidget(comments_group)
        
        btn_close = QPushButton("Zavřít")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)
        
        dlg.setLayout(layout)
        dlg.exec()
    
    def add_comment_to_message(self, msg, parent_dialog):
        user_data = self.user_manager.users.get(self.user_manager.current_user, {})
        comment_color = user_data.get("comment_color", "#000000")
        
        comment_dialog = QDialog(parent_dialog)
        comment_dialog.setWindowTitle("Přidat komentář")
        comment_dialog.setFixedWidth(400)
        layout = QVBoxLayout()
        
        comment_label = QLabel("Komentář (bude přidán na konec vzkazu tučně a barvou):")
        layout.addWidget(comment_label)
        
        comment_edit = QTextEdit()
        comment_edit.setMaximumHeight(100)
        layout.addWidget(comment_edit)
        
        color_label = QLabel(f"Barva komentáře: {comment_color}")
        color_label.setStyleSheet(f"color: {comment_color}; font-weight: bold;")
        layout.addWidget(color_label)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self.save_comment(msg, comment_edit.toPlainText(), comment_color, comment_dialog, parent_dialog))
        buttons.rejected.connect(comment_dialog.reject)
        layout.addWidget(buttons)
        
        comment_dialog.setLayout(layout)
        comment_dialog.exec()
    
    def edit_selected_comment(self, msg, parent_dialog):
        selected_item = self.comments_list.currentItem()
        if not selected_item or selected_item.text() == "Žádné komentáře":
            QMessageBox.warning(parent_dialog, "Chyba", "Vyberte komentář k úpravě")
            return
        
        comment_text = selected_item.text()
        
        if '💬' in comment_text:
            parts = comment_text.split(']:')
            if len(parts) > 1:
                original_comment = parts[1].strip()
            else:
                original_comment = comment_text.replace('💬', '').strip()
        else:
            original_comment = comment_text
        
        user_data = self.user_manager.users.get(self.user_manager.current_user, {})
        comment_color = user_data.get("comment_color", "#000000")
        
        edit_dialog = QDialog(parent_dialog)
        edit_dialog.setWindowTitle("Upravit komentář")
        edit_dialog.setFixedWidth(400)
        layout = QVBoxLayout()
        
        edit_label = QLabel("Upravit komentář:")
        layout.addWidget(edit_label)
        
        comment_edit = QTextEdit()
        comment_edit.setPlainText(original_comment)
        comment_edit.setMaximumHeight(100)
        layout.addWidget(comment_edit)
        
        color_label = QLabel(f"Barva komentáře: {comment_color}")
        color_label.setStyleSheet(f"color: {comment_color}; font-weight: bold;")
        layout.addWidget(color_label)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self.update_comment(msg, comment_text, comment_edit.toPlainText(), comment_color, edit_dialog, parent_dialog))
        buttons.rejected.connect(edit_dialog.reject)
        layout.addWidget(buttons)
        
        edit_dialog.setLayout(layout)
        edit_dialog.exec()
    
    def delete_selected_comment(self, msg, parent_dialog):
        selected_item = self.comments_list.currentItem()
        if not selected_item or selected_item.text() == "Žádné komentáře":
            QMessageBox.warning(parent_dialog, "Chyba", "Vyberte komentář ke smazání")
            return
        
        comment_text = selected_item.text()
        
        reply = QMessageBox.question(
            parent_dialog, 
            "Smazat komentář", 
            f"Opravdu chcete smazat komentář:\n{comment_text}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.remove_comment(msg, comment_text, parent_dialog)
    
    def save_comment(self, msg, comment_text, color, comment_dialog, parent_dialog):
        if not comment_text.strip():
            QMessageBox.warning(comment_dialog, "Chyba", "Zadejte komentář")
            return
        
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        user_name = self.user_manager.users[self.user_manager.current_user]["name"]
        
        comment_html = f'<br><span style="color: {color}; font-weight: bold;">💬 [{timestamp} - {user_name}]: {comment_text}</span>'
        
        msg["content_html"] = msg.get("content_html", msg["content"]) + comment_html
        msg["content"] = msg["content"] + f"\n💬 [{timestamp} - {user_name}]: {comment_text}"
        
        save_messages(self.messages)
        self.load_history()
        
        QMessageBox.information(comment_dialog, "Hotovo", "Komentář byl přidán.")
        comment_dialog.accept()
        parent_dialog.accept()
        
        self.load_selected_message()
    
    def update_comment(self, msg, old_comment, new_comment_text, color, edit_dialog, parent_dialog):
        if not new_comment_text.strip():
            QMessageBox.warning(edit_dialog, "Chyba", "Zadejte komentář")
            return
        
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        user_name = self.user_manager.users[self.user_manager.current_user]["name"]
        
        old_comment_plain = old_comment.replace('💬 ', '')
        
        if old_comment_plain in msg["content"]:
            new_comment_line = f"💬 [{timestamp} - {user_name}]: {new_comment_text}"
            msg["content"] = msg["content"].replace(old_comment_plain, new_comment_line)
        
        new_comment_html = f'<br><span style="color: {color}; font-weight: bold;">💬 [{timestamp} - {user_name}]: {new_comment_text}</span>'
        
        lines = msg["content"].split('\n')
        html_lines = []
        for line in lines:
            if '💬' in line and old_comment_plain in line:
                html_lines.append(new_comment_html.replace('<br>', ''))
            elif '💬' in line:
                parts = line.split(']:')
                if len(parts) > 1:
                    comment_text = parts[1].strip()
                    html_lines.append(f'<span style="color: {color}; font-weight: bold;">{line}</span>')
                else:
                    html_lines.append(line)
            else:
                html_lines.append(line)
        
        msg["content_html"] = '<br>'.join(html_lines)
        
        save_messages(self.messages)
        self.load_history()
        
        QMessageBox.information(edit_dialog, "Hotovo", "Komentář byl upraven.")
        edit_dialog.accept()
        parent_dialog.accept()
        
        self.load_selected_message()
    
    def remove_comment(self, msg, comment_text, parent_dialog):
        lines = msg["content"].split('\n')
        new_lines = []
        for line in lines:
            if line.strip() != comment_text.strip():
                new_lines.append(line)
        
        msg["content"] = '\n'.join(new_lines)
        
        html_lines = msg.get("content_html", "").split('<br>')
        new_html_lines = []
        for line in html_lines:
            if comment_text.strip() not in line:
                new_html_lines.append(line)
        
        msg["content_html"] = '<br>'.join(new_html_lines)
        
        save_messages(self.messages)
        self.load_history()
        
        QMessageBox.information(parent_dialog, "Hotovo", "Komentář byl smazán.")
        parent_dialog.accept()
        
        self.load_selected_message()
    
    def copy_to_today(self):
        selected = self.history_table.currentRow()
        if selected >= 0:
            date_item = self.history_table.item(selected, 0)
            user_item = self.history_table.item(selected, 1)
            if date_item and user_item:
                date = date_item.text()
                user = user_item.text()
                for msg in self.messages:
                    if msg["date"] == date and msg["user"] == user:
                        self.today_edit.setHtml(msg.get("content_html", msg["content"]))
                        self.update_format_buttons()
                        break
    
    def delete_history_message(self):
        selected = self.history_table.currentRow()
        if selected >= 0:
            date_item = self.history_table.item(selected, 0)
            user_item = self.history_table.item(selected, 1)
            if date_item and user_item:
                date = date_item.text()
                user = user_item.text()
                reply = QMessageBox.question(self, "Smazat vzkaz", 
                                           f"Opravdu chcete smazat vzkaz z {date} od {user}?",
                                           QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.messages = [msg for msg in self.messages if not (msg["date"] == date and msg["user"] == user)]
                    save_messages(self.messages)
                    self.load_history()
                    self.load_today_message()
                    
                    if self.parent_window and hasattr(self.parent_window, 'dashboard'):
                        self.parent_window.dashboard.load_data()
    
    def export_messages(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Uložit vzkazy", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("VZKAZY Z RECEPCE\n")
                f.write("=" * 50 + "\n\n")
                for msg in self.messages:
                    f.write(f"{msg['date']} - {msg['user']}:\n")
                    f.write(f"{msg['content']}\n")
                    f.write("-" * 50 + "\n\n")
            QMessageBox.information(self, "Export", "Vzkazy byly exportovány do textového souboru.")
    
    def send_email(self):
        recipients = load_email_recipients()
        active_recipients = [r for r in recipients if r.get("active", True)]
        
        if not active_recipients:
            QMessageBox.warning(self, "Chyba", "Není nastaven žádný aktivní příjemce e-mailu")
            return
        
        dlg = EmailInfoDialog(self)
        if not dlg.exec():
            return
        
        today = datetime.now().strftime("%d.%m.%Y")
        today_messages = [msg for msg in self.messages if msg["date"] == today]
        
        if not today_messages:
            reply = QMessageBox.question(self, "Žádné dnešní vzkazy", 
                                       "Pro dnešek nejsou žádné vzkazy. Chcete přesto odeslat e-mail?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
        
        messages_text = ""
        for msg in today_messages:
            messages_text += f"{msg['date']} - {msg['user']}:\n"
            messages_text += f"{msg['content']}\n\n"
        
        info_text = f"Počet snídaní: {dlg.get_breakfasts()}\n"
        info_text += f"Počet příjezdů: {dlg.get_arrivals()}\n"
        info_text += f"Počet odjezdů: {dlg.get_departures()}\n"
        info_text += f"Počet průběhů: {dlg.get_stayovers()}\n"
        info_text += f"Počet wellness: {dlg.get_wellnesses()}\n\n"
        
        full_text = info_text + messages_text
        
        email_body = settings.get("email_template", "").format(
            messages=full_text,
            user_name=self.user_manager.users[self.user_manager.current_user]["name"],
            date=datetime.now().strftime("%d.%m.%Y")
        )
        
        subject = settings.get("email_subject", "").format(
            date=datetime.now().strftime("%d.%m.%Y"),
            arrivals=dlg.get_arrivals(),
            stayovers=dlg.get_stayovers(),
            departures=dlg.get_departures(),
            wellnesses=dlg.get_wellnesses()
        )
        
        success = self.send_email_via_smtp(
            subject,
            email_body,
            [r["email"] for r in active_recipients]
        )
        
        if success:
            QMessageBox.information(self, "Hotovo", "Vzkazy byly odeslány e-mailem")
        else:
            QMessageBox.warning(self, "Chyba", "Nepodařilo se odeslat e-mail. Zkontrolujte nastavení SMTP.")
    
    def send_email_via_smtp(self, subject, body, recipients):
        try:
            smtp_server = settings.get("email_smtp_server", "")
            smtp_port = settings.get("email_smtp_port", 587)
            smtp_username = settings.get("email_smtp_username", "")
            smtp_password = settings.get("email_smtp_password", "")
            sender = settings.get("email_sender", "")
            
            if not all([smtp_server, smtp_username, smtp_password, sender]):
                return False
            
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Chyba při odesílání e-mailu: {e}")
            return False

    def refresh_messages(self):
        self.messages = load_messages()
        self.load_today_message()
        self.load_history()

# ================= 3. PENĚŽNÍ DENÍK =================
class CashDiaryDialog(QDialog):
    def __init__(self, user_manager):
        super().__init__()
        self.user_manager = user_manager
        self.setWindowTitle("Peněžní deník")
        self.setMinimumSize(800, 400)
        
        self.cash_data = load_cash_diary()
        self.shift_log = load_shift_log()
        self.init_ui()
        self.load_cash_data()
        self.check_today_status()
        self.load_existing_entry()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        cash_group = QGroupBox("Zapsat hotovost")
        cash_layout = QFormLayout()
        
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Datum:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.load_existing_entry)
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        cash_layout.addRow(date_layout)
        
        morning_layout = QHBoxLayout()
        morning_layout.addWidget(QLabel("Hotovost ráno:"))
        self.cash_start = QLineEdit()
        self.cash_start.setPlaceholderText("0")
        self.cash_start.setFixedWidth(100)
        morning_layout.addWidget(self.cash_start)
        morning_layout.addWidget(QLabel("Kč"))
        morning_layout.addStretch()
        cash_layout.addRow(morning_layout)
        
        evening_layout = QHBoxLayout()
        evening_layout.addWidget(QLabel("Hotovost večer:"))
        self.cash_end = QLineEdit()
        self.cash_end.setPlaceholderText("0")
        self.cash_end.setFixedWidth(100)
        evening_layout.addWidget(self.cash_end)
        evening_layout.addWidget(QLabel("Kč"))
        evening_layout.addStretch()
        cash_layout.addRow(evening_layout)
        
        self.cash_notes = QTextEdit()
        self.cash_notes.setMaximumHeight(60)
        self.cash_notes.setPlaceholderText("Poznámky...")
        cash_layout.addRow("Poznámky:", self.cash_notes)
        
        cash_buttons = QHBoxLayout()
        self.btn_save_cash = QPushButton("Uložit záznam")
        self.btn_save_cash.clicked.connect(self.save_cash_entry)
        cash_buttons.addWidget(self.btn_save_cash)
        cash_buttons.addStretch()
        
        cash_layout.addRow("", cash_buttons)
        cash_group.setLayout(cash_layout)
        layout.addWidget(cash_group)
        
        status_group = QGroupBox("Stav zapsání pro dnešek")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Načítám stav...")
        self.status_label.setStyleSheet("font-weight: bold; padding: 10px;")
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        history_group = QGroupBox("Historie peněžního deníku (nejnovější nahoře)")
        history_layout = QVBoxLayout()
        
        self.cash_table = QTableWidget()
        self.cash_table.setColumnCount(7)
        self.cash_table.setHorizontalHeaderLabels(["Datum", "Uživatel", "Typ směny", "Ráno", "Večer", "Rozdíl", "Akce"])
        self.cash_table.horizontalHeader().setStretchLastSection(True)
        self.cash_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cash_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        history_layout.addWidget(self.cash_table, 1)
        
        history_buttons = QHBoxLayout()
        self.btn_export_cash = QPushButton("Exportovat do CSV")
        self.btn_edit_cash = QPushButton("Upravit")
        self.btn_delete_cash = QPushButton("Smazat")
        
        self.btn_export_cash.clicked.connect(self.export_cash_data)
        self.btn_edit_cash.clicked.connect(self.edit_cash_entry)
        self.btn_delete_cash.clicked.connect(self.delete_cash_entry)
        
        history_buttons.addWidget(self.btn_export_cash)
        history_buttons.addWidget(self.btn_edit_cash)
        history_buttons.addWidget(self.btn_delete_cash)
        history_buttons.addStretch()
        
        history_layout.addLayout(history_buttons)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group, 1)
        
        self.setLayout(layout)
    
    def load_existing_entry(self):
        date_str = self.date_edit.date().toString("dd.MM.yyyy")
        
        existing_entry = None
        for entry in self.cash_data:
            if entry["date"] == date_str and entry["user"] == self.user_manager.current_user:
                existing_entry = entry
                break
        
        if existing_entry:
            self.cash_start.setText(str(existing_entry["cash_start"]) if existing_entry["cash_start"] != 0 else "")
            self.cash_end.setText(str(existing_entry["cash_end"]) if existing_entry["cash_end"] != 0 else "")
            self.cash_notes.setPlainText(existing_entry.get("notes", ""))
        else:
            self.cash_start.clear()
            self.cash_end.clear()
            self.cash_notes.clear()
    
    def check_today_status(self):
        status = check_cash_status()
        
        status_text = f"{status['stav']}\n{status['popis']}"
        self.status_label.setText(status_text)
        
        if status['barva'] == 'green':
            self.status_label.setStyleSheet("font-weight: bold; color: green; background-color: #e6ffe6; padding: 10px; border: 1px solid green;")
        elif status['barva'] == 'orange':
            self.status_label.setStyleSheet("font-weight: bold; color: orange; background-color: #fff7e6; padding: 10px; border: 1px solid orange;")
        elif status['barva'] == 'red':
            self.status_label.setStyleSheet("font-weight: bold; color: red; background-color: #ffe6e6; padding: 10px; border: 1px solid red;")
    
    def save_cash_entry(self):
        date_str = self.date_edit.date().toString("dd.MM.yyyy")
        
        existing_entry = None
        entry_index = -1
        for i, entry in enumerate(self.cash_data):
            if entry["date"] == date_str and entry["user"] == self.user_manager.current_user:
                existing_entry = entry
                entry_index = i
                break
        
        cash_start_text = self.cash_start.text().strip()
        cash_end_text = self.cash_end.text().strip()
        
        try:
            if cash_start_text:
                new_cash_start = float(cash_start_text.replace(",", "."))
            elif existing_entry:
                new_cash_start = existing_entry["cash_start"]
            else:
                new_cash_start = 0
        except ValueError:
            QMessageBox.warning(self, "Chyba", "Zadejte platnou částku pro hotovost ráno")
            return
        
        try:
            if cash_end_text:
                new_cash_end = float(cash_end_text.replace(",", "."))
            elif existing_entry:
                new_cash_end = existing_entry["cash_end"]
            else:
                new_cash_end = 0
        except ValueError:
            QMessageBox.warning(self, "Chyba", "Zadejte platnou částku pro hotovost večer")
            return
        
        shift_type = determine_shift_type(date_str, self.user_manager.current_user)
        
        if existing_entry:
            existing_entry.update({
                "cash_start": new_cash_start,
                "cash_end": new_cash_end,
                "difference": new_cash_end - new_cash_start,
                "notes": self.cash_notes.toPlainText(),
                "edited_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "edited_by": self.user_manager.current_user,
                "shift_type": shift_type
            })
        else:
            cash_entry = {
                "date": date_str,
                "user": self.user_manager.current_user,
                "shift_type": shift_type,
                "cash_start": new_cash_start,
                "cash_end": new_cash_end,
                "difference": new_cash_end - new_cash_start,
                "notes": self.cash_notes.toPlainText(),
                "recorded_at": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            
            self.cash_data.append(cash_entry)
        
        shift_record = {
            "user": self.user_manager.current_user,
            "shift_type": shift_type,
            "start_time": f"{date_str} 07:00",
            "end_time": f"{date_str} 23:00",
            "cash_start": new_cash_start,
            "cash_end": new_cash_end,
            "notes": self.cash_notes.toPlainText()
        }
        
        existing_shift = None
        shift_index = -1
        for i, shift in enumerate(self.shift_log):
            if (shift.get("start_time", "").startswith(date_str) and 
                shift.get("user") == self.user_manager.current_user):
                existing_shift = shift
                shift_index = i
                break
        
        if existing_shift:
            self.shift_log[shift_index] = shift_record
        else:
            self.shift_log.append(shift_record)
        
        save_shift_log(self.shift_log)
        save_cash_diary(self.cash_data)
        
        self.load_cash_data()
        self.check_today_status()
        
        QMessageBox.information(self, "Hotovo", "Záznam byl uložen")
    
    def load_cash_data(self):
        sorted_data = sorted(self.cash_data, 
                           key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"), 
                           reverse=True)
        
        self.cash_table.setRowCount(len(sorted_data))
        
        for i, entry in enumerate(sorted_data):
            self.cash_table.setItem(i, 0, QTableWidgetItem(entry["date"]))
            self.cash_table.setItem(i, 1, QTableWidgetItem(entry["user"]))
            self.cash_table.setItem(i, 2, QTableWidgetItem(entry.get("shift_type", "Celodenní")))
            self.cash_table.setItem(i, 3, QTableWidgetItem(f"{entry['cash_start']:,.0f} Kč".replace(",", " ")))
            self.cash_table.setItem(i, 4, QTableWidgetItem(f"{entry['cash_end']:,.0f} Kč".replace(",", " ")))
            
            difference = entry["difference"]
            diff_item = QTableWidgetItem(f"{difference:+,.0f} Kč".replace(",", " "))
            if difference > 0:
                diff_item.setForeground(QColor("green"))
            elif difference < 0:
                diff_item.setForeground(QColor("red"))
            self.cash_table.setItem(i, 5, diff_item)
            
            button_widget = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(2, 2, 2, 2)
            
            edit_btn = QPushButton("✏")
            edit_btn.setFixedSize(30, 25)
            edit_btn.setToolTip("Upravit záznam")
            edit_btn.clicked.connect(lambda checked, e=entry: self.edit_selected_entry(e))
            
            delete_btn = QPushButton("🗑")
            delete_btn.setFixedSize(30, 25)
            delete_btn.setToolTip("Smazat záznam")
            delete_btn.clicked.connect(lambda checked, e=entry: self.delete_selected_entry(e))
            
            button_layout.addWidget(edit_btn)
            button_layout.addWidget(delete_btn)
            button_widget.setLayout(button_layout)
            
            self.cash_table.setCellWidget(i, 6, button_widget)
        
        self.cash_table.resizeColumnsToContents()
    
    def edit_selected_entry(self, entry):
        dialog = CashEntryEditDialog(entry, self.user_manager)
        if dialog.exec():
            updated_entry = dialog.get_entry()
            
            for i, e in enumerate(self.cash_data):
                if (e["date"] == entry["date"] and 
                    e["user"] == entry["user"]):
                    self.cash_data[i] = updated_entry
                    break
            
            save_cash_diary(self.cash_data)
            self.load_cash_data()
            self.check_today_status()
            
            current_date = self.date_edit.date().toString("dd.MM.yyyy")
            if entry["date"] == current_date and entry["user"] == self.user_manager.current_user:
                self.load_existing_entry()
    
    def delete_selected_entry(self, entry):
        reply = QMessageBox.question(
            self, "Smazat záznam",
            f"Opravdu chcete smazat záznam ze dne {entry['date']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.cash_data = [e for e in self.cash_data if not (
                e["date"] == entry["date"] and 
                e["user"] == entry["user"]
            )]
            
            save_cash_diary(self.cash_data)
            self.load_cash_data()
            self.check_today_status()
            
            current_date = self.date_edit.date().toString("dd.MM.yyyy")
            if entry["date"] == current_date and entry["user"] == self.user_manager.current_user:
                self.load_existing_entry()
    
    def export_cash_data(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Uložit peněžní deník", "", "CSV Files (*.csv)"
        )
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(["Datum", "Uživatel", "Typ směny", "Hotovost ráno", "Hotovost večer", "Rozdíl", "Poznámky"])
                    
                    for entry in self.cash_data:
                        writer.writerow([
                            entry["date"],
                            entry["user"],
                            entry.get("shift_type", "Celodenní"),
                            entry["cash_start"],
                            entry["cash_end"],
                            entry["difference"],
                            entry.get("notes", "")
                        ])
                
                QMessageBox.information(self, "Export", "Peněžní deník byl exportován do CSV (UTF-8)")
            except Exception as e:
                QMessageBox.critical(self, "Chyba", f"Chyba při exportu: {str(e)}")
    
    def edit_cash_entry(self):
        selected = self.cash_table.currentRow()
        if selected >= 0:
            date_item = self.cash_table.item(selected, 0)
            user_item = self.cash_table.item(selected, 1)
            
            if date_item and user_item:
                date = date_item.text()
                user = user_item.text()
                
                for entry in self.cash_data:
                    if entry["date"] == date and entry["user"] == user:
                        self.edit_selected_entry(entry)
                        break
    
    def delete_cash_entry(self):
        selected = self.cash_table.currentRow()
        if selected >= 0:
            date_item = self.cash_table.item(selected, 0)
            user_item = self.cash_table.item(selected, 1)
            
            if date_item and user_item:
                date = date_item.text()
                user = user_item.text()
                
                for entry in self.cash_data:
                    if entry["date"] == date and entry["user"] == user:
                        self.delete_selected_entry(entry)
                        break

class CashEntryEditDialog(QDialog):
    def __init__(self, entry, user_manager):
        super().__init__()
        self.entry = entry
        self.user_manager = user_manager
        self.setWindowTitle("Upravit záznam peněžního deníku")
        self.setFixedWidth(400)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout()
        
        date_label = QLabel(self.entry["date"])
        layout.addRow("Datum:", date_label)
        
        user_label = QLabel(self.entry["user"])
        layout.addRow("Uživatel:", user_label)
        
        morning_layout = QHBoxLayout()
        morning_layout.addWidget(QLabel("Hotovost ráno:"))
        self.cash_start = QLineEdit(str(self.entry["cash_start"]))
        self.cash_start.setFixedWidth(100)
        morning_layout.addWidget(self.cash_start)
        morning_layout.addWidget(QLabel("Kč"))
        morning_layout.addStretch()
        layout.addRow(morning_layout)
        
        evening_layout = QHBoxLayout()
        evening_layout.addWidget(QLabel("Hotovost večer:"))
        self.cash_end = QLineEdit(str(self.entry["cash_end"]))
        self.cash_end.setFixedWidth(100)
        evening_layout.addWidget(self.cash_end)
        evening_layout.addWidget(QLabel("Kč"))
        evening_layout.addStretch()
        layout.addRow(evening_layout)
        
        self.cash_notes = QTextEdit()
        self.cash_notes.setPlainText(self.entry.get("notes", ""))
        self.cash_notes.setMaximumHeight(80)
        layout.addRow("Poznámky:", self.cash_notes)
        
        button_layout = QHBoxLayout()
        save_button = QPushButton("Uložit")
        cancel_button = QPushButton("Zrušit")
        
        save_button.clicked.connect(self.save_entry)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
    def save_entry(self):
        try:
            cash_start = float(self.cash_start.text().replace(",", "."))
            cash_end = float(self.cash_end.text().replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Chyba", "Zadejte platné částky")
            return
        
        self.entry.update({
            "cash_start": cash_start,
            "cash_end": cash_end,
            "difference": cash_end - cash_start,
            "notes": self.cash_notes.toPlainText(),
            "edited_by": self.user_manager.current_user,
            "edited_at": datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        
        self.accept()
    
    def get_entry(self):
        return self.entry

# ================= 4. NASTAVENÍ S NOVINKAMI =================
class SettingsDialog(QDialog):
    def __init__(self, user_manager):
        super().__init__()
        self.user_manager = user_manager
        self.setWindowTitle("Nastavení")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        tabs = QTabWidget()
        
        general_tab = QWidget()
        general_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Systémový (default)", "Světlý", "Tmavý"])
        current_theme = settings.get("theme", "system")
        if current_theme == "system":
            self.theme_combo.setCurrentIndex(0)
        elif current_theme == "light":
            self.theme_combo.setCurrentIndex(1)
        elif current_theme == "dark":
            self.theme_combo.setCurrentIndex(2)
        general_layout.addRow("Režim vzhledu:", self.theme_combo)
        
        self.email_checkbox = QCheckBox("Povolit e-mailové notifikace")
        self.email_checkbox.setChecked(settings.get("email_notifications", True))
        general_layout.addRow("", self.email_checkbox)
        
        self.auto_save_checkbox = QCheckBox("Automatické ukládání")
        self.auto_save_checkbox.setChecked(settings.get("auto_save", True))
        general_layout.addRow("", self.auto_save_checkbox)
        
        self.save_interval = QSpinBox()
        self.save_interval.setRange(1, 60)
        self.save_interval.setValue(settings.get("save_interval", 5))
        self.save_interval.setSuffix(" minut")
        general_layout.addRow("Interval ukládání:", self.save_interval)
        
        general_tab.setLayout(general_layout)
        
        email_tab = QWidget()
        email_layout = QFormLayout()
        
        self.smtp_server = QLineEdit(settings.get("email_smtp_server", ""))
        email_layout.addRow("SMTP Server:", self.smtp_server)
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(settings.get("email_smtp_port", 587))
        email_layout.addRow("Port:", self.smtp_port)
        
        self.smtp_username = QLineEdit(settings.get("email_smtp_username", ""))
        email_layout.addRow("Uživatelské jméno:", self.smtp_username)
        
        self.smtp_password = QLineEdit(settings.get("email_smtp_password", ""))
        self.smtp_password.setEchoMode(QLineEdit.Password)
        email_layout.addRow("Heslo:", self.smtp_password)
        
        self.sender_email = QLineEdit(settings.get("email_sender", ""))
        email_layout.addRow("Odesílatel:", self.sender_email)
        
        self.email_subject = QLineEdit(settings.get("email_subject", ""))
        email_layout.addRow("Předmět e-mailu:", self.email_subject)
        
        self.email_template = QTextEdit()
        self.email_template.setPlainText(settings.get("email_template", ""))
        self.email_template.setMaximumHeight(150)
        email_layout.addRow("Šablona e-mailu:", self.email_template)
        
        test_button = QPushButton("Otestovat připojení")
        test_button.clicked.connect(self.test_email_connection)
        email_layout.addRow("", test_button)
        
        email_tab.setLayout(email_layout)
        
        if self.user_manager.current_user == "admin":
            backup_tab = QWidget()
            backup_layout = QFormLayout()
            
            self.backup_enabled = QCheckBox("Povolit automatické zálohování")
            self.backup_enabled.setChecked(settings.get("backup_enabled", True))
            backup_layout.addRow("", self.backup_enabled)
            
            self.backup_keep_days = QSpinBox()
            self.backup_keep_days.setRange(1, 365)
            self.backup_keep_days.setValue(settings.get("backup_keep_days", 10))
            self.backup_keep_days.setSuffix(" dní")
            backup_layout.addRow("Uchovávat zálohy (dní):", self.backup_keep_days)
            
            self.backup_path_edit = QLineEdit(settings.get("backup_path", ""))
            backup_layout.addRow("Cesta k zálohám:", self.backup_path_edit)
            
            backup_browse_btn = QPushButton("Procházet...")
            backup_browse_btn.clicked.connect(self.browse_backup_path)
            backup_layout.addRow("", backup_browse_btn)
            
            manual_backup_btn = QPushButton("Vytvořit zálohu nyní")
            manual_backup_btn.clicked.connect(self.create_manual_backup)
            backup_layout.addRow("", manual_backup_btn)
            
            backup_tab.setLayout(backup_layout)
            tabs.addTab(backup_tab, "Zálohy")
            
            users_tab = QWidget()
            users_layout = QVBoxLayout()
            
            self.users_list = QListWidget()
            users_layout.addWidget(self.users_list, 1)
            
            users_buttons = QHBoxLayout()
            self.btn_add_user = QPushButton("Přidat uživatele")
            self.btn_edit_user = QPushButton("Upravit")
            self.btn_delete_user = QPushButton("Smazat")
            
            self.btn_add_user.clicked.connect(self.add_user)
            self.btn_edit_user.clicked.connect(self.edit_user)
            self.btn_delete_user.clicked.connect(self.delete_user)
            
            users_buttons.addWidget(self.btn_add_user)
            users_buttons.addWidget(self.btn_edit_user)
            users_buttons.addWidget(self.btn_delete_user)
            
            users_layout.addLayout(users_buttons)
            users_tab.setLayout(users_layout)
            tabs.addTab(users_tab, "Uživatelé")
            
            self.load_users_list()
            
            recipients_tab = QWidget()
            recipients_layout = QVBoxLayout()
            
            self.recipients_table = QTableWidget()
            self.recipients_table.setColumnCount(3)
            self.recipients_table.setHorizontalHeaderLabels(["Jméno", "E-mail", "Aktivní"])
            self.recipients_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            recipients_layout.addWidget(self.recipients_table, 1)
            
            recipients_buttons = QHBoxLayout()
            self.btn_add_recipient = QPushButton("Přidat příjemce")
            self.btn_edit_recipient = QPushButton("Upravit")
            self.btn_delete_recipient = QPushButton("Smazat")
            
            self.btn_add_recipient.clicked.connect(self.add_recipient)
            self.btn_edit_recipient.clicked.connect(self.edit_recipient)
            self.btn_delete_recipient.clicked.connect(self.delete_recipient)
            
            recipients_buttons.addWidget(self.btn_add_recipient)
            recipients_buttons.addWidget(self.btn_edit_recipient)
            recipients_buttons.addWidget(self.btn_delete_recipient)
            
            recipients_layout.addLayout(recipients_buttons)
            recipients_tab.setLayout(recipients_layout)
            tabs.addTab(recipients_tab, "Příjemci e-mailů")
            
            self.load_recipients_table()
        
        # Záložka O programu
        about_tab = QWidget()
        about_layout = QVBoxLayout()
        
        about_text = QLabel(
            "HEM - Komunikační modul\n\n"
            "Verze: 0.4.2\n"
            "Vývojář: JAMAsoft\n"
            "Web: www.jamasoft.cz\n\n"
            "Komunikační systém pro recepci\n"
            "Wellness Hotel Beethoven\n\n"
            "© 2025 HEM - Hotel Easy Manager"
        )
        about_text.setWordWrap(True)
        about_text.setAlignment(Qt.AlignCenter)
        about_layout.addWidget(about_text)
        
        novinky_btn = QPushButton("Novinky verze 0.4.2")
        novinky_btn.clicked.connect(self.show_version_news)
        about_layout.addWidget(novinky_btn)
        
        about_tab.setLayout(about_layout)
        
        tabs.addTab(general_tab, "Obecné")
        tabs.addTab(email_tab, "E-mail")
        if self.user_manager.current_user == "admin":
            tabs.addTab(backup_tab, "Zálohy")
            tabs.addTab(users_tab, "Uživatelé")
            tabs.addTab(recipients_tab, "Příjemci")
        tabs.addTab(about_tab, "O programu")
        
        button_layout = QHBoxLayout()
        save_button = QPushButton("Uložit")
        cancel_button = QPushButton("Zrušit")
        
        save_button.clicked.connect(self.save_settings)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(tabs, 1)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def show_version_news(self):
        news = (
            "Novinky ve verzi 0.4.2:\n\n"
            "• Přidán detail úkolu po dvojkliku v kalendáři:\n"
            "  - Zobrazí prioritu, přiřazení, opakování a poznámku.\n"
            "  - Tlačítka pro splnění/zrušení, smazání úkolu.\n"
            "• Zjednodušený seznam úkolů (odstraněny sloupce priorita, přiřazení, poznámka).\n"
        )
        QMessageBox.information(self, "Novinky verze 0.4.2", news)
    
    def load_users_list(self):
        self.users_list.clear()
        for username, data in self.user_manager.users.items():
            cannot_delete = data.get("cannot_delete", False)
            role = data['role']
            name = data.get('name', username)
            
            item_text = f"{username} ({name}) - {role}"
            if cannot_delete:
                item_text += " [chráněný]"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, username)
            
            if cannot_delete:
                item.setForeground(QColor("blue"))
            
            self.users_list.addItem(item)
    
    def load_recipients_table(self):
        recipients = load_email_recipients()
        self.recipients_table.setRowCount(len(recipients))
        
        for i, recipient in enumerate(recipients):
            self.recipients_table.setItem(i, 0, QTableWidgetItem(recipient["name"]))
            self.recipients_table.setItem(i, 1, QTableWidgetItem(recipient["email"]))
            
            active_checkbox = QCheckBox()
            active_checkbox.setChecked(recipient.get("active", True))
            self.recipients_table.setCellWidget(i, 2, active_checkbox)
        
        self.recipients_table.resizeColumnsToContents()
    
    def browse_backup_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Vyberte složku pro zálohy")
        if directory:
            self.backup_path_edit.setText(directory)
    
    def create_manual_backup(self):
        backup_file = create_backup()
        if backup_file:
            QMessageBox.information(self, "Záloha", f"Záloha byla vytvořena:\n{backup_file}")
        else:
            QMessageBox.warning(self, "Záloha", "Záloha se nepodařila vytvořit.")
    
    def add_user(self):
        dialog = UserEditDialog(self.user_manager, None)
        if dialog.exec():
            self.load_users_list()
    
    def edit_user(self):
        selected = self.users_list.currentItem()
        if selected:
            username = selected.data(Qt.UserRole)
            if self.user_manager.users[username].get("cannot_delete", False):
                QMessageBox.warning(self, "Chyba", "Tento účet nelze upravovat")
                return
            
            dialog = UserEditDialog(self.user_manager, username)
            if dialog.exec():
                self.load_users_list()
    
    def delete_user(self):
        selected = self.users_list.currentItem()
        if selected:
            username = selected.data(Qt.UserRole)
            
            if self.user_manager.users[username].get("cannot_delete", False):
                QMessageBox.warning(self, "Chyba", "Tento účet nelze smazat")
                return
            
            if username == self.user_manager.current_user:
                QMessageBox.warning(self, "Chyba", "Nemůžete smazat svůj vlastní účet")
                return
            
            reply = QMessageBox.question(self, "Smazat uživatele", 
                                       f"Opravdu chcete smazat uživatele {username}?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                if self.user_manager.delete_user(username):
                    self.load_users_list()
                else:
                    QMessageBox.warning(self, "Chyba", "Nelze smazat uživatele")
    
    def add_recipient(self):
        dialog = RecipientEditDialog(None)
        if dialog.exec():
            new_recipient = dialog.get_recipient()
            recipients = load_email_recipients()
            recipients.append(new_recipient)
            save_email_recipients(recipients)
            self.load_recipients_table()
    
    def edit_recipient(self):
        selected = self.recipients_table.currentRow()
        if selected >= 0:
            recipients = load_email_recipients()
            if selected < len(recipients):
                dialog = RecipientEditDialog(recipients[selected])
                if dialog.exec():
                    recipients[selected] = dialog.get_recipient()
                    save_email_recipients(recipients)
                    self.load_recipients_table()
    
    def delete_recipient(self):
        selected = self.recipients_table.currentRow()
        if selected >= 0:
            recipients = load_email_recipients()
            if selected < len(recipients):
                reply = QMessageBox.question(
                    self, "Smazat příjemce",
                    f"Opravdu chcete smazat příjemce {recipients[selected]['name']}?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    del recipients[selected]
                    save_email_recipients(recipients)
                    self.load_recipients_table()
    
    def test_email_connection(self):
        try:
            server = smtplib.SMTP(self.smtp_server.text(), self.smtp_port.value())
            server.starttls()
            server.login(self.smtp_username.text(), self.smtp_password.text())
            server.quit()
            QMessageBox.information(self, "Test připojení", "Připojení k SMTP serveru bylo úspěšné!")
        except Exception as e:
            QMessageBox.critical(self, "Chyba připojení", f"Nelze se připojit k SMTP serveru:\n{str(e)}")
    
    def save_settings(self):
        theme_index = self.theme_combo.currentIndex()
        if theme_index == 0:
            settings["theme"] = "system"
        elif theme_index == 1:
            settings["theme"] = "light"
        elif theme_index == 2:
            settings["theme"] = "dark"
        
        settings["email_notifications"] = self.email_checkbox.isChecked()
        settings["auto_save"] = self.auto_save_checkbox.isChecked()
        settings["save_interval"] = self.save_interval.value()
        
        settings["email_smtp_server"] = self.smtp_server.text()
        settings["email_smtp_port"] = self.smtp_port.value()
        settings["email_smtp_username"] = self.smtp_username.text()
        settings["email_smtp_password"] = self.smtp_password.text()
        settings["email_sender"] = self.sender_email.text()
        settings["email_subject"] = self.email_subject.text()
        settings["email_template"] = self.email_template.toPlainText()
        
        if self.user_manager.current_user == "admin":
            settings["backup_enabled"] = self.backup_enabled.isChecked()
            settings["backup_keep_days"] = self.backup_keep_days.value()
            settings["backup_path"] = self.backup_path_edit.text()
        
        save_settings(settings)
        self.accept()

class UserEditDialog(QDialog):
    def __init__(self, user_manager, username=None):
        super().__init__()
        self.user_manager = user_manager
        self.username = username
        self.is_edit = username is not None
        
        self.setWindowTitle("Přidat uživatele" if not self.is_edit else "Upravit uživatele")
        self.setFixedWidth(400)
        
        self.init_ui()
        if self.is_edit:
            self.load_user_data()
    
    def init_ui(self):
        layout = QFormLayout()
        
        self.username_edit = QLineEdit()
        if self.is_edit:
            self.username_edit.setText(self.username)
            self.username_edit.setReadOnly(True)
        layout.addRow("Uživatelské jméno:", self.username_edit)
        
        self.name_edit = QLineEdit()
        layout.addRow("Jméno a příjmení:", self.name_edit)
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        if not self.is_edit:
            layout.addRow("Heslo:", self.password_edit)
        else:
            layout.addRow("Nové heslo (ponechte prázdné):", self.password_edit)
        
        self.role_combo = QComboBox()
        self.role_combo.addItems(["recepční", "admin"])
        layout.addRow("Role:", self.role_combo)
        
        self.comment_color_edit = QLineEdit()
        self.comment_color_edit.setPlaceholderText("#RRGGBB")
        color_button = QPushButton("Vybrat barvu")
        color_button.clicked.connect(self.choose_color)
        
        color_layout = QHBoxLayout()
        color_layout.addWidget(self.comment_color_edit)
        color_layout.addWidget(color_button)
        
        layout.addRow("Barva komentáře:", color_layout)
        
        button_layout = QHBoxLayout()
        save_button = QPushButton("Uložit")
        cancel_button = QPushButton("Zrušit")
        
        save_button.clicked.connect(self.save_user)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
    def load_user_data(self):
        if self.username in self.user_manager.users:
            user_data = self.user_manager.users[self.username]
            self.name_edit.setText(user_data.get("name", ""))
            self.role_combo.setCurrentText(user_data["role"])
            self.comment_color_edit.setText(user_data.get("comment_color", "#000000"))
    
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.comment_color_edit.setText(color.name())
    
    def save_user(self):
        username = self.username_edit.text()
        if not username:
            QMessageBox.warning(self, "Chyba", "Zadejte uživatelské jméno")
            return
        
        name = self.name_edit.text()
        if not name:
            QMessageBox.warning(self, "Chyba", "Zadejte jméno a příjmení")
            return
        
        password = self.password_edit.text() if not self.is_edit else None
        if not self.is_edit and not password:
            QMessageBox.warning(self, "Chyba", "Zadejte heslo")
            return
        
        role = self.role_combo.currentText()
        
        color = self.comment_color_edit.text().strip()
        if not color:
            color = "#000000"
        elif not QColor(color).isValid():
            QMessageBox.warning(self, "Chyba", "Zadejte platnou barvu ve formátu #RRGGBB")
            return
        
        if self.is_edit:
            if password:
                self.user_manager.users[username]["password"] = hashlib.sha256(password.encode()).hexdigest()
            self.user_manager.users[username]["name"] = name
            self.user_manager.users[username]["role"] = role
            self.user_manager.users[username]["comment_color"] = color
        else:
            if not self.user_manager.add_user(username, password, role, name):
                QMessageBox.warning(self, "Chyba", "Uživatel již existuje")
                return
            self.user_manager.users[username]["comment_color"] = color
        
        self.user_manager.save_users()
        self.accept()

class RecipientEditDialog(QDialog):
    def __init__(self, recipient=None):
        super().__init__()
        self.recipient = recipient or {}
        self.is_edit = bool(recipient)
        
        self.setWindowTitle("Přidat příjemce" if not self.is_edit else "Upravit příjemce")
        self.setFixedWidth(400)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout()
        
        self.name_edit = QLineEdit(self.recipient.get("name", ""))
        layout.addRow("Jméno:", self.name_edit)
        
        self.email_edit = QLineEdit(self.recipient.get("email", ""))
        layout.addRow("E-mail:", self.email_edit)
        
        self.active_checkbox = QCheckBox("Aktivní")
        self.active_checkbox.setChecked(self.recipient.get("active", True))
        layout.addRow("", self.active_checkbox)
        
        button_layout = QHBoxLayout()
        save_button = QPushButton("Uložit")
        cancel_button = QPushButton("Zrušit")
        
        save_button.clicked.connect(self.save_recipient)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
    def save_recipient(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Chyba", "Zadejte jméno příjemce")
            return
        
        email = self.email_edit.text().strip()
        if not email or "@" not in email:
            QMessageBox.warning(self, "Chyba", "Zadejte platný e-mail")
            return
        
        self.recipient = {
            "name": name,
            "email": email,
            "active": self.active_checkbox.isChecked()
        }
        
        self.accept()
    
    def get_recipient(self):
        return self.recipient

# ================= 5. DASHBOARD =================
class DashboardWidget(QWidget):
    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.init_ui()
        self.load_data()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_data)
        self.timer.start(60000)
    
    def init_ui(self):
        main_layout = QHBoxLayout()
        
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        calendar_title = QLabel("Kalendář")
        calendar_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        left_layout.addWidget(calendar_title)
        
        self.mini_calendar = QCalendarWidget()
        self.mini_calendar.setGridVisible(True)
        self.mini_calendar.setMaximumHeight(200)
        self.mini_calendar.clicked.connect(self.on_calendar_click)
        left_layout.addWidget(self.mini_calendar)
        
        today_tasks_title = QLabel("Dnešní úkoly:")
        today_tasks_title.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px;")
        left_layout.addWidget(today_tasks_title)
        
        self.today_tasks_list = QListWidget()
        self.today_tasks_list.setMaximumHeight(150)
        left_layout.addWidget(self.today_tasks_list)
        
        left_widget.setLayout(left_layout)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        welcome_label = QLabel(f"Vítejte, {self.user_manager.users[self.user_manager.current_user]['name']}!")
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1890ff;")
        right_layout.addWidget(welcome_label)
        
        right_layout.addSpacing(15)
        
        cash_status_group = QGroupBox("Stav peněžního deníku")
        cash_status_layout = QVBoxLayout()
        
        self.cash_status_label = QLabel("Načítám stav...")
        self.cash_status_label.setWordWrap(True)
        cash_status_layout.addWidget(self.cash_status_label)
        
        self.cash_details_label = QLabel("")
        self.cash_details_label.setWordWrap(True)
        cash_status_layout.addWidget(self.cash_details_label)
        
        cash_status_group.setLayout(cash_status_layout)
        right_layout.addWidget(cash_status_group)
        
        right_layout.addSpacing(15)
        
        yesterday_cash_group = QGroupBox("Včerejší hotovost")
        yesterday_layout = QVBoxLayout()
        
        self.yesterday_cash_label = QLabel("Načítám včerejší data...")
        self.yesterday_cash_label.setWordWrap(True)
        yesterday_layout.addWidget(self.yesterday_cash_label)
        
        yesterday_cash_group.setLayout(yesterday_layout)
        right_layout.addWidget(yesterday_cash_group)
        
        right_layout.addSpacing(15)
        
        stats_group = QGroupBox("Rychlé statistiky")
        stats_layout = QGridLayout()
        
        self.stats_messages = QLabel("Načítám...")
        self.stats_tasks = QLabel("Načítám...")
        self.stats_date = QLabel(datetime.now().strftime("%d.%m.%Y"))
        
        stats_layout.addWidget(QLabel("Dnešní vzkazy:"), 0, 0)
        stats_layout.addWidget(self.stats_messages, 0, 1)
        stats_layout.addWidget(QLabel("Dnešní úkoly:"), 1, 0)
        stats_layout.addWidget(self.stats_tasks, 1, 1)
        stats_layout.addWidget(QLabel("Dnešní datum:"), 2, 0)
        stats_layout.addWidget(self.stats_date, 2, 1)
        
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        
        right_widget.setLayout(right_layout)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def load_data(self):
        messages = load_messages()
        tasks = load_tasks()
        cash_data = load_cash_diary()
        completions = load_task_completions()
        
        today = datetime.now().strftime("%d.%m.%Y")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
        today_qdate = QDate.currentDate()
        
        today_tasks_occ = get_tasks_for_date(today_qdate, tasks, completions)
        incomplete_today = [t for t in today_tasks_occ if not t["completed"]]
        
        today_messages = [m for m in messages if m["date"] == today]
        
        self.stats_messages.setText(f"{len(today_messages)}")
        self.stats_tasks.setText(f"{len(incomplete_today)}")
        self.stats_date.setText(today)
        
        self.today_tasks_list.clear()
        for task_occ in incomplete_today:
            assigned_to = task_occ["assigned_to"]
            if assigned_to == "all":
                assigned_text = "Všichni"
            else:
                assigned_text = self.user_manager.users.get(assigned_to, {}).get("name", assigned_to)
            
            item_text = f"✗ {task_occ['title']} ({assigned_text})"
            if task_occ.get("recurrence"):
                item_text += " [opak.]"
            
            item = QListWidgetItem(item_text)
            item.setForeground(QColor("red"))
            self.today_tasks_list.addItem(item)
        
        if self.today_tasks_list.count() == 0:
            self.today_tasks_list.addItem("Žádné nesplněné úkoly na dnešek")
            item = self.today_tasks_list.item(0)
            item.setForeground(QColor("gray"))
        
        status = check_cash_status()
        
        status_text = f"<b>{status['stav']}</b><br>{status['popis']}"
        self.cash_status_label.setText(status_text)
        
        if status['barva'] == 'green':
            self.cash_status_label.setStyleSheet("color: green; padding: 5px;")
        elif status['barva'] == 'orange':
            self.cash_status_label.setStyleSheet("color: orange; padding: 5px;")
        elif status['barva'] == 'red':
            self.cash_status_label.setStyleSheet("color: red; padding: 5px;")
        
        today_cash = [c for c in cash_data if c["date"] == today and c["user"] == self.user_manager.current_user]
        if today_cash:
            entry = today_cash[0]
            details = f"Dnešní hotovost: Ráno: {entry['cash_start']:,.0f} Kč, Večer: {entry['cash_end']:,.0f} Kč<br>"
            details += f"Rozdíl: {entry['difference']:+,.0f} Kč<br>"
            details += f"Typ směny: {entry.get('shift_type', 'Celodenní')}"
            
            self.cash_details_label.setText(details)
        else:
            self.cash_details_label.setText("Dnes zatím žádný záznam v peněžním deníku")
        
        yesterday_cash = [c for c in cash_data if c["date"] == yesterday]
        if yesterday_cash:
            total_evening_yesterday = sum(c["cash_end"] for c in yesterday_cash)
            self.yesterday_cash_label.setText(f"Včerejší konečná hotovost: {total_evening_yesterday:,.0f} Kč")
            
            yesterday_shifts = [c for c in cash_data if c["date"] == yesterday]
            all_have_evening = all(c["cash_end"] != 0 for c in yesterday_shifts)
            
            if not all_have_evening:
                self.yesterday_cash_label.setText(
                    f"Včerejší konečná hotovost: {total_evening_yesterday:,.0f} Kč<br>"
                    f"<span style='color: red;'>UPOZORNĚNÍ: Ne všechny včerejší směny byly uzavřeny!</span>"
                )
        else:
            self.yesterday_cash_label.setText("Včera nebyly žádné záznamy v peněžním deníku")
    
    def on_calendar_click(self, date):
        selected_date = date.toString("dd.MM.yyyy")
        tasks = load_tasks()
        completions = load_task_completions()
        day_tasks = get_tasks_for_date(date, tasks, completions)
        
        if day_tasks:
            task_list = "\n".join([f"• {t['title']}" + (" (opak.)" if t.get("recurrence") else "") for t in day_tasks])
            QMessageBox.information(self, f"Úkoly na {selected_date}", f"Úkoly na {selected_date}:\n\n{task_list}")
        else:
            QMessageBox.information(self, f"Úkoly na {selected_date}", f"Na {selected_date} nejsou žádné úkoly.")

# ================= HLAVNÍ OKNO =================
class MainWindow(QMainWindow):
    def __init__(self, single_instance_manager=None):
        super().__init__()
        self.setWindowTitle("HEM - Komunikační modul")
        self.resize(1000, 600)
        
        self.user_manager = UserManager()
        
        if not self.login():
            sys.exit()
        
        if self.user_manager.current_user == "admin" and settings.get("backup_enabled", True):
            create_backup()
        
        self.init_ui()
        
        self.tray_icon = None
        self.setup_system_tray()
        
        self.single_instance_manager = single_instance_manager
        if single_instance_manager:
            single_instance_manager.set_window_callback(self.bring_to_front)
    
    def login(self):
        dlg = LoginDialog(self.user_manager)
        return dlg.exec() == QDialog.Accepted
    
    def init_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tab_widget)
        
        self.dashboard = DashboardWidget(self.user_manager)
        self.tab_widget.addTab(self.dashboard, "🏠 Dashboard")
        
        self.calendar_dialog = CalendarDialog(self.user_manager)
        self.tab_widget.addTab(self.calendar_dialog, "📅 Kalendář s úkoly")
        
        self.messages_dialog = MessagesDialog(self.user_manager, self)
        self.tab_widget.addTab(self.messages_dialog, "💬 Vzkazy")
        
        self.cash_dialog = CashDiaryDialog(self.user_manager)
        self.tab_widget.addTab(self.cash_dialog, "💰 Peněžní deník")
        
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        refresh_action = QAction("🔄 Aktualizovat", self)
        refresh_action.triggered.connect(self.refresh_all)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        settings_action = QAction("⚙ Nastavení", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
        
        logout_action = QAction("🚪 Odhlásit", self)
        logout_action.triggered.connect(self.logout)
        toolbar.addAction(logout_action)
        
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        user_info = f"Přihlášen jako: {self.user_manager.current_user} ({self.user_manager.users[self.user_manager.current_user]['name']})"
        status_bar.showMessage(user_info)
    
    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon())
        self.tray_icon.setToolTip("HEM Komunikace")
        
        tray_menu = QMenu()
        show_action = QAction("Zobrazit okno", self)
        show_action.triggered.connect(self.show_normal)
        quit_action = QAction("Ukončit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
    
    def show_normal(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
    
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            self.show_normal()
    
    def closeEvent(self, event):
        status = check_cash_status()
        now_hour = datetime.now().hour
        
        warning_message = ""
        if not status["zapsáno_ráno"] and now_hour >= 8:
            warning_message += "• Ranní hotovost nebyla zapsána!\n"
        if not status["zapsáno_večer"] and now_hour >= 20:
            warning_message += "• Večerní hotovost nebyla zapsána (po 20:00)!\n"
        
        if warning_message:
            reply = QMessageBox.warning(
                self, 
                "Peněžní deník není zapsán",
                f"Před minimalizací aplikace prosím zkontrolujte peněžní deník:\n\n{warning_message}\nOpravdu chcete minimalizovat aplikaci do lišty?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        messages_tab = self.messages_dialog
        if messages_tab:
            current_text = messages_tab.today_edit.toPlainText().strip()
            last_saved_text = messages_tab.last_saved_text
            if current_text != last_saved_text:
                reply = QMessageBox.question(
                    self, 
                    "Neuložené vzkazy",
                    "Máte neuložené vzkazy. Chcete je uložit před minimalizací?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                if reply == QMessageBox.Yes:
                    messages_tab.save_today_message()
                elif reply == QMessageBox.Cancel:
                    event.ignore()
                    return
        
        self.hide()
        self.tray_icon.showMessage(
            "HEM Komunikace",
            "Aplikace běží na pozadí. Kliknutím pravým tlačítkem na ikonu ji můžete ukončit.",
            QSystemTrayIcon.Information,
            3000
        )
        event.ignore()
    
    def quit_app(self):
        if self.user_manager.current_user == "admin" and settings.get("backup_enabled", True):
            create_backup()
        QApplication.quit()
    
    def bring_to_front(self):
        self.show_normal()
    
    def on_tab_changed(self, index):
        if hasattr(self, 'messages_dialog') and index == self.tab_widget.indexOf(self.messages_dialog):
            self.messages_dialog.refresh_messages()
        
        if hasattr(self, 'dashboard') and index == self.tab_widget.indexOf(self.dashboard):
            self.dashboard.load_data()
        
        if hasattr(self, 'cash_dialog') and index == self.tab_widget.indexOf(self.cash_dialog):
            self.cash_dialog.load_cash_data()
            self.cash_dialog.check_today_status()
            self.cash_dialog.load_existing_entry()
    
    def refresh_all(self):
        if hasattr(self, 'dashboard'):
            self.dashboard.load_data()
        
        if hasattr(self, 'calendar_dialog'):
            self.calendar_dialog.load_calendar()
            self.calendar_dialog.load_tasks_for_date(self.calendar_dialog.selected_date)
        
        if hasattr(self, 'messages_dialog'):
            self.messages_dialog.refresh_messages()
        
        if hasattr(self, 'cash_dialog'):
            self.cash_dialog.load_cash_data()
            self.cash_dialog.check_today_status()
            self.cash_dialog.load_existing_entry()
    
    def show_settings(self):
        dlg = SettingsDialog(self.user_manager)
        if dlg.exec():
            QMessageBox.information(self, "Nastavení", "Některé změny se projeví po restartování aplikace.")
    
    def logout(self):
        reply = QMessageBox.question(
            self, 
            "Odhlásit", 
            "Opravdu chcete odhlásit?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            subprocess.Popen([sys.executable] + sys.argv)
            QApplication.quit()

# ================= START =================
if __name__ == "__main__":
    app = QApplication([])
    
    single_instance = SingleInstanceManager()
    if not single_instance.try_to_become_server():
        if single_instance.send_show_message():
            sys.exit(0)
        else:
            sys.exit(1)
    
    check_integrity()
    create_desktop_shortcut()
    ensure_startup_entry()
    
    theme = settings.get("theme", "system")
    setup_theme(app, theme)
    
    win = MainWindow(single_instance_manager=single_instance)
    win.show()
    
    sys.exit(app.exec())