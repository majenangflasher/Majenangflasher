import subprocess
import os
import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame, QProgressBar, QDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal as Signal, QObject, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QPalette
import warnings

from frp_license import check_license, get_hwid, logger as lic_logger
from frp_ui import ActivationDialog, btn_style, card_style, TAG_COLORS, LockWidget

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── ADB PATH SETUP ────────────────────────────────────────────────────────────
def find_adb():
    """Find ADB executable"""
    if getattr(sys, 'frozen', False):
        SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
        BUNDLE_DIR = getattr(sys, '_MEIPASS', SCRIPT_DIR)
    else:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        BUNDLE_DIR = SCRIPT_DIR
    
    candidates = [
        os.path.join(BUNDLE_DIR, "adb.exe"), os.path.join(BUNDLE_DIR, "adb"),
        os.path.join(SCRIPT_DIR, "adb.exe"), os.path.join(SCRIPT_DIR, "adb"),
    ]
    
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "adb"

ADB_PATH = find_adb()

# ── SIGNALS ───────────────────────────────────────────────────────────────────
class WorkerSignals(QObject):
    log_signal      = Signal(str, str)   # msg, tag
    result_signal   = Signal(bool, str)
    bar_signal      = Signal(int)

signals = WorkerSignals()

# ── WORKER THREAD ─────────────────────────────────────────────────────────────
class ADBWorker(QThread):
    """Background thread for ADB operations"""
    def __init__(self):
        super().__init__()
        self.command = None
        
    def run(self):
        if not self.command:
            return
        try:
            signals.log_signal.emit("~ Executing command...", "info")
            result = subprocess.run(
                self.command,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                signals.log_signal.emit(result.stdout, "success")
                signals.result_signal.emit(True, "Success")
            else:
                signals.log_signal.emit(result.stderr or "Command failed", "error")
                signals.result_signal.emit(False, "Failed")
        except subprocess.TimeoutExpired:
            signals.log_signal.emit("✘ Command timeout (>30s)", "error")
            signals.result_signal.emit(False, "Timeout")
            logger.error("ADB command timeout")
        except FileNotFoundError:
            signals.log_signal.emit(f"✘ ADB not found: {ADB_PATH}", "error")
            signals.result_signal.emit(False, "Not found")
            logger.error(f"ADB not found: {ADB_PATH}")
        except Exception as e:
            signals.log_signal.emit(f"✘ Error: {str(e)}", "error")
            signals.result_signal.emit(False, "Error")
            logger.error(f"ADB command error: {e}")

# ── MAIN WINDOW ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAJENANG FLASHER — FRP RESET TOOL v2.0")
        self.setFixedSize(600, 700)
        self.setStyleSheet("background-color:#080810; color:#e2e8f0;")
        self.is_running = False
        self.adb_worker = None
        self._build_ui()
        self._wire_signals()
        logger.info("MainWindow initialized")
        
    def _build_ui(self):
        """Build main UI"""
        try:
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)

            # Header
            header = QFrame()
            header.setStyleSheet(card_style())
            h_lay = QVBoxLayout(header)
            h_lay.setContentsMargins(20, 15, 20, 15)
            
            title = QLabel("🔑 MAJENANG FLASHER - FRP RESET")
            title.setFont(QFont("Segoe UI", 16, QFont.Bold))
            title.setStyleSheet("color:#c084fc;")
            h_lay.addWidget(title)
            
            subtitle = QLabel("v2.0 Production | ADB FRP Reset Tool")
            subtitle.setFont(QFont("Segoe UI", 9))
            subtitle.setStyleSheet("color:#6b7280;")
            h_lay.addWidget(subtitle)
            layout.addWidget(header)

            # Control Panel
            control = QFrame()
            control.setStyleSheet(card_style())
            c_lay = QVBoxLayout(control)
            c_lay.setContentsMargins(15, 15, 15, 15)
            
            c_label = QLabel("KONTROL")
            c_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            c_label.setStyleSheet("color:#fbbf24;")
            c_lay.addWidget(c_label)
            
            btn_lay = QHBoxLayout()
            
            self.check_btn = QPushButton("📱 Cek Device")
            self.check_btn.setStyleSheet(btn_style("#1e5f5f", "#2a8a8a"))
            self.check_btn.clicked.connect(self._check_device)
            btn_lay.addWidget(self.check_btn)
            
            self.reset_btn = QPushButton("🗑 Reset FRP")
            self.reset_btn.setStyleSheet(btn_style("#6d28d9", "#7c3aed"))
            self.reset_btn.clicked.connect(self._start_reset)
            btn_lay.addWidget(self.reset_btn)
            
            self.clear_btn = QPushButton("🧹 Clear")
            self.clear_btn.setStyleSheet(btn_style("#5f3d00", "#8a5a00"))
            self.clear_btn.clicked.connect(self._clear_logs)
            btn_lay.addWidget(self.clear_btn)
            
            c_lay.addLayout(btn_lay)
            layout.addWidget(control)

            # Progress Bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #111128;
                    border: 1px solid #2a2a4a;
                    border-radius: 4px;
                    height: 20px;
                }
                QProgressBar::chunk {
                    background-color: #22c55e;
                }
            """)
            self.progress_bar.setValue(0)
            layout.addWidget(self.progress_bar)

            # Log Display
            log_label = QLabel("LOG OUTPUT")
            log_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
            log_label.setStyleSheet("color:#4b5563;")
            layout.addWidget(log_label)
            
            self.log_display = QTextEdit()
            self.log_display.setStyleSheet("""
                QTextEdit {
                    background-color: #0d0d1f;
                    color: #4ade80;
                    border: 1px solid #2a1f4a;
                    border-radius: 8px;
                    font-family: Consolas;
                    font-size: 9pt;
                    padding: 10px;
                }
            """)
            self.log_display.setReadOnly(True)
            self.log_display.setMinimumHeight(300)
            layout.addWidget(self.log_display)

            # Status
            self.status_bar = QLabel("✓ Ready")
            self.status_bar.setStyleSheet("color:#22c55e;")
            layout.addWidget(self.status_bar)

            logger.info("UI built successfully")
        except Exception as e:
            logger.error(f"Error building UI: {e}", exc_info=True)

    def _wire_signals(self):
        """Connect signals to slots"""
        try:
            signals.log_signal.connect(self._on_log)
            signals.result_signal.connect(self._on_result)
            signals.bar_signal.connect(self._on_progress)
            logger.info("Signals wired successfully")
        except Exception as e:
            logger.error(f"Error wiring signals: {e}", exc_info=True)

    def _check_device(self):
        """Check connected ADB devices"""
        try:
            self.log_display.append("~ Checking devices...")
            self.adb_worker = ADBWorker()
            self.adb_worker.command = [ADB_PATH, "devices"]
            self.adb_worker.start()
        except Exception as e:
            self._on_log(f"✘ Error: {e}", "error")
            logger.error(f"Check device error: {e}")

    def _start_reset(self):
        """Start FRP reset"""
        if self.is_running:
            self._on_log("⚠ Already running", "warning")
            return
        try:
            self.is_running = True
            self.reset_btn.setEnabled(False)
            self.log_display.append("~ Starting FRP reset...")
            self.adb_worker = ADBWorker()
            self.adb_worker.command = [ADB_PATH, "shell", "am start -n com.android.settings/com.android.settings.Settings"]
            self.adb_worker.start()
        except Exception as e:
            self._on_log(f"✘ Error: {e}", "error")
            logger.error(f"Reset error: {e}")
            self.is_running = False
            self.reset_btn.setEnabled(True)

    def _clear_logs(self):
        """Clear log display"""
        self.log_display.clear()
        self.progress_bar.setValue(0)

    @pyqtSlot(str, str)
    def _on_log(self, msg, tag):
        """Handle log signal"""
        try:
            color = TAG_COLORS.get(tag, "#e2e8f0")
            self.log_display.setTextColor(QColor(color))
            self.log_display.append(msg)
        except Exception as e:
            logger.error(f"Error handling log: {e}")

    @pyqtSlot(bool, str)
    def _on_result(self, success, msg):
        """Handle result signal"""
        try:
            self.is_running = False
            self.reset_btn.setEnabled(True)
            status = "✔ Success" if success else "✘ Failed"
            self.status_bar.setText(status)
            self.status_bar.setStyleSheet(f"color:{'#22c55e' if success else '#f87171'};")
        except Exception as e:
            logger.error(f"Error handling result: {e}")

    @pyqtSlot(int)
    def _on_progress(self, value):
        """Handle progress signal"""
        try:
            self.progress_bar.setValue(min(value, 100))
        except Exception as e:
            logger.error(f"Error handling progress: {e}")

def main():
    """Main entry point"""
    warnings.filterwarnings("ignore")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor("#080810"))
    pal.setColor(QPalette.WindowText, QColor("#e2e8f0"))
    pal.setColor(QPalette.Base, QColor("#0b0b18"))
    pal.setColor(QPalette.AlternateBase, QColor("#0d0d1f"))
    pal.setColor(QPalette.Text, QColor("#e2e8f0"))
    pal.setColor(QPalette.Button, QColor("#111128"))
    pal.setColor(QPalette.ButtonText, QColor("#e2e8f0"))
    pal.setColor(QPalette.Highlight, QColor("#7c3aed"))
    app.setPalette(pal)

    logger.info("Checking license...")
    valid, hwid = check_license()
    if not valid:
        dlg = ActivationDialog(hwid, btn_style, card_style)
        if dlg.exec_() != QDialog.Accepted or not dlg.activated:
            logger.warning("License activation failed")
            sys.exit(0)

    logger.info("License valid - opening main window")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
