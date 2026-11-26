from __future__ import annotations
import sys
from pathlib import Path

def set_launch_at_login(enabled: bool) -> tuple[bool, str]:
    if sys.platform != "win32":
        return False, "Windows startup integration is available only on Windows."
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )
        name = "JudyAssistant"
        if enabled:
            exe = Path(sys.executable)
            if getattr(sys, "frozen", False):
                command = f'"{exe}" --background'
            else:
                command = f'"{exe}" -m judy.main --background'
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True, "Launch at login enabled." if enabled else "Launch at login disabled."
    except Exception as e:
        return False, str(e)
