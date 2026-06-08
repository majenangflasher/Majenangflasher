from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, 
    QFrame, QProgressBar, QLineEdit, QDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal as Signal, QObject, QPropertyAnimation, QEasingCurve, QRectF, pyqtSlot
from PyQt5.QtCore import pyqtProperty as Property
from PyQt5.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QPainter, QPen, QBrush, QPainterPath

# ── STYLE CONSTANTS ───────────────────────────────────────────────────────────
TAG_COLORS = {
    "success": "#22c55e",
    "error":   "#f87171",
    "warning": "#fbbf24",
    "info":    "#60a5fa",
    "purple":  "#c084fc",
    "dim":     "#4b5563",
    "white":   "#e2e8f0",
    "cyan":    "#22d3ee",
}

def btn_style(bg="#111128", hover="#1e1535", border="#2a2a4a", text_color="#e2e8f0",
              font_size=9, bold=False, height=30, radius=8):
    """Generate button stylesheet"""
    weight = "600" if bold else "400"
    return f"""
        QPushButton {{
            background-color: {bg};
            color: {text_color};
            border: 1px solid {border};
            border-radius: {radius}px;
            padding: 4px 10px;
            font-size: {font_size}pt;
            font-weight: {weight};
            min-height: {height}px;
        }}
        QPushButton:hover {{
            background-color: {hover};
            border-color: {hover};
        }}
        QPushButton:disabled {{
            background-color: #1a1a2e;
            color: #4b5563;
            border-color: #1e1e3a;
        }}
    """

def card_style(bg="#0d0d1f", border="#2a1f4a", radius=10):
    """Generate card stylesheet"""
    return f"background-color:{bg}; border:1px solid {border}; border-radius:{radius}px;"

