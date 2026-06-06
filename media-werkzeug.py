#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
#  Media‑Werkzeug – Multi‑Tool für Download, Konvertierung & Verwaltung
# ==============================================================================
#  Beschreibung : Ein leistungsstarkes GTK4/Libadwaita‑Tool für Video‑Download,
#                 Audio‑Extraktion & Medien‑Konvertierung
#
#  Version      : 1.2
#  Autoren      : evilware666 & Helga
#  Lizenz       : MIT
#  Plattform    : Linux (Debian/Ubuntu & Derivate)
#  GUI          : GTK4 + Libadwaita

import gi
import os
import sys
import threading
import subprocess
import time
import configparser
import re
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, Adw, GLib, Gdk, Notify, Pango, Gio

# ==============================================================================
# KONFIGURATION
# ==============================================================================

VIDEO_FORMATS = ['mp4', 'avi', 'mkv', 'mov', 'webm']
AUDIO_FORMATS = ['mp3', 'flac', 'wav', 'ogg', 'm4a']
IMAGE_FORMATS = ['jpg', 'png', 'webp', 'bmp']

# Bekannte Bildbearbeitungsprogramme (Name, Befehl, wie erkennen)
KNOWN_IMAGE_EDITORS = [
    {"name": "GIMP", "cmd": "gimp", "check": "gimp --version", "icon": "🎨"},
    {"name": "Pinta", "cmd": "pinta", "check": "pinta --version", "icon": "🖌️"},
    {"name": "Krita", "cmd": "krita", "check": "krita --version", "icon": "🎨"},
    {"name": "Inkscape", "cmd": "inkscape", "check": "inkscape --version", "icon": "✏️"},
    {"name": "KolourPaint", "cmd": "kolourpaint", "check": "kolourpaint --version", "icon": "🎨"},
    {"name": "MyPaint", "cmd": "mypaint", "check": "mypaint --version", "icon": "🖌️"},
    {"name": "LazPaint", "cmd": "lazpaint", "check": "lazpaint --version", "icon": "🎨"},
    {"name": "XnView MP", "cmd": "xnview", "check": "xnview --version", "icon": "🖼️"},
    {"name": "Shotwell", "cmd": "shotwell", "check": "shotwell --version", "icon": "📷"},
    {"name": "Darktable", "cmd": "darktable", "check": "darktable --version", "icon": "📸"},
    {"name": "RawTherapee", "cmd": "rawtherapee", "check": "rawtherapee --version", "icon": "🎨"},
]

