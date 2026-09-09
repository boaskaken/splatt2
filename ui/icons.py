"""Window icons with a native Windows fallback, independent of Tcl file paths."""
import base64
import ctypes
from ctypes import wintypes
import logging
import sys
import tkinter as tk

from core.paths import resource_path

log = logging.getLogger(__name__)


def configure_taskbar():
    if sys.platform == "win32":
        try:
            function = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
            function.argtypes = [wintypes.LPCWSTR]
            function.restype = ctypes.c_long
            result = function("boaskaken.Splatt2.Community")
            if result < 0:
                raise OSError(f"AppUserModelID failed: {result}")
        except (OSError, AttributeError):
            log.exception("Could not set taskbar identity")


def _set_windows_icon(root):
    """Set both HICON sizes on the actual Windows top-level window."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR,
                                 wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                    ctypes.c_size_t, ctypes.c_ssize_t]
    user32.SendMessageW.restype = ctypes.c_ssize_t
    user32.DestroyIcon.argtypes = [wintypes.HANDLE]
    user32.DestroyIcon.restype = wintypes.BOOL
    handles = getattr(root, "_native_icons", [])
    created = not handles
    try:
        path = str(resource_path("assets", "splatt2.ico"))
        if created:
            for size in (16, 32):
                handle = user32.LoadImageW(None, path, 1, size, size, 0x10)
                if not handle:
                    raise ctypes.WinError(ctypes.get_last_error())
                handles.append(handle)
        # Tk can create/replace its wrapper HWND when the window is mapped.
        hwnd = int(root.wm_frame(), 0)
        if not hwnd:
            hwnd = user32.GetAncestor(root.winfo_id(), 2) or root.winfo_id()
        # WM_SETICON: ICON_SMALL=0, ICON_BIG=1 (title bar and taskbar).
        for kind, handle in enumerate(handles):
            user32.SendMessageW(hwnd, 0x80, kind, handle)
            actual = user32.SendMessageW(hwnd, 0x7F, kind, 0)  # WM_GETICON
            if actual != handle:
                raise OSError(f"Window rejected icon {kind}: HWND={hwnd}")
        root._native_icons = handles
        def release(event):
            if event.widget is root:
                for handle in handles:
                    user32.DestroyIcon(handle)
                handles.clear()
        if created:
            root.bind("<Destroy>", release, add="+")
        log.info("Target icons applied to HWND=%s; file=%s", hwnd, path)
    except (OSError, ValueError, tk.TclError):
        # Keep assigned handles alive; Windows may still be displaying them.
        root._native_icons = handles
        log.exception("Could not set native Windows icons")


def set_window_icon(root):
    try:
        # Python reads the file; Tcl receives image bytes, not a Windows path.
        data = base64.b64encode(resource_path("assets", "splatt2.png").read_bytes())
        root._app_icon = tk.PhotoImage(master=root, data=data, format="png")
        root.iconphoto(True, root._app_icon)
    except (OSError, tk.TclError):
        log.exception("Could not load PNG application icon")
    if sys.platform == "win32":
        try:
            path = str(resource_path("assets", "splatt2.ico"))
            root.iconbitmap(bitmap=path, default=path)
        except (OSError, tk.TclError):
            log.exception("Could not set default window icon; trying native Windows icons")
        def mapped(event=None):
            if event is None or event.widget is root:
                root.after_idle(lambda: _set_windows_icon(root))
        root.bind("<Map>", mapped, add="+")
        # Apply again after Tk has mapped its native wrapper, not just during
        # construction, when Tk can overwrite the Windows icon afterwards.
        root.after(250, mapped)
