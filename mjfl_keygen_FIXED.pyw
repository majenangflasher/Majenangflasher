import hashlib
import hmac
import tkinter as tk
import subprocess
from datetime import datetime
import logging

# ── Logging Setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("mjfl_keygen.log")]
)
logger = logging.getLogger(__name__)

LICENSE_PREFIX = "MJFL"
SECRET_SALT    = "MajenangFlasher@2026#SecretKey!XYZ"

def generate_license_key(hwid, timestamp=""):
    """Generate license key from HWID"""
    try:
        hwid   = hwid.strip().upper()
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        raw    = f"{LICENSE_PREFIX}:{hwid}:{SECRET_SALT}:{timestamp}"
        digest = hmac.new(SECRET_SALT.encode(), raw.encode(), digestmod=hashlib.sha256).hexdigest().upper()
        b1,b2  = hwid[0:4], hwid[4:8]
        b3,b4  = digest[0:4], digest[4:8]
        b5     = digest[8:12]
        key = f"{LICENSE_PREFIX}-{b1}-{b2}-{b3}-{b4}-{b5}-{timestamp}"
        logger.info(f"Key generated for HWID: {hwid}")
        return key
    except Exception as e:
        logger.error(f"Error generating key: {e}")
        return None

def get_own_hwid():
    """Get PC HWID from WMIC"""
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        
        cpu = subprocess.check_output(
            ["wmic", "cpu", "get", "ProcessorId"],
            startupinfo=si,
            stderr=subprocess.DEVNULL,
            timeout=10
        ).decode(errors="ignore")
        
        disk = subprocess.check_output(
            ["wmic", "diskdrive", "get", "SerialNumber"],
            startupinfo=si,
            stderr=subprocess.DEVNULL,
            timeout=10
        ).decode(errors="ignore")
        
        raw = (cpu+disk).replace("\n","").replace("\r","").replace(" ","").upper()
        hwid = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
        logger.info(f"HWID retrieved: {hwid}")
        return hwid
    except subprocess.TimeoutExpired:
        logger.error("HWID retrieval timeout")
        return "0000000000000000"
    except FileNotFoundError:
        logger.error("WMIC not found")
        return "0000000000000000"
    except Exception as e:
        logger.error(f"Error getting HWID: {e}")
        return "0000000000000000"

# ── UI Setup ───────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("MJFL Key Generator — ADMIN ONLY")
root.resizable(False, False)
root.configure(bg="#080810")

F_TITLE = ("Segoe UI", 15, "bold")
F_SUB   = ("Segoe UI", 8)
F_INPUT = ("Consolas", 12, "bold")
F_BTN   = ("Segoe UI", 10, "bold")
F_FOOT  = ("Segoe UI", 7)

# Top accent bar
tk.Frame(root, bg="#7c3aed", height=3).pack(fill="x")

# Header
hdr = tk.Frame(root, bg="#0d0d1f")
hdr.pack(fill="x")
icon_lbl = tk.Label(hdr, text="🔑", bg="#0d0d1f", fg="#c084fc", font=("Segoe UI", 30))
icon_lbl.pack(pady=(18,2))
title_lbl = tk.Label(hdr, text="MAJENANG FLASHER", bg="#0d0d1f", fg="#c084fc", font=F_TITLE)
title_lbl.pack()
tk.Label(hdr, text="KEY GENERATOR  ·  ADMIN ONLY  ·  v2.0", bg="#0d0d1f", fg="#4b5563", font=F_SUB).pack(pady=(2,16))
tk.Frame(root, bg="#1e1e3a", height=1).pack(fill="x")

# Glow pulse animation untuk title & icon
_glow_colors = [
    "#6b21a8","#7c3aed","#9333ea","#a855f7","#c084fc",
    "#d8b4fe","#c084fc","#a855f7","#9333ea","#7c3aed","#6b21a8"
]
_glow_step = [0]
def _pulse_glow():
    c = _glow_colors[_glow_step[0] % len(_glow_colors)]
    title_lbl.configure(fg=c)
    icon_lbl.configure(fg=c)
    _glow_step[0] += 1
    root.after(80, _pulse_glow)
_pulse_glow()

# HWID Admin
own_frame = tk.Frame(root, bg="#080810")
own_frame.pack(fill="x", padx=24, pady=(14,0))
tk.Label(own_frame, text="HWID PC ADMIN", bg="#080810", fg="#4b5563", font=("Segoe UI", 8, "bold")).pack(anchor="w")
own_inner = tk.Frame(own_frame, bg="#111128", pady=6)
own_inner.pack(fill="x", pady=(4,0))
own_hwid = get_own_hwid()
tk.Label(own_inner, text=own_hwid, bg="#111128", fg="#6b7280", font=("Consolas", 11)).pack(side="left", padx=10)

