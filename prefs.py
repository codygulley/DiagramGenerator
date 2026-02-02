import os
import json
import platform
import subprocess
from typing import Dict


def get_config_path() -> str:
    """Return a path to the user config file for saving preferences."""
    try:
        if os.name == 'nt':
            appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
            cfg_dir = os.path.join(appdata, 'DiagramGenerator')
        else:
            cfg_dir = os.path.expanduser('~')
        os.makedirs(cfg_dir, exist_ok=True)
        return os.path.join(cfg_dir, 'diagram_config.json')
    except Exception:
        return os.path.join(os.path.expanduser('~'), '.diagram_config.json')


def load_preferences() -> Dict:
    path = get_config_path()
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_preferences(config: Dict):
    path = get_config_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f)
    except Exception:
        pass


def detect_system_theme() -> str:
    """Return 'dark' or 'light' based on OS settings where possible."""
    try:
        system = platform.system()
        if system == 'Windows':
            try:
                import winreg
                key = r'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize'
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                    val = winreg.QueryValueEx(k, 'AppsUseLightTheme')[0]
                    return 'light' if val == 1 else 'dark'
            except Exception:
                return 'light'
        elif system == 'Darwin':
            try:
                p = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'], capture_output=True, text=True)
                out = (p.stdout or p.stderr or '').strip()
                return 'dark' if out.lower().startswith('dark') else 'light'
            except Exception:
                return 'light'
    except Exception:
        pass
    return 'light'