class Settings:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = os.path.expanduser("~/.config/media-werkzeug.ini")
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)

    def get(self, section, key, default=None):
        try:
            return self.config.get(section, key)
        except:
            return default

    def set(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        with open(self.config_file, 'w') as f:
            self.config.write(f)

# ==============================================================================
# SYSTEMERKENNUNG
# ==============================================================================

def detect_system():
    info = {"distro": "other", "version": "", "codename": "", "pretty": "Unbekannt"}
    try:
        with open("/etc/os-release") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ID="):
                    val = line.split("=", 1)[1].strip('"').lower()
                    if "ubuntu" in val:
                        info["distro"] = "ubuntu"
                    elif "debian" in val:
                        info["distro"] = "debian"
                elif line.startswith("VERSION_ID="):
                    info["version"] = line.split("=", 1)[1].strip('"')
                elif line.startswith("VERSION_CODENAME="):
                    info["codename"] = line.split("=", 1)[1].strip('"').lower()
                elif line.startswith("PRETTY_NAME="):
                    info["pretty"] = line.split("=", 1)[1].strip('"')
    except Exception:
        pass
    return info


def backports_already_enabled(codename):
    sources_dirs = [
        "/etc/apt/sources.list",
        "/etc/apt/sources.list.d/"
    ]
    needle = f"{codename}-backports"
    for path in sources_dirs:
        if os.path.isfile(path):
            try:
                content = open(path).read()
                if needle in content:
                    return True
            except:
                pass
        elif os.path.isdir(path):
            for fname in os.listdir(path):
                fpath = os.path.join(path, fname)
                try:
                    content = open(fpath).read()
                    if needle in content:
                        return True
                except:
                    pass
    return False


# ==============================================================================
# HAUPTANWENDUNG
# ==============================================================================

class MediaMultiTool(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.media-werkzeug')
        Notify.init("Media-Werkzeug")
        self.settings = Settings()
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MediaMultiToolWindow(application=self, settings=self.settings)
        self.win.present()


class MediaMultiToolWindow(Adw.ApplicationWindow):
    def __init__(self, settings, **kwargs):
        super().__init__(**kwargs)
        self.settings = settings
        self.set_title("Media-Werkzeug")
        self.set_default_size(1000, 900)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(self.main_box)

        self.create_header_bar()
        self.create_sidebar_navigation()

        self._system = detect_system()
        GLib.idle_add(self._run_startup_checks)

    # ==========================================================================
    # STARTUP
    # ==========================================================================

    def _run_startup_checks(self):
        if self._system["distro"] == "debian":
            self._check_debian_backports()
        else:
            self.check_dependencies()
        return False

    def _check_debian_backports(self):
        codename = self._system.get("codename", "")
        if not codename:
            self.check_dependencies()
            return

        if backports_already_enabled(codename):
            self.check_dependencies()
            return

        pretty = self._system.get("pretty", "Debian")
        body = (
            f"Dieses Programm läuft auf <b>{pretty}</b>.\n\n"
            "Einige benötigte Programme (z. B. <b>yt-dlp</b> und eine aktuelle Version von "
            "<b>ffmpeg</b>) sind im normalen Debian‑Paketarchiv entweder veraltet oder gar "
            "nicht vorhanden.\n\n"
            "<b>Was sind Backports?</b>\n"
            "Debian ist bekannt für Stabilität – deshalb werden Pakete dort selten aktualisiert. "
            "Die sogenannten <i>Backports</i> sind ein offizielles Zusatz‑Archiv von Debian, "
            "das neuere Versionen wichtiger Programme bereitstellt, ohne die Systemstabilität "
            "zu gefährden.\n\n"
            f"Mit einem Klick auf <b>Backports aktivieren</b> wird das Archiv "
            f"<tt>{codename}-backports</tt> einmalig zu Ihrer Paketliste hinzugefügt. "
            "Das ist sicher und wird von Debian offiziell empfohlen.\n\n"
            "Wenn Sie <b>Überspringen</b> wählen, versucht das Programm trotzdem zu starten – "
            "manche Funktionen könnten jedoch nicht verfügbar sein."
        )

        dialog = Adw.AlertDialog.new("Debian erkannt – Backports empfohlen", None)
        lbl = Gtk.Label()
        lbl.set_markup(body)
        lbl.set_wrap(True)
        lbl.set_max_width_chars(60)
        lbl.set_xalign(0)
        lbl.set_margin_top(6)
        lbl.set_margin_bottom(6)
        dialog.set_extra_child(lbl)

        dialog.add_response("skip", "Überspringen")
        dialog.add_response("enable", "Backports aktivieren")
        dialog.set_response_appearance("enable", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("enable")
        dialog.connect("response", self._on_backports_response, codename)
        dialog.present(self)

    def _on_backports_response(self, dialog, response, codename):
        if response == "enable":
            self._enable_backports(codename)
        else:
            self.check_dependencies()

    def _enable_backports(self, codename):
        win = Gtk.Window(title="Backports werden aktiviert …")
        win.set_transient_for(self)
        win.set_modal(True)
        win.set_default_size(520, 340)
        win.set_resizable(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        win.set_child(outer)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        outer.append(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        outer.append(content)

        step_lbl = Gtk.Label(label="Vorbereitung …")
        step_lbl.set_xalign(0)
        step_lbl.set_wrap(True)
        content.append(step_lbl)

        pbar = Gtk.ProgressBar()
        pbar.set_show_text(True)
        pbar.set_text("Bitte warten …")
        content.append(pbar)

        log_view = Gtk.TextView()
        log_view.set_editable(False)
        log_view.set_monospace(True)
        log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        log_buf = log_view.get_buffer()

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_vexpand(True)
        log_scroll.set_child(log_view)
        content.append(log_scroll)

        close_btn = Gtk.Button(label="Weiter")
        close_btn.add_css_class("suggested-action")
        close_btn.set_sensitive(False)
        content.append(close_btn)

        win.present()

        pulse_active = [True]

        def pulse():
            if pulse_active[0]:
                pbar.pulse()
            return pulse_active[0]

        GLib.timeout_add(120, pulse)

        def log(text):
            end = log_buf.get_end_iter()
            log_buf.insert(end, text + "\n")
            end = log_buf.get_end_iter()
            mark = log_buf.create_mark(None, end, False)
            log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

        def finish(success):
            pulse_active[0] = False
            if success:
                pbar.set_fraction(1.0)
                pbar.set_text("Backports aktiviert!")
                step_lbl.set_text("✅ Fertig! Klicken Sie auf Weiter.")
            else:
                pbar.set_fraction(0.0)
                pbar.set_text("Fehler aufgetreten.")
                step_lbl.set_text("⚠️ Backports konnten nicht aktiviert werden.")
            close_btn.set_sensitive(True)

        def on_close(_btn):
            win.close()
            self.check_dependencies()

        close_btn.connect("clicked", on_close)

        def worker():
            line = (
                f"deb http://deb.debian.org/debian {codename}-backports main contrib non-free\n"
            )
            sources_file = f"/etc/apt/sources.list.d/{codename}-backports.list"
            script = (
                "#!/bin/bash\n"
                "set -e\n"
                f"echo '{line.strip()}' > {sources_file}\n"
                "apt-get update\n"
            )
            import tempfile
            with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False) as f:
                f.write(script)
                spath = f.name
            os.chmod(spath, 0o755)

            GLib.idle_add(step_lbl.set_text, "Schritt 1/2: Backports‑Eintrag hinzufügen …")
            GLib.idle_add(log, f"▶  pkexec bash {spath}")

            proc = subprocess.Popen(
                ['pkexec', 'bash', spath],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            for out_line in proc.stdout:
                s = out_line.rstrip()
                if not s:
                    continue
                GLib.idle_add(log, "  " + s)
                sl = s.lower()
                if 'get:' in sl or 'paketlisten' in sl or 'reading package' in sl:
                    GLib.idle_add(step_lbl.set_text, "Schritt 2/2: Paketlisten aktualisieren …")
                    GLib.idle_add(pbar.set_text, "apt update …")
            proc.wait()

            GLib.idle_add(finish, proc.returncode == 0)
            os.unlink(spath)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    # ==========================================================================
    # ABHÄNGIGKEITEN
    # ==========================================================================

    def check_dependencies(self, manual=False):
        import shutil
        missing = []
        if not shutil.which('yt-dlp'):
            missing.append('yt-dlp')
        if not shutil.which('ffmpeg'):
            missing.append('ffmpeg')

        if missing:
            GLib.idle_add(self._show_missing_deps_dialog, missing)
        elif manual:
            self.show_info("✅ Alle Abhängigkeiten sind vorhanden!")

    def _show_missing_deps_dialog(self, missing):
        pkg_list = ", ".join(f"<b>{p}</b>" for p in missing)
        body = (
            f"Folgende Programme werden von Media‑Werkzeug benötigt, "
            f"sind aber noch nicht installiert:\n\n"
            f"  {pkg_list}\n\n"
            "<b>Was machen diese Programme?</b>\n"
        )
        if "yt-dlp" in missing:
            body += (
                "• <b>yt-dlp</b> – lädt Videos und Musik von YouTube, Vimeo und "
                "hunderten anderen Webseiten herunter.\n"
            )
        if "ffmpeg" in missing:
            body += (
                "• <b>ffmpeg</b> – wandelt Medien‑Dateien um, z. B. Video in MP4 oder "
                "Musik in MP3. Es ist das Herzstück des Konverters.\n"
            )
        body += (
            "\nMit einem Klick auf <b>Jetzt installieren</b> werden diese Programme "
            "automatisch aus dem Internet geladen und eingerichtet. "
            "Sie werden einmalig nach Ihrem Administrator‑Passwort gefragt."
        )

        dialog = Adw.AlertDialog.new("Fehlende Programme", None)
        lbl = Gtk.Label()
        lbl.set_markup(body)
        lbl.set_wrap(True)
        lbl.set_max_width_chars(60)
        lbl.set_xalign(0)
        lbl.set_margin_top(6)
        lbl.set_margin_bottom(6)
        dialog.set_extra_child(lbl)

        dialog.add_response("cancel", "Abbrechen")
        dialog.add_response("install", "Jetzt installieren")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("install")
        dialog.connect("response", self._on_deps_dialog_response, missing)
        dialog.present(self)

    def _on_deps_dialog_response(self, dialog, response, missing):
        if response == "install":
            self._install_dependencies(missing)

    def _install_dependencies(self, missing):
        pkg_str = " ".join(missing)

        win = Gtk.Window(title="Installation läuft …")
        win.set_transient_for(self)
        win.set_modal(True)
        win.set_default_size(560, 380)
        win.set_resizable(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        win.set_child(outer)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        outer.append(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        outer.append(content)

        info_lbl = Gtk.Label(
            label=f"Installiere: {pkg_str}\nBitte Passwort im System‑Dialog eingeben."
        )
        info_lbl.set_xalign(0)
        info_lbl.set_wrap(True)
        content.append(info_lbl)

        pbar = Gtk.ProgressBar()
        pbar.set_show_text(True)
        pbar.set_text("Warte auf Passwort‑Eingabe …")
        content.append(pbar)

        log_view = Gtk.TextView()
        log_view.set_editable(False)
        log_view.set_monospace(True)
        log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        log_buf = log_view.get_buffer()

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_vexpand(True)
        log_scroll.set_child(log_view)
        content.append(log_scroll)

        close_btn = Gtk.Button(label="Schließen")
        close_btn.add_css_class("suggested-action")
        close_btn.set_sensitive(False)
        close_btn.connect("clicked", lambda _: win.close())
        content.append(close_btn)

        win.present()

        pulse_active = [True]

        def pulse():
            if pulse_active[0]:
                pbar.pulse()
            return pulse_active[0]

        GLib.timeout_add(120, pulse)

        def log(text):
            end = log_buf.get_end_iter()
            log_buf.insert(end, text + "\n")
            end = log_buf.get_end_iter()
            mark = log_buf.create_mark(None, end, False)
            log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

        def finish(success):
            pulse_active[0] = False
            if success:
                pbar.set_fraction(1.0)
                pbar.set_text("Installation erfolgreich!")
                GLib.idle_add(log, "\n=== Installation erfolgreich! ===")
            else:
                pbar.set_fraction(0.0)
                pbar.set_text("Installation fehlgeschlagen!")
                GLib.idle_add(log, "\n=== Installation fehlgeschlagen! ===")
                GLib.idle_add(log, "Bitte manuell im Terminal ausführen:")
                GLib.idle_add(log, f"  sudo apt install {pkg_str}")
            close_btn.set_sensitive(True)

        def worker():
            backport_flag = []
            if self._system["distro"] == "debian" and self._system.get("codename"):
                backport_flag = ["-t", f"{self._system['codename']}-backports"]

            script = (
                "#!/bin/bash\n"
                "set -e\n"
                "apt-get update\n"
                f"apt-get install -y {' '.join(backport_flag)} {pkg_str}\n"
            )
            import tempfile
            with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False) as f:
                f.write(script)
                spath = f.name
            os.chmod(spath, 0o755)

            GLib.idle_add(log, f"▶  Installiere: {pkg_str}")
            GLib.idle_add(pbar.set_text, "Installation läuft …")

            proc = subprocess.Popen(
                ['pkexec', 'bash', spath],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            for out_line in proc.stdout:
                s = out_line.rstrip()
                if s:
                    GLib.idle_add(log, "  " + s)
            proc.wait()

            GLib.idle_add(finish, proc.returncode == 0)
            os.unlink(spath)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    # ==========================================================================
    # BILDBEARBEITUNGSPROGRAMME ERKENNEN
    # ==========================================================================

    def get_installed_image_editors(self):
        """Erkennt alle installierten Bildbearbeitungsprogramme"""
        import shutil
        installed = []
        
        for editor in KNOWN_IMAGE_EDITORS:
            if shutil.which(editor["cmd"]):
                installed.append(editor)
        
        return installed

    def get_default_image_editor(self):
        """Ermittelt das gespeicherte oder Standard-Programm für Bilder"""
        saved = self.settings.get("image_editor", "default_editor", "")
        if saved:
            import shutil
            if shutil.which(saved):
                return saved
        return "xdg-open"

    def get_editor_display_name(self, cmd):
        """Holt den Anzeigenamen für einen Befehl"""
        for editor in KNOWN_IMAGE_EDITORS:
            if editor["cmd"] == cmd:
                return f"{editor['icon']} {editor['name']}"
        return f"📷 {cmd}"

    # ==========================================================================
    # HEADER + SIDEBAR
    # ==========================================================================

    def create_header_bar(self):
        header = Adw.HeaderBar()
        self.main_box.append(header)

        about_button = Gtk.Button(label="Über")
        about_button.connect('clicked', self.show_about)
        header.pack_end(about_button)

        deps_button = Gtk.Button(label="Abhängigkeiten prüfen")
        deps_button.connect('clicked', lambda x: self.check_dependencies(manual=True))
        header.pack_start(deps_button)

    def create_sidebar_navigation(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_box.append(paned)

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        sidebar_box.set_margin_top(20)
        sidebar_box.set_margin_bottom(20)
        sidebar_box.set_margin_start(15)
        sidebar_box.set_margin_end(15)
        sidebar_box.set_size_request(220, -1)

        title_label = Gtk.Label()
        title_label.set_markup("<b><big>      Werkzeug Auswahl</big></b>")
        title_label.set_xalign(0)
        sidebar_box.append(title_label)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(10)
        sep.set_margin_bottom(10)
        sidebar_box.append(sep)

        self.nav_downloader_btn = self.create_nav_button("🎬", "Video Downloader")
        self.nav_converter_btn  = self.create_nav_button("🔄", "Media Konverter")
        self.nav_settings_btn   = self.create_nav_button("⚙️",  "Einstellungen")

        sidebar_box.append(self.nav_downloader_btn)
        sidebar_box.append(self.nav_converter_btn)
        sidebar_box.append(self.nav_settings_btn)

        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        sidebar_box.append(spacer)

        exit_btn = Gtk.Button(label="Beenden")
        exit_btn.add_css_class("destructive-action")
        exit_btn.connect("clicked", lambda x: self.close())
        sidebar_box.append(exit_btn)

        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.content_stack.set_margin_top(10)
        self.content_stack.set_margin_bottom(10)
        self.content_stack.set_margin_start(10)
        self.content_stack.set_margin_end(10)

        self.content_stack.add_named(self.create_downloader_view(), "downloader")
        self.content_stack.add_named(self.create_converter_view(),  "converter")
        self.content_stack.add_named(self.create_settings_view(),   "settings")

        self.content_stack.set_visible_child_name("downloader")
        self.update_nav_buttons("downloader")

        self.nav_downloader_btn.connect("clicked", lambda x: self.switch_view("downloader"))
        self.nav_converter_btn.connect("clicked",  lambda x: self.switch_view("converter"))
        self.nav_settings_btn.connect("clicked",   lambda x: self.switch_view("settings"))

        paned.set_start_child(sidebar_box)
        paned.set_end_child(self.content_stack)
        paned.set_position(240)

    def create_nav_button(self, icon, title):
        button = Gtk.Button()
        button.add_css_class("flat")
        button.set_size_request(-1, 60)
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        content.set_margin_top(10)
        content.set_margin_bottom(10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        icon_label = Gtk.Label()
        icon_label.set_markup(f"<span size='x-large'>{icon}</span>")
        content.append(icon_label)
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{title}</b>")
        title_label.set_xalign(0)
        content.append(title_label)
        button.set_child(content)
        return button

    def switch_view(self, view_name):
        self.content_stack.set_visible_child_name(view_name)
        self.update_nav_buttons(view_name)

    def update_nav_buttons(self, active_view):
        buttons = [
            (self.nav_downloader_btn, "downloader"),
            (self.nav_converter_btn,  "converter"),
            (self.nav_settings_btn,   "settings"),
        ]
        for btn, view in buttons:
            if view == active_view:
                btn.add_css_class("suggested-action")
            else:
                btn.remove_css_class("suggested-action")

    # ==========================================================================
    # DOWNLOADER VIEW
    # ==========================================================================

    def create_downloader_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        downloader_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        downloader_box.set_margin_top(20)
        downloader_box.set_margin_bottom(20)
        downloader_box.set_margin_start(20)
        downloader_box.set_margin_end(20)

        header = Gtk.Label()
        header.set_markup("<big><b>🎬 Video Downloader</b></big>")
        header.set_halign(Gtk.Align.START)
        downloader_box.append(header)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(5)
        separator.set_margin_bottom(15)
        downloader_box.append(separator)

        url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        url_label = Gtk.Label(label="Video-URL:")
        url_label.set_width_chars(12)
        url_box.append(url_label)

        self.url_entry = Gtk.Entry()
        self.url_entry.set_hexpand(True)
        self.url_entry.set_placeholder_text("Hier Video oder Playlisten-Link einfügen.")
        url_box.append(self.url_entry)
        downloader_box.append(url_box)

        options_frame = Gtk.Frame(label="Download-Optionen")
        options_frame.set_margin_top(10)
        downloader_box.append(options_frame)

        options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        options_box.set_margin_top(12)
        options_box.set_margin_bottom(12)
        options_box.set_margin_start(12)
        options_box.set_margin_end(12)
        options_frame.set_child(options_box)

        tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tab_bar.add_css_class("linked")
        options_box.append(tab_bar)

        self.tab_video_btn = Gtk.ToggleButton(label="🎬  Video")
        self.tab_video_btn.set_hexpand(True)
        self.tab_video_btn.set_active(True)
        tab_bar.append(self.tab_video_btn)

        self.tab_audio_btn = Gtk.ToggleButton(label="🎵  Nur Audio")
        self.tab_audio_btn.set_hexpand(True)
        self.tab_audio_btn.set_group(self.tab_video_btn)
        tab_bar.append(self.tab_audio_btn)

        self.format_stack = Gtk.Stack()
        options_box.append(self.format_stack)

        video_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        video_quality_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vq_label = Gtk.Label(label="Qualität:")
        vq_label.set_width_chars(12)
        video_quality_box.append(vq_label)
        
        self.video_quality_combo = Gtk.DropDown()
        vq_model = Gtk.StringList()
        for q in ["Beste", "1080p", "720p", "480p", "360p"]:
            vq_model.append(q)
        self.video_quality_combo.set_model(vq_model)
        self.video_quality_combo.set_selected(0)
        self.video_quality_combo.set_hexpand(True)
        video_quality_box.append(self.video_quality_combo)
        video_page.append(video_quality_box)

        video_format_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vf_label = Gtk.Label(label="Format:")
        vf_label.set_width_chars(12)
        video_format_box.append(vf_label)
        
        self.video_format_combo = Gtk.DropDown()
        vf_model = Gtk.StringList()
        for fmt in ["Auto", "MP4", "MKV", "WEBM", "AVI"]:
            vf_model.append(fmt)
        self.video_format_combo.set_model(vf_model)
        self.video_format_combo.set_selected(0)
        self.video_format_combo.set_hexpand(True)
        video_format_box.append(self.video_format_combo)
        video_page.append(video_format_box)
        
        self.format_stack.add_named(video_page, "video")

        audio_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        audio_fmt_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        af_label = Gtk.Label(label="Format:")
        af_label.set_width_chars(12)
        audio_fmt_box.append(af_label)
        
        self.audio_format_combo = Gtk.DropDown()
        af_model = Gtk.StringList()
        for fmt in ["MP3", "M4A", "OGG", "OPUS", "FLAC", "WAV"]:
            af_model.append(fmt)
        self.audio_format_combo.set_model(af_model)
        self.audio_format_combo.set_selected(0)
        self.audio_format_combo.set_hexpand(True)
        audio_fmt_box.append(self.audio_format_combo)
        audio_page.append(audio_fmt_box)
        
        audio_quality_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        aq_label = Gtk.Label(label="Qualität:")
        aq_label.set_width_chars(12)
        audio_quality_box.append(aq_label)
        
        self.audio_quality_combo = Gtk.DropDown()
        aq_model = Gtk.StringList()
        for q in ["Beste (320k)", "Hoch (192k)", "Mittel (128k)", "Niedrig (96k)"]:
            aq_model.append(q)
        self.audio_quality_combo.set_model(aq_model)
        self.audio_quality_combo.set_selected(0)
        self.audio_quality_combo.set_hexpand(True)
        audio_quality_box.append(self.audio_quality_combo)
        audio_page.append(audio_quality_box)
        
        self.embed_thumbnail_check = Gtk.CheckButton(label="Thumbnail als Cover einbetten")
        self.embed_thumbnail_check.set_active(True)
        audio_page.append(self.embed_thumbnail_check)
        
        self.format_stack.add_named(audio_page, "audio")
        
        self.tab_video_btn.connect("toggled", self._on_tab_toggled)
        self.tab_audio_btn.connect("toggled", self._on_tab_toggled)
        self.tab_video_btn.add_css_class("suggested-action")
        
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        options_box.append(sep)
        
        save_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        save_label = Gtk.Label(label="Speicherort:")
        save_label.set_width_chars(12)
        save_box.append(save_label)

        self.save_entry = Gtk.Entry()
        self.save_entry.set_hexpand(True)
        default_path = self.settings.get("general", "default_save_path", str(Path.home() / "Downloads"))
        self.save_entry.set_text(default_path)
        save_box.append(self.save_entry)
        
        browse_button = Gtk.Button(label="Durchsuchen")
        browse_button.connect('clicked', self.choose_save_location)
        save_box.append(browse_button)
        options_box.append(save_box)
        
        self.download_button = Gtk.Button(label="Download starten")
        self.download_button.add_css_class("suggested-action")
        self.download_button.set_margin_top(6)
        self.download_button.connect('clicked', self.start_download)
        options_box.append(self.download_button)
        
        progress_frame = Gtk.Frame(label="Fortschritt")
        progress_frame.set_margin_top(10)
        downloader_box.append(progress_frame)
        
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        progress_box.set_margin_top(10)
        progress_box.set_margin_bottom(10)
        progress_box.set_margin_start(10)
        progress_box.set_margin_end(10)
        progress_frame.set_child(progress_box)
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        progress_box.append(self.progress_bar)
        
        self.status_label = Gtk.Label(label="Bereit")
        self.status_label.set_xalign(0)
        progress_box.append(self.status_label)
        
        log_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        log_header_box.set_margin_top(10)
        downloader_box.append(log_header_box)
        
        log_title = Gtk.Label(label="Log / Ausgabe")
        log_title.set_hexpand(True)
        log_title.set_xalign(0)
        log_title.add_css_class("heading")
        log_header_box.append(log_title)
        
        clear_log_button = Gtk.Button(label="🗑 Leeren")
        clear_log_button.add_css_class("flat")
        clear_log_button.connect("clicked", self.clear_log)
        log_header_box.append(clear_log_button)
        
        preview_frame = Gtk.Frame()
        preview_frame.set_vexpand(True)
        downloader_box.append(preview_frame)
        
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        preview_frame.set_child(preview_box)
        
        self.preview_text = Gtk.TextView()
        self.preview_text.set_editable(False)
        self.preview_text.set_monospace(True)
        self.preview_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        
        preview_scroll = Gtk.ScrolledWindow()
        preview_scroll.set_vexpand(True)
        preview_scroll.set_child(self.preview_text)
        preview_box.append(preview_scroll)
        
        self.preview_buffer = self.preview_text.get_buffer()
        
        scrolled.set_child(downloader_box)
        return scrolled

    def _on_tab_toggled(self, btn):
        if self.tab_video_btn.get_active():
            self.format_stack.set_visible_child_name("video")
            self.tab_video_btn.add_css_class("suggested-action")
            self.tab_audio_btn.remove_css_class("suggested-action")
        else:
            self.format_stack.set_visible_child_name("audio")
            self.tab_audio_btn.add_css_class("suggested-action")
            self.tab_video_btn.remove_css_class("suggested-action")

    def choose_save_location(self, widget):
        dialog = Gtk.FileDialog()
        dialog.set_title("Speicherort auswählen")
        dialog.select_folder(self, None, self.on_folder_selected)

    def on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.save_entry.set_text(folder.get_path())
        except:
            pass

    def start_download(self, widget):
        url = self.url_entry.get_text().strip()
        if not url:
            self.show_error("Bitte geben Sie eine URL ein.")
            return
        
        save_path = self.save_entry.get_text().strip()
        if not os.path.exists(save_path):
            try:
                os.makedirs(save_path)
            except:
                self.show_error("Speicherort konnte nicht erstellt werden.")
                return
        
        self.download_button.set_sensitive(False)
        self.status_label.set_text("Download läuft...")
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_text("0%")
        
        thread = threading.Thread(target=self.run_download, args=(url, save_path), daemon=True)
        thread.start()

    def run_download(self, url, save_path):
        cmd = ['yt-dlp', '--newline', '--progress', '--no-playlist']
        GLib.idle_add(self.append_log, "📹 Modus: Einzelnes Video")
        
        if self.tab_audio_btn.get_active():
            fmt_idx = self.audio_format_combo.get_selected()
            fmt_map = ['mp3', 'm4a', 'vorbis', 'opus', 'flac', 'wav']
            fmt = fmt_map[fmt_idx]
            cmd.extend(['-x', '--audio-format', fmt])
            q_idx = self.audio_quality_combo.get_selected()
            q_map = ['0', '2', '5', '7']
            cmd.extend(['--audio-quality', q_map[q_idx]])
            if self.embed_thumbnail_check.get_active():
                cmd.append('--embed-thumbnail')
        else:
            vq_idx = self.video_quality_combo.get_selected()
            heights = [None, 1080, 720, 480, 360]
            h = heights[vq_idx]
            if h:
                quality = f'bestvideo[height<={h}]+bestaudio/best[height<={h}]'
            else:
                quality = 'bestvideo+bestaudio/best'
            cmd.extend(['-f', quality])
        
        output_template = os.path.join(save_path, '%(title)s.%(ext)s')
        cmd.extend(['-o', output_template, url])
        
        GLib.idle_add(self.append_log, "▶ " + " ".join(cmd))
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, bufsize=1, universal_newlines=True)
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                GLib.idle_add(self.append_log, line)
                if '%' in line:
                    try:
                        pct_match = re.search(r'(\d+\.?\d*)%', line)
                        if pct_match:
                            pct = float(pct_match.group(1)) / 100
                            GLib.idle_add(self.progress_bar.set_fraction, pct)
                            GLib.idle_add(self.progress_bar.set_text, f"{pct_match.group(1)}%")
                            GLib.idle_add(self.status_label.set_text, f"📥 Download: {pct_match.group(1)}%")
                    except:
                        pass
                if '[download] 100%' in line:
                    GLib.idle_add(self.append_log, "✅ Download abgeschlossen")
            process.wait()
            
            if process.returncode == 0:
                GLib.idle_add(self.download_finished)
            else:
                GLib.idle_add(self.show_error, "Download fehlgeschlagen")
        except Exception as e:
            GLib.idle_add(self.show_error, str(e))

    def append_log(self, text):
        if self.preview_buffer:
            end_iter = self.preview_buffer.get_end_iter()
            self.preview_buffer.insert(end_iter, text + "\n")
            self.preview_text.scroll_to_iter(end_iter, 0.0, False, 0, 0)

    def clear_log(self, widget):
        if self.preview_buffer:
            self.preview_buffer.set_text("")

    def download_finished(self):
        self.status_label.set_text("✅ Fertig!")
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Fertig!")
        self.download_button.set_sensitive(True)
        self.show_info("Download abgeschlossen!")

    # ==========================================================================
    # CONVERTER VIEW (mit vereinfachter Bildbearbeitungsauswahl)
    # ==========================================================================

    def create_converter_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        converter_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        converter_box.set_margin_top(20)
        converter_box.set_margin_bottom(20)
        converter_box.set_margin_start(20)
        converter_box.set_margin_end(20)

        header = Gtk.Label()
        header.set_markup("<big><b>🔄 Media Konverter</b></big>")
        header.set_halign(Gtk.Align.START)
        converter_box.append(header)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(5)
        separator.set_margin_bottom(15)
        converter_box.append(separator)

        type_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        type_bar.add_css_class("linked")
        converter_box.append(type_bar)

        self.conv_video_btn = Gtk.ToggleButton(label="🎬 Video")
        self.conv_video_btn.set_hexpand(True)
        self.conv_video_btn.set_active(True)
        type_bar.append(self.conv_video_btn)

        self.conv_audio_btn = Gtk.ToggleButton(label="🎵 Audio")
        self.conv_audio_btn.set_hexpand(True)
        self.conv_audio_btn.set_group(self.conv_video_btn)
        type_bar.append(self.conv_audio_btn)

        self.conv_image_btn = Gtk.ToggleButton(label="🖼️ Bild")
        self.conv_image_btn.set_hexpand(True)
        self.conv_image_btn.set_group(self.conv_video_btn)
        type_bar.append(self.conv_image_btn)

        drag_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        drag_box.set_size_request(-1, 80)
        drag_box.add_css_class("card")
        drag_box.set_halign(Gtk.Align.FILL)
        drag_box.set_margin_top(10)

        drag_center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        drag_center_box.set_halign(Gtk.Align.CENTER)
        drag_center_box.set_valign(Gtk.Align.CENTER)
        drag_center_box.set_hexpand(True)
        drag_center_box.set_vexpand(True)

        drag_label = Gtk.Label()
        drag_label.set_markup("<span foreground='gray' size='large'>📁 Dateien hierher ziehen</span>")
        drag_center_box.append(drag_label)
        drag_box.append(drag_center_box)

        drop_target = Gtk.DropTarget.new(type=Gdk.FileList, actions=Gdk.DragAction.COPY)
        drop_target.connect("drop", self.on_drag_drop)
        drag_box.add_controller(drop_target)

        converter_box.append(drag_box)

        self.batch_info_label = Gtk.Label()
        self.batch_info_label.set_visible(False)
        self.batch_info_label.add_css_class("dim-label")
        converter_box.append(self.batch_info_label)

        file_selector_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        file_label = Gtk.Label(label="Datei(en):")
        file_label.set_width_chars(12)
        file_selector_box.append(file_label)

        self.converter_file_entry = Gtk.Entry()
        self.converter_file_entry.set_hexpand(True)
        self.converter_file_entry.set_placeholder_text("Dateien hierher ziehen oder auswählen...")
        self.converter_file_entry.set_editable(False)
        file_selector_box.append(self.converter_file_entry)

        self.select_files_btn = Gtk.Button(label="Durchsuchen")
        self.select_files_btn.connect("clicked", self.select_converter_files)
        file_selector_box.append(self.select_files_btn)

        converter_box.append(file_selector_box)

        self.info_label = Gtk.Label()
        self.info_label.set_visible(False)
        self.info_label.add_css_class("dim-label")
        converter_box.append(self.info_label)

        # ======================================================================
        # BEREICH FÜR BILDBEARBEITUNG (Nur Combobox, kein zusätzlicher Button)
        # ======================================================================
        
        self.image_edit_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.image_edit_box.set_margin_top(10)
        self.image_edit_box.set_visible(False)
        converter_box.append(self.image_edit_box)
        
        # Info-Karte
        edit_info = Gtk.Frame()
        edit_info.set_margin_top(5)
        edit_info.set_label_align(0.5)
        edit_info.set_label("📷 Bildbearbeitung")
        self.image_edit_box.append(edit_info)
        
        edit_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        edit_info_box.set_margin_top(10)
        edit_info_box.set_margin_bottom(10)
        edit_info_box.set_margin_start(10)
        edit_info_box.set_margin_end(10)
        edit_info.set_child(edit_info_box)
        
        edit_icon = Gtk.Label()
        edit_icon.set_markup("<span size='x-large'>🖌️</span>")
        edit_icon.set_halign(Gtk.Align.CENTER)
        edit_info_box.append(edit_icon)
        
        edit_label = Gtk.Label()
        edit_label.set_markup("<b>Bildbearbeitung mit externem Programm</b>")
        edit_label.set_halign(Gtk.Align.CENTER)
        edit_info_box.append(edit_label)
        
        edit_desc = Gtk.Label()
        edit_desc.set_markup(
            "Sie können das ausgewählte Bild mit Ihrem bevorzugten Programm bearbeiten.\n"
            ""
        )
        edit_desc.set_wrap(True)
        edit_desc.set_xalign(0.5)
        edit_desc.set_justify(Gtk.Justification.CENTER)
        edit_info_box.append(edit_desc)
        
        # Nur die Combobox zur Auswahl (kein zusätzlicher Button)
        program_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        program_row.set_margin_top(5)
        program_row.set_margin_bottom(5)
        program_row.set_halign(Gtk.Align.CENTER)
        
        program_label = Gtk.Label(label="Programm:")
        program_row.append(program_label)
        
        self.editor_combo = Gtk.DropDown()
        self.editor_combo.connect("notify::selected", self.on_editor_changed)
        program_row.append(self.editor_combo)
        
        edit_info_box.append(program_row)
        
        # Button zum Bearbeiten
        self.edit_button = Gtk.Button(label="✏️ Bild bearbeiten")
        self.edit_button.add_css_class("suggested-action")
        self.edit_button.set_size_request(200, 40)
        self.edit_button.set_halign(Gtk.Align.CENTER)
        self.edit_button.connect("clicked", self.edit_current_image)
        edit_info_box.append(self.edit_button)
        
        # Hinweis zum aktuellen Programm
        self.app_note = Gtk.Label()
        self.app_note.set_halign(Gtk.Align.CENTER)
        edit_info_box.append(self.app_note)
        
        # Programmauswahl-Combobox initialisieren
        self.update_editor_combo()

        format_frame = Gtk.Frame(label="Format-Optionen")
        format_frame.set_margin_top(10)
        converter_box.append(format_frame)

        format_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        format_box.set_margin_top(12)
        format_box.set_margin_bottom(12)
        format_box.set_margin_start(12)
        format_box.set_margin_end(12)
        format_frame.set_child(format_box)

        format_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        format_label = Gtk.Label(label="Zielformat:")
        format_label.set_width_chars(12)
        format_row.append(format_label)

        self.converter_format_combo = Gtk.DropDown()
        format_row.append(self.converter_format_combo)
        format_box.append(format_row)

        quality_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.quality_label = Gtk.Label(label="Qualität / Auflösung:")
        self.quality_label.set_width_chars(12)
        quality_row.append(self.quality_label)

        self.quality_combo = Gtk.DropDown()
        quality_row.append(self.quality_combo)
        format_box.append(quality_row)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_homogeneous(True)
        button_box.set_margin_top(6)

        self.convert_btn = Gtk.Button(label="Konvertieren")
        self.convert_btn.add_css_class("suggested-action")
        self.convert_btn.set_sensitive(False)
        self.convert_btn.connect('clicked', self.start_conversion)

        self.cancel_btn = Gtk.Button(label="Abbrechen")
        self.cancel_btn.add_css_class("destructive-action")
        self.cancel_btn.set_sensitive(False)
        self.cancel_btn.connect('clicked', self.cancel_conversion)

        button_box.append(self.convert_btn)
        button_box.append(self.cancel_btn)
        converter_box.append(button_box)

        progress_frame = Gtk.Frame(label="Fortschritt")
        progress_frame.set_margin_top(10)
        converter_box.append(progress_frame)

        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        progress_box.set_margin_top(10)
        progress_box.set_margin_bottom(10)
        progress_box.set_margin_start(10)
        progress_box.set_margin_end(10)
        progress_frame.set_child(progress_box)

        self.converter_progress_bar = Gtk.ProgressBar()
        self.converter_progress_bar.set_show_text(True)
        self.converter_progress_bar.set_visible(False)
        progress_box.append(self.converter_progress_bar)

        self.converter_percent_label = Gtk.Label()
        self.converter_percent_label.set_visible(False)
        self.converter_percent_label.add_css_class("dim-label")
        progress_box.append(self.converter_percent_label)

        self.converter_status_label = Gtk.Label(label="Bereit")
        self.converter_status_label.set_xalign(0)
        progress_box.append(self.converter_status_label)

        log_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        log_header_box.set_margin_top(10)
        converter_box.append(log_header_box)

        log_title = Gtk.Label(label="Konverter-Log")
        log_title.set_hexpand(True)
        log_title.set_xalign(0)
        log_title.add_css_class("heading")
        log_header_box.append(log_title)

        clear_conv_log_btn = Gtk.Button(label="🗑 Leeren")
        clear_conv_log_btn.add_css_class("flat")
        clear_conv_log_btn.connect("clicked", self.clear_converter_log)
        log_header_box.append(clear_conv_log_btn)

        log_frame = Gtk.Frame()
        log_frame.set_vexpand(True)
        log_frame.set_size_request(-1, 200)
        converter_box.append(log_frame)

        log_scroll_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        log_frame.set_child(log_scroll_box)

        self.converter_log_text = Gtk.TextView()
        self.converter_log_text.set_editable(False)
        self.converter_log_text.set_monospace(True)
        self.converter_log_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_vexpand(True)
        log_scroll.set_child(self.converter_log_text)
        log_scroll_box.append(log_scroll)

        self.converter_log_buffer = self.converter_log_text.get_buffer()

        self.current_converter_type = "video"
        self.converter_input_files  = []
        self.current_process        = None
        self.stop_conversion        = False
        self.total_duration         = 0
        self.current_time           = 0.0
        self.current_file_index     = 0
        self.progress_update_timer  = None

        self.update_converter_options("video")

        self.conv_video_btn.connect("toggled", lambda x: self.update_converter_options("video") if x.get_active() else None)
        self.conv_audio_btn.connect("toggled", lambda x: self.update_converter_options("audio") if x.get_active() else None)
        self.conv_image_btn.connect("toggled", lambda x: self.update_converter_options("image") if x.get_active() else None)

        ctrl = Gtk.EventControllerKey.new()
        ctrl.connect("key-pressed", self.on_converter_key_pressed)
        self.add_controller(ctrl)

        scrolled.set_child(converter_box)
        return scrolled

    def on_editor_changed(self, combo, *args):
        """Wird aufgerufen, wenn in der Combobox ein neues Programm ausgewählt wird"""
        self.update_editor_note()

    def update_editor_combo(self):
        """Aktualisiert die Combobox mit den installierten Bildbearbeitungsprogrammen"""
        installed = self.get_installed_image_editors()
        string_list = Gtk.StringList()
        
        self.editor_commands = []  # Liste der Befehle für die Auswahl
        
        for editor in installed:
            display = f"{editor['icon']} {editor['name']}"
            string_list.append(display)
            self.editor_commands.append(editor["cmd"])
        
        self.editor_combo.set_model(string_list)
        
        # Aktuelle Standardauswahl setzen
        current = self.get_default_image_editor()
        for i, cmd in enumerate(self.editor_commands):
            if cmd == current:
                self.editor_combo.set_selected(i)
                break
        
        # Hinweistext aktualisieren
        self.update_editor_note()

    def update_editor_note(self):
        """Aktualisiert den Hinweistext für das aktuell ausgewählte Programm"""
        selected_idx = self.editor_combo.get_selected()
        if selected_idx >= 0 and selected_idx < len(self.editor_commands):
            selected_cmd = self.editor_commands[selected_idx]
            display = self.get_editor_display_name(selected_cmd)
            self.app_note.set_markup(f"<small><i>Aktuell ausgewählt: {display}</i></small>")
            # Speichern in Einstellungen
            self.settings.set("image_editor", "default_editor", selected_cmd)
        else:
            self.app_note.set_markup("<small><i>Kein Programm ausgewählt</i></small>")

    def get_current_editor_command(self):
        """Gibt den Befehl des aktuell ausgewählten Bildbearbeitungsprogramms zurück"""
        selected_idx = self.editor_combo.get_selected()
        if selected_idx >= 0 and selected_idx < len(self.editor_commands):
            return self.editor_commands[selected_idx]
        return "xdg-open"

    def edit_current_image(self, button):
        """Öffnet das aktuell ausgewählte Bild mit dem ausgewählten Programm"""
        if not self.converter_input_files:
            self.show_error("Keine Datei ausgewählt.")
            return
        
        current_file = self.converter_input_files[self.current_file_index] if self.current_file_index < len(self.converter_input_files) else self.converter_input_files[0]
        
        if not os.path.exists(current_file):
            self.show_error("Datei nicht gefunden.")
            return
        
        editor_cmd = self.get_current_editor_command()
        
        try:
            subprocess.Popen([editor_cmd, current_file])
            editor_name = self.get_editor_display_name(editor_cmd)
            self.append_converter_log(f"✏️ Bild geöffnet mit {editor_name}: {os.path.basename(current_file)}")
        except Exception as e:
            self.show_error(f"Konnte Bild nicht öffnen: {str(e)}\n\nVersuche mit xdg-open...")
            try:
                subprocess.Popen(['xdg-open', current_file])
                self.append_converter_log(f"✏️ Bild geöffnet mit Standardprogramm: {os.path.basename(current_file)}")
            except:
                self.show_error("Konnte Bild mit keinem Programm öffnen.")

    def update_converter_options(self, conv_type):
        self.current_converter_type = conv_type
        self.converter_file_entry.set_text("")
        self.batch_info_label.set_visible(False)
        self.convert_btn.set_sensitive(False)
        self.info_label.set_visible(False)
        
        if conv_type == "image":
            self.image_edit_box.set_visible(True)
        else:
            self.image_edit_box.set_visible(False)

        if conv_type == "video":
            model = Gtk.StringList()
            for fmt in VIDEO_FORMATS:
                model.append(fmt.upper())
            self.converter_format_combo.set_model(model)
            quality_model = Gtk.StringList()
            for q in ["Original", "1080p", "720p", "480p", "360p"]:
                quality_model.append(q)
            self.quality_combo.set_model(quality_model)
            self.quality_label.set_text("Auflösung:")
            self.quality_label.set_visible(True)
            self.quality_combo.set_visible(True)

        elif conv_type == "audio":
            model = Gtk.StringList()
            for fmt in AUDIO_FORMATS:
                model.append(fmt.upper())
            self.converter_format_combo.set_model(model)
            self.update_audio_quality_visibility()
            if hasattr(self, '_format_changed_handler'):
                self.converter_format_combo.disconnect(self._format_changed_handler)
            self._format_changed_handler = self.converter_format_combo.connect("notify::selected", self.on_audio_format_changed)

        else:  # image
            model = Gtk.StringList()
            for fmt in IMAGE_FORMATS:
                model.append(fmt.upper())
            self.converter_format_combo.set_model(model)
            quality_model = Gtk.StringList()
            for q in ["Hohe (90%)", "Mittlere (75%)", "Niedrige (50%)"]:
                quality_model.append(q)
            self.quality_combo.set_model(quality_model)
            self.quality_label.set_text("Qualität:")
            self.quality_label.set_visible(True)
            self.quality_combo.set_visible(True)

    def on_audio_format_changed(self, combo, *args):
        self.update_audio_quality_visibility()

    def update_audio_quality_visibility(self):
        fmt_idx = self.converter_format_combo.get_selected()
        if fmt_idx < len(AUDIO_FORMATS):
            selected_format = AUDIO_FORMATS[fmt_idx].lower()
            lossless = ['flac', 'wav']
            if selected_format in lossless:
                self.quality_label.set_visible(False)
                self.quality_combo.set_visible(False)
                self.append_converter_log(f"ℹ️ {selected_format.upper()} ist ein verlustfreies Format")
            else:
                self.quality_label.set_visible(True)
                self.quality_combo.set_visible(True)
                quality_model = Gtk.StringList()
                if selected_format == 'mp3':
                    for q in ["320k", "256k", "192k", "128k"]:
                        quality_model.append(q)
                elif selected_format == 'ogg':
                    for q in ["320k", "192k", "128k", "96k"]:
                        quality_model.append(q)
                else:
                    for q in ["320k", "256k", "192k", "128k"]:
                        quality_model.append(q)
                self.quality_combo.set_model(quality_model)
                self.quality_combo.set_selected(0)

    def get_media_duration(self, file_path):
        try:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return float(result.stdout.strip())
        except:
            return 0

    def on_drag_drop(self, drop_target, value, x, y):
        files = value.get_files()
        if files:
            self.converter_input_files = []
            for file in files:
                path = file.get_path()
                if path:
                    self.converter_input_files.append(path)
            self.update_converter_file_display()
            self.convert_btn.set_sensitive(len(self.converter_input_files) > 0)
            if self.converter_input_files:
                self.update_file_info(self.converter_input_files[0])
            self.append_converter_log(f"📁 {len(self.converter_input_files)} Datei(en) hinzugefügt")
        return True

    def update_file_info(self, file_path):
        try:
            size = os.path.getsize(file_path)
            if size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            duration = self.get_media_duration(file_path)
            if duration > 0:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                icon = "🎬" if self.current_converter_type == "video" else "🎵" if self.current_converter_type == "audio" else "🖼️"
                self.info_label.set_text(f"{icon} {size_str}  ⏱️ {minutes}:{seconds:02d} min")
            else:
                self.info_label.set_text(f"📁 {size_str}")
            self.info_label.set_visible(True)
        except:
            self.info_label.set_visible(False)

    def select_converter_files(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Datei(en) auswählen")
        dialog.set_modal(True)
        dialog.open_multiple(self, None, self.on_converter_files_selected)

    def on_converter_files_selected(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
            if files:
                self.converter_input_files = []
                for file in files:
                    path = file.get_path()
                    if path:
                        self.converter_input_files.append(path)
                self.update_converter_file_display()
                self.convert_btn.set_sensitive(len(self.converter_input_files) > 0)
                if self.converter_input_files:
                    self.update_file_info(self.converter_input_files[0])
                self.append_converter_log(f"📁 {len(self.converter_input_files)} Datei(en) ausgewählt")
        except:
            pass

    def update_converter_file_display(self):
        if not self.converter_input_files:
            self.converter_file_entry.set_text("")
            self.batch_info_label.set_visible(False)
            return
        if len(self.converter_input_files) == 1:
            short_name = os.path.basename(self.converter_input_files[0])
            if len(short_name) > 50:
                short_name = short_name[:47] + "..."
            self.converter_file_entry.set_text(short_name)
            self.batch_info_label.set_visible(False)
        else:
            self.converter_file_entry.set_text(f"{len(self.converter_input_files)} Dateien ausgewählt")
            self.batch_info_label.set_text(f"📦 Batch: {len(self.converter_input_files)} Dateien")
            self.batch_info_label.set_visible(True)

    def append_converter_log(self, text):
        if self.converter_log_buffer:
            end_iter = self.converter_log_buffer.get_end_iter()
            self.converter_log_buffer.insert(end_iter, text + "\n")

    def clear_converter_log(self, widget):
        if self.converter_log_buffer:
            self.converter_log_buffer.set_text("")

    def on_converter_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape and self.conversion_in_progress():
            self.cancel_conversion(None)
            return True
        return False

    def conversion_in_progress(self):
        return (not self.convert_btn.get_sensitive() and self.cancel_btn.get_sensitive())

    def cancel_conversion(self, button):
        self.stop_conversion = True
        if self.current_process:
            self.current_process.terminate()
        self.converter_status_label.set_text("⏹️ Konvertierung wird abgebrochen...")
        self.cancel_btn.set_sensitive(False)
        self.append_converter_log("⚠️ Konvertierung wurde abgebrochen!")

    def start_conversion(self, button):
        if not self.converter_input_files:
            return
        self.stop_conversion = False
        self.current_file_index = 0
        self.start_next_conversion()

    def start_next_conversion(self):
        if self.current_file_index >= len(self.converter_input_files):
            self.conversion_finished()
            return

        input_file = self.converter_input_files[self.current_file_index]
        self.converter_status_label.set_text(f"📄 Datei {self.current_file_index + 1} von {len(self.converter_input_files)}: {os.path.basename(input_file)}")

        fmt_idx = self.converter_format_combo.get_selected()
        if self.current_converter_type == "video":
            formats = VIDEO_FORMATS
        elif self.current_converter_type == "audio":
            formats = AUDIO_FORMATS
        else:
            formats = IMAGE_FORMATS
        output_format = formats[fmt_idx]

        base_name = Path(input_file).stem
        keep_original = self.settings.get("converter", "keep_original", "true") == "true"
        default_save_path = self.settings.get("general", "default_save_path", str(Path.home() / "Downloads"))

        if keep_original:
            default_filename = f"{base_name}_converted.{output_format}"
        else:
            default_filename = f"{base_name}.{output_format}"

        default_full_path = os.path.join(default_save_path, default_filename)
        self.current_input_file = input_file
        self.keep_original = keep_original

        self.save_file_dialog(default_full_path, self.start_conversion_thread)

    def save_file_dialog(self, default_full_path, callback):
        dialog = Gtk.FileDialog()
        dialog.set_title("Speichern unter")
        dialog.set_initial_name(os.path.basename(default_full_path))
        default_dir = os.path.dirname(default_full_path)
        if os.path.exists(default_dir):
            dialog.set_initial_folder(Gio.File.new_for_path(default_dir))
        dialog.save(self, None, lambda d, r: self._on_save_response(d, r, callback))

    def _on_save_response(self, dialog, result, callback):
        try:
            file = dialog.save_finish(result)
            if file:
                callback(file.get_path())
            else:
                self.current_file_index += 1
                GLib.idle_add(self.start_next_conversion)
        except Exception:
            self.current_file_index += 1
            GLib.idle_add(self.start_next_conversion)

    def start_conversion_thread(self, output_file):
        self.convert_btn.set_sensitive(False)
        self.cancel_btn.set_sensitive(True)
        self.select_files_btn.set_sensitive(False)
        self.converter_progress_bar.set_visible(True)
        self.converter_percent_label.set_visible(True)
        self.converter_progress_bar.set_fraction(0)
        self.converter_percent_label.set_text("0%")
        self.converter_status_label.set_text("Konvertiere...")

        input_file = self.current_input_file
        self.total_duration = self.get_media_duration(input_file)
        if self.current_converter_type == "video":
            self.append_converter_log(f"🎬 Video-Dauer: {self.total_duration:.1f} Sekunden")
        else:
            self.append_converter_log(f"🎵 Audio-Dauer: {self.total_duration:.1f} Sekunden")
        self.current_time = 0.0
        self.current_output_file = output_file

        self.conversion_thread = threading.Thread(target=self.convert_file_thread, args=(input_file, output_file))
        self.conversion_thread.daemon = True
        self.conversion_thread.start()

        if self.total_duration > 0:
            self.start_progress_timer()

    def start_progress_timer(self):
        def update_timer():
            if self.current_process and self.current_process.poll() is None:
                if self.total_duration > 0:
                    progress = min(self.current_time / self.total_duration, 0.99)
                    percent = int(progress * 100)
                    GLib.idle_add(self.update_progress, progress, f"🔄 Konvertiere... {percent}%")
                    GLib.idle_add(self.converter_percent_label.set_text, f"{percent}%")
                GLib.timeout_add(500, update_timer)
            else:
                self.progress_update_timer = None
            return False
        GLib.timeout_add(500, update_timer)

    def parse_ffmpeg_progress(self, line):
        if 'out_time=' in line:
            try:
                time_str = line.split('=')[1].strip()
                if time_str != 'N/A':
                    if ':' in time_str:
                        parts = time_str.split(':')
                        if len(parts) == 3:
                            self.current_time = (float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2]))
                            return True
                    else:
                        self.current_time = float(time_str)
                        return True
            except:
                pass
        return False

    def convert_file_thread(self, input_file, output_file):
        try:
            cmd = self.get_conversion_command(input_file, output_file)

            self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                    text=True, bufsize=1, universal_newlines=True)
            self.current_time = 0.0

            for line in self.current_process.stderr:
                if self.stop_conversion:
                    self.current_process.terminate()
                    break
                self.parse_ffmpeg_progress(line)

            self.current_process.wait()
            return_code = self.current_process.returncode

            if not self.stop_conversion and return_code == 0:
                GLib.idle_add(self.update_progress, 1.0, "✅ Fertig!")
                GLib.idle_add(self.converter_percent_label.set_text, "100%")

                if not self.keep_original:
                    try:
                        os.remove(input_file)
                        GLib.idle_add(self.append_converter_log, f"🗑️ Originaldatei gelöscht: {os.path.basename(input_file)}")
                    except Exception as e:
                        GLib.idle_add(self.append_converter_log, f"⚠️ Konnte Originaldatei nicht löschen: {e}")

                time.sleep(0.5)
                self.current_file_index += 1
                GLib.idle_add(self.start_next_conversion)

            elif not self.stop_conversion:
                GLib.idle_add(self.show_error, f"❌ Konvertierung fehlgeschlagen: {os.path.basename(input_file)}")
                GLib.idle_add(self.reset_converter_ui)
            else:
                GLib.idle_add(self.reset_converter_ui)

        except Exception as e:
            if not self.stop_conversion:
                GLib.idle_add(self.show_error, f"❌ Fehler: {str(e)}")
                GLib.idle_add(self.reset_converter_ui)

    def get_conversion_command(self, input_file, output_file):
        quality_idx = self.quality_combo.get_selected() if self.quality_combo.get_visible() else 0

        if self.current_converter_type == "video":
            resolutions = ["", "1920x1080", "1280x720", "854x480", "640x360"]
            resolution = resolutions[quality_idx] if quality_idx < len(resolutions) else ""
            cmd = ['ffmpeg', '-i', input_file, '-y']
            if resolution:
                height = resolution.split("x")[1]
                cmd.extend(['-vf', f'scale=-2:{height}'])
            cmd.extend(['-progress', 'pipe:2', output_file])
            return cmd

        elif self.current_converter_type == "audio":
            fmt_idx = self.converter_format_combo.get_selected()
            selected_format = AUDIO_FORMATS[fmt_idx].lower()
            base_cmd = ['ffmpeg', '-i', input_file, '-y', '-progress', 'pipe:2']
            if selected_format == 'mp3':
                bitrates = ['320k', '256k', '192k', '128k']
                bitrate = bitrates[quality_idx] if quality_idx < len(bitrates) else '192k'
                base_cmd.extend(['-c:a', 'libmp3lame', '-b:a', bitrate, output_file])
            elif selected_format == 'flac':
                base_cmd.extend(['-c:a', 'flac', '-compression_level', '8', output_file])
            elif selected_format == 'wav':
                base_cmd.extend(['-c:a', 'pcm_s16le', output_file])
            elif selected_format == 'ogg':
                bitrates = ['320k', '192k', '128k', '96k']
                bitrate = bitrates[quality_idx] if quality_idx < len(bitrates) else '192k'
                base_cmd.extend(['-c:a', 'libvorbis', '-b:a', bitrate, output_file])
            else:
                bitrates = ['320k', '256k', '192k', '128k']
                bitrate = bitrates[quality_idx] if quality_idx < len(bitrates) else '192k'
                base_cmd.extend(['-c:a', 'aac', '-b:a', bitrate, output_file])
            return base_cmd

        else:  # image
            qualities = ['90', '75', '50']
            quality = qualities[quality_idx] if quality_idx < len(qualities) else '90'
            return ['ffmpeg', '-i', input_file, '-y', '-q:v', quality, output_file]

    def update_progress(self, value, status_text=""):
        self.converter_progress_bar.set_fraction(value)
        self.converter_progress_bar.set_text(f"{int(value*100)}%")
        if status_text:
            self.converter_status_label.set_text(status_text)

    def reset_converter_ui(self):
        self.convert_btn.set_sensitive(True)
        self.cancel_btn.set_sensitive(False)
        self.select_files_btn.set_sensitive(True)
        self.converter_progress_bar.set_visible(False)
        self.converter_percent_label.set_visible(False)
        self.converter_status_label.set_text("Bereit")
        self.stop_conversion = False
        self.current_process = None
        self.current_file_index = 0
        self.total_duration = 0
        self.current_time = 0.0
        self.converter_input_files = []
        self.update_converter_file_display()
        self.convert_btn.set_sensitive(False)

    def conversion_finished(self):
        self.append_converter_log("═" * 40)
        self.append_converter_log("✅ KONVERTIERUNG ABGESCHLOSSEN - Alle Dateien erfolgreich konvertiert!")
        self.convert_btn.set_sensitive(True)
        self.cancel_btn.set_sensitive(False)
        self.select_files_btn.set_sensitive(True)
        self.converter_status_label.set_text("Bereit")
        self.converter_progress_bar.set_fraction(1.0)
        self.converter_progress_bar.set_text("100%")
        self.converter_percent_label.set_text("100%")
        GLib.timeout_add(2000, self.hide_converter_progress)
        self.show_info("Konvertierung aller Dateien abgeschlossen!")
        self.converter_input_files = []
        self.update_converter_file_display()
        self.convert_btn.set_sensitive(False)
        self.stop_conversion = False
        self.current_process = None
        self.current_file_index = 0
        self.total_duration = 0
        self.current_time = 0.0

    def hide_converter_progress(self):
        self.converter_progress_bar.set_visible(False)
        self.converter_percent_label.set_visible(False)
        return False

    # ==========================================================================
    # SETTINGS VIEW
    # ==========================================================================

    def create_settings_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        settings_box.set_margin_top(20)
        settings_box.set_margin_bottom(20)
        settings_box.set_margin_start(20)
        settings_box.set_margin_end(20)

        header = Gtk.Label()
        header.set_markup("<big><b>⚙️ Einstellungen</b></big>")
        header.set_halign(Gtk.Align.START)
        settings_box.append(header)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(5)
        separator.set_margin_bottom(15)
        settings_box.append(separator)

        general_group = Adw.PreferencesGroup()
        general_group.set_title("Allgemeine Einstellungen")
        settings_box.append(general_group)

        save_path_row = Adw.ActionRow()
        save_path_row.set_title("Standard-Speicherort")
        save_path_row.set_subtitle("Wird für Downloads und Konvertierungen verwendet")

        save_path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.default_path_entry = Gtk.Entry()
        self.default_path_entry.set_hexpand(True)
        default_path = self.settings.get("general", "default_save_path", str(Path.home() / "Downloads"))
        self.default_path_entry.set_text(default_path)
        save_path_box.append(self.default_path_entry)

        browse_default_btn = Gtk.Button(label="📁")
        browse_default_btn.set_tooltip_text("Ordner auswählen")
        browse_default_btn.connect("clicked", self.choose_default_folder)
        save_path_box.append(browse_default_btn)

        save_path_row.add_suffix(save_path_box)
        general_group.add(save_path_row)

        # Bildbearbeitungs-Programm Auswahl in Einstellungen
        editor_group = Adw.PreferencesGroup()
        editor_group.set_title("Bildbearbeitung")
        settings_box.append(editor_group)

        editor_row = Adw.ActionRow()
        editor_row.set_title("Standard-Bildbearbeitungsprogramm")
        editor_row.set_subtitle("Welches Programm soll für die Bildbearbeitung verwendet werden?")

        editor_choice_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.settings_editor_combo = Gtk.DropDown()
        self.settings_editor_combo.connect("notify::selected", self.on_settings_editor_changed)
        editor_choice_box.append(self.settings_editor_combo)
        
        editor_row.add_suffix(editor_choice_box)
        editor_group.add(editor_row)
        
        # Combobox für Einstellungen füllen
        self.update_settings_editor_combo()

        converter_group = Adw.PreferencesGroup()
        converter_group.set_title("Konverter-Einstellungen")
        settings_box.append(converter_group)

        keep_row = Adw.ActionRow()
        keep_row.set_title("Originaldateien behalten")
        keep_row.set_subtitle("Wenn deaktiviert, werden Originaldateien nach erfolgreicher Konvertierung gelöscht")
        self.keep_original_switch = Gtk.Switch()
        self.keep_original_switch.set_active(self.settings.get("converter", "keep_original", "true") == "true")
        self.keep_original_switch.set_valign(Gtk.Align.CENTER)
        keep_row.add_suffix(self.keep_original_switch)
        converter_group.add(keep_row)

        save_btn = Gtk.Button(label="Einstellungen speichern")
        save_btn.add_css_class("suggested-action")
        save_btn.set_margin_top(20)
        save_btn.connect("clicked", self.save_all_settings)
        settings_box.append(save_btn)

        scrolled.set_child(settings_box)
        return scrolled

    def update_settings_editor_combo(self):
        """Aktualisiert die Combobox in den Einstellungen"""
        installed = self.get_installed_image_editors()
        string_list = Gtk.StringList()
        
        self.settings_editor_commands = []
        
        for editor in installed:
            display = f"{editor['icon']} {editor['name']}"
            string_list.append(display)
            self.settings_editor_commands.append(editor["cmd"])
        
        self.settings_editor_combo.set_model(string_list)
        
        current = self.get_default_image_editor()
        for i, cmd in enumerate(self.settings_editor_commands):
            if cmd == current:
                self.settings_editor_combo.set_selected(i)
                break

    def on_settings_editor_changed(self, combo, *args):
        """Wird aufgerufen, wenn in den Einstellungen ein neues Programm ausgewählt wird"""
        selected_idx = self.settings_editor_combo.get_selected()
        if selected_idx >= 0 and selected_idx < len(self.settings_editor_commands):
            selected_cmd = self.settings_editor_commands[selected_idx]
            self.settings.set("image_editor", "default_editor", selected_cmd)
            # Auch in der Converter-View aktualisieren
            self.update_editor_combo()

    def choose_default_folder(self, widget):
        dialog = Gtk.FileDialog()
        dialog.set_title("Standard-Speicherort auswählen")
        dialog.select_folder(self, None, self.on_default_folder_selected)

    def on_default_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.default_path_entry.set_text(folder.get_path())
        except:
            pass

    def save_all_settings(self, widget):
        default_path = self.default_path_entry.get_text().strip()
        if default_path:
            self.settings.set("general", "default_save_path", default_path)
        
        self.settings.set("converter", "keep_original", str(self.keep_original_switch.get_active()).lower())
        
        self.show_info("Einstellungen gespeichert!")
        if hasattr(self, 'save_entry'):
            self.save_entry.set_text(default_path)

    # ==========================================================================
    # GEMEINSAME HILFSFUNKTIONEN
    # ==========================================================================

    def show_error(self, message):
        dialog = Adw.MessageDialog(transient_for=self, heading="Fehler", body=message)
        dialog.add_response("ok", "OK")
        dialog.present()

    def show_info(self, message):
        dialog = Adw.MessageDialog(transient_for=self, heading="Info", body=message)
        dialog.add_response("ok", "OK")
        dialog.present()

    def show_about(self, widget):
        about = Adw.AboutWindow(
            transient_for=self,
            application_name="Media-Werkzeug",
            version="2.3",
            developer_name="evilware666 & Helga",
            copyright="© 2024-2026",
            license_type=Gtk.License.MIT,
            comments="Ein leistungsstarkes Tool für:\n\n"
                    "• Video-Download von YouTube & Co.\n"
                    "• Audio-Extraktion (MP3, FLAC, etc.)\n"
                    "• Medien-Konvertierung (Video, Audio, Bilder)\n"
                    "• Externe Bildbearbeitung (GIMP, Pinta, Krita, etc.)\n"
                    "• Batch-Verarbeitung mit Fortschrittsanzeige\n"
                    "• Drag & Drop Unterstützung\n\n"
                    "Bilder werden mit Ihrem ausgewählten Standard-Programm bearbeitet.\n"
                    "Unterstützte Bildbearbeitungsprogramme:\n"
                    "GIMP, Pinta, Krita, Inkscape, KolourPaint, MyPaint, LazPaint,\n"
                    "XnView MP, Shotwell, Darktable, RawTherapee"
        )
        about.present()


def main():
    app = MediaMultiTool()
    return app.run()


if __name__ == "__main__":
    main()
