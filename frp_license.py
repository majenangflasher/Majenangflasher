import subprocess
import hashlib
import hmac
from datetime import datetime
import logging

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("majenang_frp_tool.log")]
)
logger = logging.getLogger(__name__)

# ── LICENSE SYSTEM ────────────────────────────────────────────────────────────
LICENSE_PREFIX = "MJFL"
SECRET_SALT    = "MajenangFlasher@2026#SecretKey!XYZ"
REG_PATH       = r"SOFTWARE\MajenangFlasher\License"

def get_hwid():
    """Get system HWID from CPU and Disk serial"""
    try:
        import sys
        _cf = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        cpu = subprocess.check_output("wmic cpu get ProcessorId", shell=True, creationflags=_cf, timeout=5).decode(errors="ignore")
        disk = subprocess.check_output("wmic diskdrive get SerialNumber", shell=True, creationflags=_cf, timeout=5).decode(errors="ignore")
        raw = (cpu + disk).replace("\n","").replace("\r","").replace(" ","").upper()
        return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    except subprocess.TimeoutExpired:
        logger.error("HWID retrieval timeout")
        return "0000000000000000"
    except Exception as e:
        logger.error(f"Error getting HWID: {e}")
        return "0000000000000000"

def _xor_encrypt(data: str, hwid: str) -> str:
    """XOR encryption using HWID as key"""
    key = (hwid.encode() * 4)[:16]
    result = []
    for i, c in enumerate(data.encode('utf-8')):
        result.append(c ^ key[i % len(key)])
    return bytes(result).hex().upper()

def _xor_decrypt(data_hex: str, hwid: str) -> str:
    """XOR decryption using HWID as key"""
    key = (hwid.encode() * 4)[:16]
    raw = bytes.fromhex(data_hex)
    result = []
    for i, c in enumerate(raw):
        result.append(c ^ key[i % len(key)])
    for enc in ('utf-8', 'cp949', 'gb2312', 'latin-1'):
        try:
            return bytes(result).decode(enc)
        except Exception:
            continue
    return bytes(result).decode('utf-8', errors='ignore')

def generate_license_key(hwid, timestamp=""):
    """Generate license key from HWID"""
    hwid   = hwid.strip().upper()
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw    = f"{LICENSE_PREFIX}:{hwid}:{SECRET_SALT}:{timestamp}"
    digest = hmac.new(SECRET_SALT.encode(), raw.encode(), digestmod=hashlib.sha256).hexdigest().upper()
    b1 = hwid[0:4];  b2 = hwid[4:8]
    b3 = digest[0:4]; b4 = digest[4:8]
    b5 = digest[8:12]
    return f"{LICENSE_PREFIX}-{b1}-{b2}-{b3}-{b4}-{b5}-{timestamp}"

def validate_license_key(key, hwid):
    """Validate license key against HWID"""
    parts = key.strip().upper().split("-")
    if len(parts) != 7 or parts[0] != LICENSE_PREFIX:
        return False
    hwid_from_key = parts[1] + parts[2]
    if hwid_from_key != hwid.strip().upper():
        return False
    
    stored = _load_registry_raw()
    if not stored:
        return False
    try:
        decrypted = _xor_decrypt(stored, hwid.strip().upper())
        parts_reg = decrypted.split("|")
        if len(parts_reg) < 3:
            return False
        saved_key   = parts_reg[0].strip()
        saved_ts    = parts_reg[2].strip()
        expected    = generate_license_key(hwid, saved_ts)
        return key.strip().upper() == expected.upper() and key.strip().upper() == saved_key.upper()
    except Exception as e:
        logger.error(f"Error validating license: {e}")
        return False

def _save_registry_raw(encrypted: str):
    """Save encrypted license to registry"""
    try:
        import winreg
        reg = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.SetValueEx(reg, "Data", 0, winreg.REG_SZ, encrypted)
        winreg.CloseKey(reg)
        logger.info("License saved to registry")
    except Exception as e:
        logger.error(f"Error saving to registry: {e}")

def _load_registry_raw():
    """Load encrypted license from registry"""
    try:
        import winreg
        reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        val, _ = winreg.QueryValueEx(reg, "Data")
        winreg.CloseKey(reg)
        return val.strip()
    except FileNotFoundError:
        logger.debug("Registry key not found")
        return None
    except Exception as e:
        logger.error(f"Error reading registry: {e}")
        return None

def _save_credit(credit: int):
    """Save credit to registry"""
    try:
        import winreg
        reg = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.SetValueEx(reg, "Credit", 0, winreg.REG_DWORD, credit)
        winreg.CloseKey(reg)
        logger.info(f"Credit saved: {credit}")
    except Exception as e:
        logger.error(f"Error saving credit: {e}")

def _load_credit(default: int = 9800) -> int:
    """Load credit from registry"""
    try:
        import winreg
        reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        val, _ = winreg.QueryValueEx(reg, "Credit")
        winreg.CloseKey(reg)
        return int(val)
    except Exception as e:
        logger.debug(f"Error reading credit: {e}")
        return default

def save_license(key, hwid, timestamp):
    """Save license key+token+timestamp encrypted to registry"""
    try:
        import uuid
        token     = uuid.uuid4().hex.upper()
        plaintext = f"{key.strip().upper()}|{token}|{timestamp.strip()}"
        encrypted = _xor_encrypt(plaintext, hwid.strip().upper())
        _save_registry_raw(encrypted)
        return True
    except Exception as e:
        logger.error(f"Error saving license: {e}")
        return False

def check_license():
    """Check if license is valid"""
    hwid      = get_hwid()
    encrypted = _load_registry_raw()
    if not encrypted:
        logger.info("No license found")
        return False, hwid
    try:
        decrypted = _xor_decrypt(encrypted, hwid)
        parts     = decrypted.split("|")
        if len(parts) < 3:
            return False, hwid
        saved_key = parts[0].strip()
        saved_ts  = parts[2].strip()
        expected  = generate_license_key(hwid, saved_ts)
        valid     = saved_key.upper() == expected.upper()
        logger.info(f"License check: {'VALID' if valid else 'INVALID'}")
        return valid, hwid
    except Exception as e:
        logger.error(f"Error checking license: {e}")
        return False, hwid
