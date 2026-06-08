import shutil
import customtkinter as ctk
import subprocess
import os
import sys
import string
import logging
from datetime import datetime

# ── Logging Setup ──────────────────────────────────────────────────────────────
log_file = os.path.join(os.path.dirname(__file__), "mjfl_reset_tool.log")
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
import hashlib as _hashlib
_ADMIN_RAW = "salebu45"
ADMIN_PASSWORD_HASH = _hashlib.sha256(_ADMIN_RAW.encode()).hexdigest()
del _ADMIN_RAW  
FONT_MAIN = "Segoe UI"

# ── Cari semua mjfl.lic di seluruh drive ──────────────────────────────────────
def get_all_drives():
    """Get all available drives on Windows"""
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        try:
            if os.path.exists(drive):
                drives.append(drive)
        except PermissionError:
            logger.debug(f"Permission denied accessing {drive}")
        except Exception as e:
            logger.debug(f"Error checking drive {drive}: {e}")
    return drives

def find_all_lic_files():
    """Find all mjfl.lic files in system"""
    found = []
    logger.info("Starting license file search...")

    # 1. APPDATA
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        try:
            p = os.path.join(appdata, ".mjfl_data", "mjfl.lic")
            if os.path.exists(p):
                found.append(p)
                logger.info(f"Found: {p}")
        except Exception as e:
            logger.warning(f"Error checking APPDATA: {e}")

    # 2. Semua drive — scan 3 level
    for drive in get_all_drives():
        try:
            for entry1 in os.scandir(drive):
                if not entry1.is_dir(follow_symlinks=False):
                    continue
                try:
                    p = os.path.join(entry1.path, "mjfl.lic")
                    if os.path.exists(p) and p not in found:
                        found.append(p)
                        logger.info(f"Found: {p}")
                except Exception:
                    pass
                
                try:
                    for entry2 in os.scandir(entry1.path):
                        if not entry2.is_dir(follow_symlinks=False):
                            continue
                        p2 = os.path.join(entry2.path, "mjfl.lic")
                        if os.path.exists(p2) and p2 not in found:
                            found.append(p2)
                            logger.info(f"Found: {p2}")
                except Exception:
                    pass
        except PermissionError:
            logger.debug(f"Permission denied scanning {drive}")
        except Exception as e:
            logger.debug(f"Error scanning {drive}: {e}")

    # 3. Semua user di semua drive
    common_subs = ["Desktop", "Downloads", "Documents", "AppData\\Roaming", "AppData\\Local"]
    for drive in get_all_drives():
        users_dir = os.path.join(drive, "Users")
        try:
            if not os.path.exists(users_dir):
                continue
            for user_entry in os.scandir(users_dir):
                if not user_entry.is_dir(follow_symlinks=False):
                    continue
                user_path = user_entry.path

                try:
                    p_hidden = os.path.join(user_path, "AppData", "Roaming", ".mjfl_data", "mjfl.lic")
                    if os.path.exists(p_hidden) and p_hidden not in found:
                        found.append(p_hidden)
                        logger.info(f"Found: {p_hidden}")
                except Exception:
                    pass

                for sub in common_subs:
                    try:
                        sub_path = os.path.join(user_path, sub)
                        if not os.path.exists(sub_path):
                            continue
                        p = os.path.join(sub_path, "mjfl.lic")
                        if os.path.exists(p) and p not in found:
                            found.append(p)
                            logger.info(f"Found: {p}")
                        
                        for e1 in os.scandir(sub_path):
                            if not e1.is_dir(follow_symlinks=False):
                                continue
                            p1 = os.path.join(e1.path, "mjfl.lic")
                            if os.path.exists(p1) and p1 not in found:
                                found.append(p1)
                                logger.info(f"Found: {p1}")
                            
                            try:
                                for e2 in os.scandir(e1.path):
                                    if not e2.is_dir(follow_symlinks=False):
                                        continue
                                    p2 = os.path.join(e2.path, "mjfl.lic")
                                    if os.path.exists(p2) and p2 not in found:
                                        found.append(p2)
                                        logger.info(f"Found: {p2}")
                            except Exception as e:
                                logger.debug(f"Error in nested scan: {e}")
                    except Exception as e:
                        logger.debug(f"Error scanning {sub}: {e}")
        except PermissionError:
            logger.debug(f"Permission denied accessing Users on {drive}")
        except Exception as e:
            logger.debug(f"Error scanning users on {drive}: {e}")

    logger.info(f"Search complete. Found {len(found)} license files.")
    return found

