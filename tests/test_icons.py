import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from ui import icons


class IconTests(unittest.TestCase):
    def test_png_failure_does_not_skip_windows_fallback(self):
        root = Mock()
        with patch.object(icons.sys, "platform", "win32"), \
             patch.object(icons.tk, "PhotoImage", side_effect=tk.TclError("PNG failed")), \
             self.assertLogs(icons.log, level="ERROR"):
            icons.set_window_icon(root)
        root.iconbitmap.assert_called_once()
        root.after.assert_called_once()
        self.assertTrue(any(call.args[0] == "<Map>" for call in root.bind.call_args_list))

    def test_png_uses_bytes_instead_of_tcl_path(self):
        root = Mock()
        with patch.object(icons.sys, "platform", "linux"), \
             patch.object(icons.tk, "PhotoImage") as photo:
            icons.set_window_icon(root)
        self.assertIn("data", photo.call_args.kwargs)
        self.assertNotIn("file", photo.call_args.kwargs)
        root.iconphoto.assert_called_once_with(True, photo.return_value)