# HWID User
card1 = tk.Frame(root, bg="#0d0d1f")
card1.pack(fill="x", padx=24, pady=(14,0))
tk.Frame(card1, bg="#2a1f4a", height=1).pack(fill="x")
inner1 = tk.Frame(card1, bg="#0d0d1f")
inner1.pack(fill="x")
tk.Frame(card1, bg="#2a1f4a", height=1).pack(fill="x")
tk.Label(inner1, text="HWID USER", bg="#0d0d1f", fg="#4b5563", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(10,2))
hwid_var = tk.StringVar()
hwid_entry = tk.Entry(inner1, textvariable=hwid_var, bg="#111128", fg="#fbbf24",
    insertbackground="#fbbf24", font=F_INPUT, relief="flat", bd=8,
    highlightthickness=1, highlightbackground="#2a2a4a", highlightcolor="#7c3aed")
hwid_entry.pack(fill="x", padx=14, pady=(0,10))

# License Key
card2 = tk.Frame(root, bg="#0d0d1f")
card2.pack(fill="x", padx=24, pady=(10,0))
tk.Frame(card2, bg="#2a1f4a", height=1).pack(fill="x")
inner2 = tk.Frame(card2, bg="#0d0d1f")
inner2.pack(fill="x")
tk.Frame(card2, bg="#2a1f4a", height=1).pack(fill="x")
tk.Label(inner2, text="LICENSE KEY", bg="#0d0d1f", fg="#4b5563", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(10,2))
result_var = tk.StringVar()
result_entry = tk.Entry(inner2, textvariable=result_var, bg="#111128", fg="#22c55e",
    insertbackground="#22c55e", font=F_INPUT, relief="flat", bd=8, state="readonly",
    highlightthickness=1, highlightbackground="#2a2a4a", highlightcolor="#22c55e",
    readonlybackground="#111128")
result_entry.pack(fill="x", padx=14, pady=(0,10))

# Status
status_var = tk.StringVar(value="")
status_lbl = tk.Label(root, textvariable=status_var, bg="#080810", fg="#f87171", font=("Segoe UI", 9, "bold"))
status_lbl.pack(pady=(8,0))

# Buttons
btn_frame = tk.Frame(root, bg="#080810")
btn_frame.pack(pady=14)

def do_generate(event=None):
    """Generate license key"""
    try:
        hwid = hwid_var.get().strip().upper()
        if len(hwid) != 16:
            status_var.set("✘  HWID harus tepat 16 karakter!")
            status_lbl.configure(fg="#f87171")
            result_var.set("")
            logger.warning(f"Invalid HWID length: {len(hwid)}")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        key = generate_license_key(hwid, timestamp)
        
        if not key:
            status_var.set("✘  Gagal generate key!")
            status_lbl.configure(fg="#f87171")
            result_var.set("")
            return
        
        result_var.set(key)
        status_var.set(f"✔  Key digenerate! [{timestamp}]")
        status_lbl.configure(fg="#22c55e")
    except Exception as e:
        status_var.set(f"✘  Error: {str(e)}")
        status_lbl.configure(fg="#f87171")
        logger.error(f"Generate error: {e}")

def do_copy():
    """Copy key to clipboard"""
    try:
        key = result_var.get()
        if not key:
            status_var.set("✘  Generate key dulu!")
            status_lbl.configure(fg="#f87171")
            return
        root.clipboard_clear()
        root.clipboard_append(key)
        status_var.set("✔  Key disalin ke clipboard!")
        status_lbl.configure(fg="#22c55e")
        logger.info("Key copied to clipboard")
    except Exception as e:
        status_var.set(f"✘  Error: {str(e)}")
        status_lbl.configure(fg="#f87171")
        logger.error(f"Copy error: {e}")

def do_clear():
    """Clear all inputs"""
    try:
        hwid_var.set("")
        result_var.set("")
        status_var.set("")
        hwid_entry.focus()
        logger.info("Cleared all inputs")
    except Exception as e:
        logger.error(f"Clear error: {e}")

