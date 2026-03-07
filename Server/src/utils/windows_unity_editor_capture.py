from __future__ import annotations

import ctypes
import io
import json
import subprocess
import time
from ctypes import wintypes

from PIL import ImageGrab


user32 = ctypes.WinDLL("user32", use_last_error=True)


SW_RESTORE = 9


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL


def _find_unity_pid_for_project(project_name: str) -> int | None:
    escaped = project_name.replace("'", "''")
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -eq 'Unity.exe' -and $_.CommandLine -match '-projectpath' } | "
        "Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    if isinstance(rows, dict):
        rows = [rows]

    lowered = project_name.lower()
    for row in rows:
        command_line = (row.get("CommandLine") or "").lower()
        if f"\\{lowered}" in command_line or f"/{lowered}" in command_line or command_line.endswith(lowered):
            return int(row["ProcessId"])
    return None


def _find_best_window_for_pid(pid: int) -> int | None:
    best_hwnd = 0
    best_area = 0

    @EnumWindowsProc
    def callback(hwnd: int, _lparam: int) -> bool:
        nonlocal best_hwnd, best_area
        if not user32.IsWindowVisible(hwnd):
            return True

        owner_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
        if owner_pid.value != pid:
            return True

        rect = RECT()
        if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return True

        width = max(0, rect.right - rect.left)
        height = max(0, rect.bottom - rect.top)
        area = width * height
        if area <= best_area:
            return True

        best_hwnd = hwnd
        best_area = area
        return True

    user32.EnumWindows(callback, 0)
    return best_hwnd or None


def capture_unity_editor_window(project_name: str) -> dict | None:
    pid = _find_unity_pid_for_project(project_name)
    if not pid:
        return None

    hwnd = _find_best_window_for_pid(pid)
    if not hwnd:
        return None

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.2)

    user32.SetForegroundWindow(hwnd)
    time.sleep(0.15)

    rect = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None

    top_left = POINT(0, 0)
    bottom_right = POINT(rect.right, rect.bottom)
    if not user32.ClientToScreen(hwnd, ctypes.byref(top_left)):
        return None
    if not user32.ClientToScreen(hwnd, ctypes.byref(bottom_right)):
        return None

    bbox = (top_left.x, top_left.y, bottom_right.x, bottom_right.y)
    image = ImageGrab.grab(bbox=bbox, all_screens=True)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    png = buffer.getvalue()

    return {
        "success": True,
        "width": image.width,
        "height": image.height,
        "format": "png",
        "size_bytes": len(png),
        "image_base64": __import__("base64").b64encode(png).decode("ascii"),
        "capture_backend": "server_hwnd_client_bbox",
    }