REG_PATH = r"SOFTWARE\MajenangFlasher\License"

def delete_registry():
    """Delete registry entries safely"""
    try:
        import winreg
        
        try:
            reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS)
            try:
                winreg.DeleteValue(reg, "Data")
                logger.info("Deleted registry value: Data")
            except FileNotFoundError:
                logger.debug("Registry value 'Data' not found")
            except Exception as e:
                logger.warning(f"Error deleting Data value: {e}")
            
            try:
                winreg.DeleteValue(reg, "Credit")
                logger.info("Deleted registry value: Credit")
            except FileNotFoundError:
                logger.debug("Registry value 'Credit' not found")
            except Exception as e:
                logger.warning(f"Error deleting Credit value: {e}")
            
            winreg.CloseKey(reg)
        except FileNotFoundError:
            logger.info("Registry key not found")
            return True
        except PermissionError as e:
            logger.error(f"Permission denied accessing registry: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting registry values: {e}")
            return False
        
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_PATH)
            logger.info(f"Deleted registry key: {REG_PATH}")
            return True
        except FileNotFoundError:
            logger.info("Registry key already deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting registry key: {e}")
            return False
            
    except ImportError:
        logger.error("winreg module not available")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in delete_registry: {e}")
        return False

def unhide_and_delete(path):
    """Remove file attributes and delete"""
    try:
        try:
            subprocess.run(
                ["attrib", "-h", "-s", "-r", path],
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=False,
                timeout=10
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout unhiding {path}, attempting delete anyway")
        except FileNotFoundError:
            logger.error("attrib.exe not found")
            return False
        except Exception as e:
            logger.warning(f"Error unhiding {path}: {e}")
        
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted: {path}")
            return True
        else:
            logger.warning(f"File not found: {path}")
            return False
            
    except PermissionError as e:
        logger.error(f"Permission denied deleting {path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error deleting {path}: {e}")
        return False

def delete_all_licenses():
    """Main function to delete all license files and registry"""
    results = []
    logger.info("=" * 60)
    logger.info("STARTING LICENSE DELETION PROCESS")
    logger.info("=" * 60)

    # 1. Hapus registry
    try:
        reg_ok = delete_registry()
        if reg_ok:
            results.append(("✔", f"Registry dihapus: HKCU\\{REG_PATH}", "#22c55e"))
        else:
            results.append(("⚠", f"Registry gagal dihapus atau tidak ditemukan", "#fbbf24"))
    except Exception as e:
        logger.error(f"Registry deletion exception: {e}")
        results.append(("✘", f"Registry error: {str(e)}", "#f87171"))

    # 2. Hapus semua file lisensi
    try:
        files = find_all_lic_files()
        if not files:
            results.append(("⚠", "Tidak ada file mjfl.lic yang ditemukan", "#fbbf24"))
        else:
            for path in files:
                ok = unhide_and_delete(path)
                if ok:
                    results.append(("✔", f"Dihapus: {path}", "#22c55e"))
                else:
                    results.append(("✘", f"Gagal hapus: {path}", "#f87171"))
    except Exception as e:
        logger.error(f"License file deletion exception: {e}")
        results.append(("✘", f"Error scanning files: {str(e)}", "#f87171"))

    # 3. Hapus folder cadangan .mjfl_data
    try:
        for drive in get_all_drives():
            users_dir = os.path.join(drive, "Users")
            if not os.path.exists(users_dir):
                continue
            try:
                for user_entry in os.scandir(users_dir):
                    if not user_entry.is_dir(follow_symlinks=False):
                        continue
                    hidden_dir = os.path.join(user_entry.path, "AppData", "Roaming", ".mjfl_data")
                    try:
                        if os.path.exists(hidden_dir):
                            try:
                                subprocess.run(
                                    ["attrib", "-h", "-s", "-r", hidden_dir, "/S", "/D"],
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                    shell=False,
                                    timeout=15
                                )
                            except subprocess.TimeoutExpired:
                                logger.warning(f"Timeout unhiding {hidden_dir}")
                            except Exception as e:
                                logger.warning(f"Error unhiding directory: {e}")
                            
                            try:
                                shutil.rmtree(hidden_dir, ignore_errors=True)
                                if not os.path.exists(hidden_dir):
                                    results.append(("✔", f"Folder dihapus: {hidden_dir}", "#22c55e"))
                                    logger.info(f"Folder deleted: {hidden_dir}")
                                else:
                                    results.append(("✘", f"Gagal hapus folder: {hidden_dir}", "#f87171"))
                            except Exception as e:
                                logger.error(f"Error deleting folder {hidden_dir}: {e}")
                    except Exception as e:
                        logger.debug(f"Error processing hidden directory: {e}")
            except Exception as e:
                logger.debug(f"Error scanning users on {drive}: {e}")
    except Exception as e:
        logger.error(f"Folder deletion exception: {e}")

    logger.info("=" * 60)
    logger.info("LICENSE DELETION PROCESS COMPLETE")
    logger.info("=" * 60)
    return results

# ── UI ─────────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception as e:
        logger.warning(f"Could not hide console: {e}")

app = ctk.CTk()
app.title("MJFL License Reset Tool — Admin v2.0")
app.geometry("460x520")
app.resizable(False, False)
app.configure(fg_color="#080810")

app.update_idletasks()
sw = app.winfo_screenwidth()
sh = app.winfo_screenheight()
app.geometry(f"460x520+{sw//2-230}+{sh//2-260}")

ctk.CTkFrame(app, fg_color="#7c3aed", height=3, corner_radius=0).pack(fill="x")

ctk.CTkLabel(app, text="🔑", font=ctk.CTkFont(family=FONT_MAIN, size=36),
             text_color="#7c3aed").pack(pady=(20, 4))
ctk.CTkLabel(app, text="MJFL LICENSE RESET", font=ctk.CTkFont(family=FONT_MAIN, size=15, weight="bold"),
             text_color="#c084fc").pack()
ctk.CTkLabel(app, text="Admin Tool — Majenang Flasher | v2.0 Production",
             font=ctk.CTkFont(family=FONT_MAIN, size=9), text_color="#4b5563").pack(pady=(2, 16))

pw_card = ctk.CTkFrame(app, fg_color="#0d0d1f", corner_radius=10,
                        border_width=1, border_color="#2a1f4a")
pw_card.pack(fill="x", padx=24, pady=(0, 10))

ctk.CTkLabel(pw_card, text="Password Admin", font=ctk.CTkFont(family=FONT_MAIN, size=10),
             text_color="#6b7280", anchor="w").pack(fill="x", padx=16, pady=(12, 2))

pw_entry = ctk.CTkEntry(pw_card, placeholder_text="Masukkan password admin...",
    fg_color="#111128", border_color="#2a2a4a", text_color="#e2e8f0",
    font=ctk.CTkFont(family=FONT_MAIN, size=11), height=36, corner_radius=8, show="●")
pw_entry.pack(fill="x", padx=16, pady=(0, 6))

pw_status = ctk.CTkLabel(pw_card, text="", font=ctk.CTkFont(family=FONT_MAIN, size=10, weight="bold"),
                          text_color="#f87171")
pw_status.pack(pady=(0, 10))

result_card = ctk.CTkFrame(app, fg_color="#0d0d1f", corner_radius=10,
                             border_width=1, border_color="#2a1f4a")
result_card.pack(fill="both", expand=True, padx=24, pady=(0, 10))

ctk.CTkLabel(result_card, text="HASIL", font=ctk.CTkFont(family=FONT_MAIN, size=8, weight="bold"),
             text_color="#4b5563").pack(pady=(10, 4))

result_text = ctk.CTkTextbox(result_card, fg_color="#111128", text_color="#4ade80",
    font=ctk.CTkFont(family=FONT_MAIN, size=10), corner_radius=8, border_width=0,
    state="disabled")
result_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

def log_result(icon, msg, color="#4ade80"):
    """Log result to UI textbox"""
    try:
        result_text.configure(state="normal")
        result_text.insert("end", f"{icon}  {msg}\n")
        result_text.configure(state="disabled")
        result_text.see("end")
    except Exception as e:
        logger.error(f"Error logging result: {e}")

def clear_result():
    """Clear result textbox"""
    try:
        result_text.configure(state="normal")
        result_text.delete("1.0", "end")
        result_text.configure(state="disabled")
    except Exception as e:
        logger.error(f"Error clearing results: {e}")

def do_reset(event=None):
    """Main reset function"""
    try:
        pw = pw_entry.get().strip()
        if not pw:
            pw_status.configure(text="✘  Masukkan password!", text_color="#f87171")
            logger.warning("Reset attempt with empty password")
            return
        
        import hashlib as _hl
        pw_hash = _hl.sha256(pw.encode()).hexdigest()
        
        if pw_hash != ADMIN_PASSWORD_HASH:
            pw_status.configure(text="✘  Password salah!", text_color="#f87171")
            pw_entry.delete(0, "end")
            logger.warning("Reset attempt with incorrect password")
            return

        pw_status.configure(text="✔  Password benar!", text_color="#22c55e")
        logger.info("Password verified - starting reset")
        
        clear_result()
        log_result("~", "Mencari semua file lisensi...", "#60a5fa")
        app.update()

        results = delete_all_licenses()
        
        for icon, msg, color in results:
            log_result(icon, msg, color)
            app.update()

        log_result("─", "─" * 38, "#2a2a4a")
        success = sum(1 for i, _, _ in results if i == "✔")
        log_result("✔" if success else "⚠",
                   f"Selesai. {success} file berhasil dihapus.",
                   "#22c55e" if success else "#fbbf24")
        
        logger.info(f"Reset complete. {success} items deleted successfully.")
        
        pw_entry.delete(0, "end")
        pw_status.configure(text="")
        
    except Exception as e:
        logger.error(f"Error in do_reset: {e}", exc_info=True)
        log_result("✘", f"Error: {str(e)}", "#f87171")
        pw_status.configure(text="✘  Error occurred!", text_color="#f87171")

pw_entry.bind("<Return>", do_reset)

ctk.CTkButton(app, text="🗑  HAPUS SEMUA LISENSI", fg_color="#6d28d9", hover_color="#5b21b6",
    font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"), height=42, corner_radius=10,
    border_width=1, border_color="#7c3aed", command=do_reset).pack(fill="x", padx=24, pady=(0, 8))

ctk.CTkLabel(app, text="⚡  MAJENANG FLASHER SOLUTION  |  v2.0 PRODUCTION",
    font=ctk.CTkFont(family=FONT_MAIN, size=8), text_color="#1e1e3a").pack(pady=(0, 8))

logger.info("Application started")

try:
    app.mainloop()
except Exception as e:
    logger.critical(f"Critical error in mainloop: {e}", exc_info=True)
    app.destroy()

logger.info("Application closed")