def make_rounded_btn(parent, text, icon, bg, fg, glow, hover_bg, command):
    """Create rounded button using Canvas"""
    BTN_W, BTN_H, RADIUS = 148, 40, 12
    cv = tk.Canvas(parent, width=BTN_W, height=BTN_H,
                   bg="#080810", highlightthickness=0, cursor="hand2")

    def draw(bg_col, glow_col):
        cv.delete("all")
        
        # glow layer
        for i in range(4, 0, -1):
            cv.create_polygon(
                i+RADIUS,i, BTN_W-i-RADIUS,i, BTN_W-i,i+RADIUS,
                BTN_W-i,BTN_H-i-RADIUS, BTN_W-i-RADIUS,BTN_H-i,
                i+RADIUS,BTN_H-i, i,BTN_H-i-RADIUS, i,i+RADIUS,
                smooth=True, fill="", outline=glow_col, width=1)
        
        # main bg with rounded corners
        cv.create_polygon(
            RADIUS,0, BTN_W-RADIUS,0, BTN_W,RADIUS,
            BTN_W,BTN_H-RADIUS, BTN_W-RADIUS,BTN_H,
            RADIUS,BTN_H, 0,BTN_H-RADIUS, 0,RADIUS,
            smooth=True, fill=bg_col, outline=glow_col, width=2)
        
        # text with icon
        cv.create_text(BTN_W//2, BTN_H//2, text=f"{icon}  {text}",
                       fill=fg, font=F_BTN)

    draw(bg, glow)

    def on_enter(e):
        draw(hover_bg, glow)
    def on_leave(e):
        draw(bg, glow)
    def on_click(e):
        if command:
            command()

    cv.bind("<Enter>", on_enter)
    cv.bind("<Leave>", on_leave)
    cv.bind("<Button-1>", on_click)
    return cv

def do_generate_with_log(event=None):
    """Generate and log to history"""
    do_generate(event)
    if result_var.get():
        add_to_history(hwid_var.get().strip().upper(), result_var.get())

# Create buttons
gen_btn  = make_rounded_btn(btn_frame, "GENERATE KEY", "🔑", "#9B30FF", "white",  "#CC77FF", "#BB55FF", do_generate_with_log)
copy_btn = make_rounded_btn(btn_frame, "COPY KEY",     "📋", "#003d4d", "#00D4FF","#00D4FF", "#005566", do_copy)
clear_btn= make_rounded_btn(btn_frame, "CLEAR",        "🗑️", "#3d0000", "#FF3C3C","#FF3C3C", "#550000", do_clear)

gen_btn.grid(row=0, column=0, padx=5)
copy_btn.grid(row=0, column=1, padx=5)
clear_btn.grid(row=0, column=2, padx=5)

# History
tk.Frame(root, bg="#1e1e3a", height=1).pack(fill="x", padx=24, pady=(8,0))
log_frame = tk.Frame(root, bg="#080810")
log_frame.pack(fill="x", padx=24, pady=(8,0))
tk.Label(log_frame, text="HISTORY", bg="#080810", fg="#4b5563", font=("Segoe UI", 8, "bold")).pack(anchor="w")
log_box = tk.Text(log_frame, bg="#0d0d1f", fg="#6b7280", font=("Consolas", 8),
    relief="flat", bd=4, height=4, state="disabled",
    highlightthickness=1, highlightbackground="#1e1e3a")
log_box.pack(fill="x", pady=(4,0))

history = []

def add_to_history(hwid, key):
    """Add entry to history"""
    try:
        history.append(f"HWID: {hwid}  →  {key}")
        log_box.configure(state="normal")
        log_box.delete("1.0", "end")
        for h in history[-4:]:
            log_box.insert("end", h + "\n")
        log_box.configure(state="disabled")
        logger.info("Entry added to history")
    except Exception as e:
        logger.error(f"History error: {e}")

hwid_entry.bind("<Return>", do_generate_with_log)

# Footer
tk.Frame(root, bg="#1e1e3a", height=1).pack(fill="x", pady=(8,0))
tk.Label(root, text="⚡  MAJENANG FLASHER SOLUTION  |  KEY GENERATOR v2.0  |  ADMIN ONLY",
    bg="#080810", fg="#4b5563", font=F_FOOT).pack(pady=6)

# Center window
root.update_idletasks()
w = root.winfo_width()
h = root.winfo_height()
sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()
root.geometry(f"{w}x{h}+{sw//2-w//2}+{sh//2-h//2}")

def on_closing():
    """Handle window close"""
    logger.info("Application closing")
    root.quit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

logger.info("Application started")
root.mainloop()
logger.info("Application closed")