# ── ANIMATED LOCK WIDGET ──────────────────────────────────────────────────────
class LockWidget(QWidget):
    """Animated lock icon for license dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 64)
        self._shackle_offset = 0.0
        self._pulse_colors = [
            "#7c3aed","#9333ea","#a855f7","#c084fc",
            "#fbbf24","#fde68a","#fbbf24","#c084fc",
            "#a855f7","#9333ea",
        ]
        self._pulse_idx = 0
        self._color = QColor("#7c3aed")

        self._anim = QPropertyAnimation(self, b"shackle_offset")
        self._anim.setDuration(1100)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.finished.connect(self._anim_reverse)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_step)
        self._pulse_timer.start(90)

        QTimer.singleShot(500, self._anim.start)

    def _anim_reverse(self):
        if self._anim.direction() == QPropertyAnimation.Forward:
            self._anim.setDirection(QPropertyAnimation.Backward)
            QTimer.singleShot(700, self._anim.start)
        else:
            self._anim.setDirection(QPropertyAnimation.Forward)
            QTimer.singleShot(900, self._anim.start)

    def _pulse_step(self):
        self._color = QColor(self._pulse_colors[self._pulse_idx % len(self._pulse_colors)])
        self._pulse_idx += 1
        self.update()

    def get_shackle_offset(self):
        return self._shackle_offset

    def set_shackle_offset(self, val):
        self._shackle_offset = val
        self.update()

    shackle_offset = Property(float, get_shackle_offset, set_shackle_offset)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx = w / 2.0

        pen = QPen(self._color, 2.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)

        body_w, body_h = 30, 20
        body_x = cx - body_w / 2
        body_y = float(h - body_h - 6)
        body_rect = QRectF(body_x, body_y, body_w, body_h)
        p.setBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), 35))
        p.drawRoundedRect(body_rect, 5, 5)

        p.setBrush(self._color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx - 2.5, body_y + 5, 5, 5))
        p.setPen(QPen(self._color, 1.8, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(cx), int(body_y + 10), int(cx), int(body_y + 14))

        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        shackle_w = 16.0
        shackle_h = 18.0
        shackle_x = cx - shackle_w / 2.0
        shackle_top = body_y - shackle_h + 2.0

        ox = self._shackle_offset * 11.0
        oy = self._shackle_offset * -5.0

        path = QPainterPath()
        path.moveTo(shackle_x + ox, body_y)
        path.lineTo(shackle_x + ox, shackle_top + oy + shackle_h * 0.5)
        path.arcTo(
            QRectF(shackle_x + ox, shackle_top + oy, shackle_w, shackle_h * 0.9),
            180, -180
        )
        path.lineTo(shackle_x + shackle_w + ox, body_y)
        p.drawPath(path)
        p.end()

# ── ACTIVATION DIALOG ─────────────────────────────────────────────────────────
class ActivationDialog(QDialog):
    """License activation dialog"""
    def __init__(self, hwid, btn_style_func, card_style_func):
        super().__init__()
        self.hwid = hwid
        self.activated = False
        self.btn_style = btn_style_func
        self.card_style = card_style_func
        self.setWindowTitle("MAJENANG FLASHER — Aktivasi")
        self.setFixedSize(400, 480)
        self.setStyleSheet("background-color:#080810; color:#e2e8f0;")
        self._build_ui()

    def _small_label(self, text, color):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lbl.setStyleSheet(f"color:{color}; border:none;")
        return lbl

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet("background-color:#7c3aed;")
        root.addWidget(accent)

        inner_widget = QWidget()
        inner = QVBoxLayout(inner_widget)
        inner.setContentsMargins(24, 0, 24, 16)
        inner.setSpacing(0)

        self.lock_widget = LockWidget()
        lock_wrap = QHBoxLayout()
        lock_wrap.addStretch()
        lock_wrap.addWidget(self.lock_widget)
        lock_wrap.addStretch()
        inner.addSpacing(12)
        inner.addLayout(lock_wrap)

        self.title_lbl = QLabel("MAJENANG FLASHER")
        self.title_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet("color:#c084fc;")
        inner.addWidget(self.title_lbl)

        sub = QLabel("Aktivasi Lisensi")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color:#4b5563; padding-bottom:14px;")
        inner.addWidget(sub)

        hwid_card = QFrame()
        hwid_card.setStyleSheet(self.card_style("#0d0d1f", "#2a1f4a"))
        cl = QVBoxLayout(hwid_card)
        cl.setContentsMargins(12, 10, 12, 12)
        cl.setSpacing(4)

        lbl_h = QLabel("HARDWARE ID (HWID)")
        lbl_h.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lbl_h.setStyleSheet("color:#4b5563; border:none;")
        lbl_h.setAlignment(Qt.AlignCenter)
        cl.addWidget(lbl_h)

        hwid_row = QFrame()
        hwid_row.setStyleSheet("background-color:#111128; border-radius:8px; border:none;")
        hr_lay = QHBoxLayout(hwid_row)
        hr_lay.setContentsMargins(10, 6, 6, 6)
        hwid_val = QLabel(self.hwid)
        hwid_val.setFont(QFont("Segoe UI", 12, QFont.Bold))
        hwid_val.setStyleSheet("color:#fbbf24; border:none;")
        hr_lay.addWidget(hwid_val, 1)

        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setFixedWidth(72)
        self.copy_btn.setStyleSheet(self.btn_style("#1e1535", "#7c3aed", "#7c3aed", "#e2e8f0", 9, False, 28, 6))
        self.copy_btn.clicked.connect(self._copy_hwid)
        hr_lay.addWidget(self.copy_btn)
        cl.addWidget(hwid_row)

        note = QLabel("Kirim HWID ke Admin untuk mendapatkan License Key")
        note.setFont(QFont("Segoe UI", 8))
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("color:#6b7280; border:none;")
        cl.addWidget(note)

        wa = QFrame()
        wa.setStyleSheet("background-color:#052e16; border-radius:8px; border:none;")
        wa_l = QHBoxLayout(wa)
        wa_l.setContentsMargins(10, 8, 10, 8)
        wa_lbl = QLabel("📱 WhatsApp Admin: 0851-1740-8105")
        wa_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        wa_lbl.setStyleSheet("color:#4ade80; border:none;")
        wa_l.addWidget(wa_lbl, 0, Qt.AlignHCenter)
        cl.addWidget(wa)
        inner.addWidget(hwid_card)
        inner.addSpacing(8)

        lic_card = QFrame()
        lic_card.setStyleSheet(self.card_style("#0d0d1f", "#2a1f4a"))
        lc = QVBoxLayout(lic_card)
        lc.setContentsMargins(16, 12, 16, 12)
        lc.setSpacing(4)
        lc.addWidget(self._small_label("License Key", "#6b7280"))

        self.key_entry = QLineEdit()
        self.key_entry.setPlaceholderText("MJFL-XXXX-XXXX-XXXX-XXXX")
        self.key_entry.setFont(QFont("Segoe UI", 11))
        self.key_entry.setFixedHeight(38)
        self.key_entry.setStyleSheet("""
            QLineEdit {
                background-color:#111128; border:1px solid #2a2a4a; color:#e2e8f0;
                border-radius:8px; padding-left:10px; font-weight:bold;
            }
            QLineEdit:focus { border:1px solid #7c3aed; }
        """)
        lc.addWidget(self.key_entry)

        self.status_lbl = QLabel("")
        self.status_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.status_lbl.setAlignment(Qt.AlignCenter)
        lc.addWidget(self.status_lbl)

        self.act_btn = QPushButton("🔓 AKTIFKAN LISENSI SEKARANG")
        self.act_btn.setStyleSheet(self.btn_style("#7c3aed", "#9333ea", "#7c3aed", "#ffffff", 10, True, 40, 8))
        self.act_btn.clicked.connect(self._do_activate)
        lc.addWidget(self.act_btn)
        inner.addWidget(lic_card)

        root.addWidget(inner_widget)

    def _copy_hwid(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.hwid)
        self.copy_btn.setText("✔ Copied")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 Copy"))

    def _do_activate(self):
        from frp_license import save_license, validate_license_key, LICENSE_PREFIX
        key = self.key_entry.text().strip().upper()
        if not key:
            self.status_lbl.setText("❌ Masukkan License Key!")
            self.status_lbl.setStyleSheet("color:#f87171; border:none;")
            return

        parts = key.split("-")
        if len(parts) == 7 and parts[0] == LICENSE_PREFIX:
            timestamp = parts[6]
            save_license(key, self.hwid, timestamp)
            if validate_license_key(key, self.hwid):
                self.status_lbl.setText("✅ Lisensi Valid! Membuka Tool...")
                self.status_lbl.setStyleSheet("color:#22c55e; border:none;")
                self.activated = True
                QTimer.singleShot(1200, self.accept)
                return

        self.status_lbl.setText("❌ License Key Tidak Valid!")
        self.status_lbl.setStyleSheet("color:#f87171; border:none;")
