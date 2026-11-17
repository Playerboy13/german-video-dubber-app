#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deutscher Video-Synchronisierer
--------------------------------
Eine einfache Windows-GUI-App, die die gesprochene Sprache in einem
eigenen Video erkennt, ins Deutsche übersetzt und die Originalstimme durch
eine (geklonte) deutsche KI-Stimme ersetzt - über die ElevenLabs
Dubbing-API.

Dieses Programm ist NUR für Videos gedacht, an denen der Nutzer die Rechte
hat (eigene Aufnahmen, eigene Projekte, lizenziertes Material). Es ist
nicht dafür gedacht, fremde kommerzielle Filme oder Serien neu zu
synchronisieren und weiterzuverbreiten.
"""
import json
import os
import sys
import threading
import time
import traceback

APP_NAME = "Deutscher Video-Synchronisierer"
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "GermanVideoDubber")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
API_BASE = "https://api.elevenlabs.io/v1"


def resource_path(relative_path):
    """Findet eine Datei, egal ob das Programm als .py-Skript läuft oder
    von PyInstaller zu einer .exe gebündelt wurde."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def bundled_ffmpeg_path():
    """Pfad zur mitgelieferten ffmpeg.exe (wird vom Installer mitgebündelt,
    der Nutzer muss nichts selbst installieren)."""
    candidate = resource_path(os.path.join("bin", "ffmpeg.exe"))
    if os.path.isfile(candidate):
        return candidate
    # Fallback: ffmpeg.exe liegt direkt neben der .exe (onedir-Build)
    alt = os.path.join(os.path.dirname(sys.executable), "bin", "ffmpeg.exe")
    if os.path.isfile(alt):
        return alt
    return None


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------
# Abhängigkeitsprüfung: jede Zeile hier entspricht einem Eintrag, der in
# der GUI als "benötigt" angezeigt wird - mit Status (OK/fehlt) und,
# falls nötig, einem Download-Link daneben.
# ---------------------------------------------------------------------
def check_dependencies(api_key=None):
    """Gibt eine Liste von Abhängigkeiten mit Status zurück.
    Jeder Eintrag: {name, ok, info, download_url (oder None)}"""
    results = []

    # 1. ffmpeg - wird mitgeliefert, sollte also immer vorhanden sein.
    ffmpeg = bundled_ffmpeg_path()
    if ffmpeg:
        results.append({
            "name": "ffmpeg (Video-/Audio-Werkzeug)",
            "ok": True,
            "info": "Ist bereits im Programm enthalten - keine Installation nötig.",
            "download_url": None,
        })
    else:
        results.append({
            "name": "ffmpeg (Video-/Audio-Werkzeug)",
            "ok": False,
            "info": "Fehlt unerwartet (sollte mitgeliefert sein). Bitte neu installieren.",
            "download_url": "https://www.gyan.dev/ffmpeg/builds/",
        })

    # 2. ElevenLabs-Konto / API-Key - das ist die einzige Sache, die der
    # Nutzer selbst einmalig einrichten muss (Cloud-Konto, kein Programm).
    key_ok = bool(api_key)
    results.append({
        "name": "ElevenLabs-Konto (API-Schlüssel)",
        "ok": key_ok,
        "info": (
            "API-Schlüssel eingetragen." if key_ok else
            "Noch kein API-Schlüssel eingetragen. Kostenlos/kostenpflichtig "
            "registrieren, Schlüssel kopieren und unten einfügen."
        ),
        "download_url": None if key_ok else "https://elevenlabs.io",
    })

    return results


def verify_api_key(api_key):
    """Prüft den API-Key mit einem echten, leichten API-Aufruf."""
    import requests
    try:
        resp = requests.get(f"{API_BASE}/user", headers={"xi-api-key": api_key}, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------
# Dubbing-Workflow (läuft im Hintergrund-Thread, damit die GUI nicht
# einfriert)
# ---------------------------------------------------------------------
def run_dubbing_job(video_path, api_key, target_lang, num_speakers, log_cb, done_cb, error_cb):
    import requests

    try:
        log_cb(f"Starte Übertragung von '{os.path.basename(video_path)}' ...")
        data = {"target_lang": target_lang}
        if num_speakers:
            data["num_speakers"] = str(num_speakers)

        with open(video_path, "rb") as f:
            files = {"file": (os.path.basename(video_path), f)}
            resp = requests.post(
                f"{API_BASE}/dubbing",
                headers={"xi-api-key": api_key},
                data=data,
                files=files,
                timeout=600,
            )

        if resp.status_code not in (200, 201):
            error_cb(f"Fehler beim Hochladen: {resp.status_code} - {resp.text}")
            return

        job = resp.json()
        dubbing_id = job.get("dubbing_id")
        if not dubbing_id:
            error_cb(f"Unerwartete Antwort vom Server: {job}")
            return

        log_cb("Hochgeladen. Verarbeitung läuft (Übersetzung + Stimme) ...")

        elapsed = 0
        poll_interval = 15
        timeout = 60 * 60  # 1 Stunde Obergrenze

        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval
            status_resp = requests.get(
                f"{API_BASE}/dubbing/{dubbing_id}", headers={"xi-api-key": api_key}, timeout=30
            )
            if status_resp.status_code != 200:
                error_cb(f"Fehler bei Status-Abfrage: {status_resp.status_code} - {status_resp.text}")
                return

            status_json = status_resp.json()
            status = status_json.get("status")
            log_cb(f"Status nach {elapsed}s: {status}")

            if status == "dubbed":
                break
            if status == "failed":
                error_cb(f"Verarbeitung fehlgeschlagen: {status_json}")
                return
        else:
            error_cb("Zeitüberschreitung: Die Verarbeitung hat zu lange gedauert.")
            return

        log_cb("Lade fertiges Video herunter ...")
        base, ext = os.path.splitext(video_path)
        out_path = f"{base}-{target_lang}{ext or '.mp4'}"
        dl_resp = requests.get(
            f"{API_BASE}/dubbing/{dubbing_id}/audio/{target_lang}",
            headers={"xi-api-key": api_key},
            stream=True,
            timeout=300,
        )
        if dl_resp.status_code != 200:
            error_cb(f"Fehler beim Herunterladen: {dl_resp.status_code} - {dl_resp.text}")
            return

        with open(out_path, "wb") as out_f:
            for chunk in dl_resp.iter_content(chunk_size=8192):
                out_f.write(chunk)

        log_cb(f"Fertig! Gespeichert unter: {out_path}")
        done_cb(out_path)

    except Exception as exc:  # pragma: no cover - defensive
        error_cb(f"Unerwarteter Fehler: {exc}\n{traceback.format_exc()}")


# ---------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------
def build_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    cfg = load_config()

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("640x560")
    root.resizable(False, False)

    notice = tk.Label(
        root,
        text=(
            "Nur für eigene Videos oder Videos mit entsprechenden Rechten nutzen.\n"
            "Nicht für fremde kommerzielle Filme/Serien gedacht."
        ),
        fg="#883300",
        justify="left",
        wraplength=600,
    )
    notice.pack(padx=16, pady=(12, 4), anchor="w")

    # --- Abhängigkeiten / Voraussetzungen -----------------------------
    dep_frame = ttk.LabelFrame(root, text="Voraussetzungen")
    dep_frame.pack(fill="x", padx=16, pady=8)

    dep_rows = []

    def render_dependencies():
        for widget in dep_frame.winfo_children():
            widget.destroy()
        dep_rows.clear()

        deps = check_dependencies(api_key_var.get().strip())
        for dep in deps:
            row = ttk.Frame(dep_frame)
            row.pack(fill="x", padx=8, pady=4)

            status = "✅" if dep["ok"] else "❌"
            label = ttk.Label(row, text=f"{status} {dep['name']} - {dep['info']}", wraplength=480, justify="left")
            label.pack(side="left")

            if dep["download_url"]:
                def open_link(url=dep["download_url"]):
                    import webbrowser
                    webbrowser.open(url)

                link_btn = ttk.Button(row, text="Öffnen / Herunterladen", command=open_link)
                link_btn.pack(side="right")

        all_ok = all(d["ok"] for d in deps)
        status_label.config(
            text="Alles bereit ✅" if all_ok else "Noch nicht alles bereit ❌ - siehe oben",
            fg="green" if all_ok else "#aa0000",
        )
        start_btn.config(state=("normal" if all_ok else "disabled"))

    recheck_btn = ttk.Button(dep_frame, text="Erneut prüfen", command=lambda: render_dependencies())
    recheck_btn.pack(anchor="e", padx=8, pady=(0, 8))

    status_label = tk.Label(root, text="", font=("Segoe UI", 10, "bold"))
    status_label.pack(padx=16, anchor="w")

    # --- Eingaben -------------------------------------------------------
    form_frame = ttk.LabelFrame(root, text="Video auswählen und Einstellungen")
    form_frame.pack(fill="x", padx=16, pady=8)

    video_path_var = tk.StringVar()
    api_key_var = tk.StringVar(value=cfg.get("api_key", ""))
    speakers_var = tk.StringVar(value=cfg.get("num_speakers", "Automatisch"))

    row1 = ttk.Frame(form_frame)
    row1.pack(fill="x", padx=8, pady=6)
    ttk.Label(row1, text="Video-Datei:").pack(side="left")
    video_entry = ttk.Entry(row1, textvariable=video_path_var, width=45)
    video_entry.pack(side="left", padx=6)

    def choose_file():
        path = filedialog.askopenfilename(
            title="Video auswählen",
            filetypes=[("Videos", "*.mp4 *.mov *.mkv *.avi"), ("Alle Dateien", "*.*")],
        )
        if path:
            video_path_var.set(path)

    ttk.Button(row1, text="Durchsuchen ...", command=choose_file).pack(side="left")

    row2 = ttk.Frame(form_frame)
    row2.pack(fill="x", padx=8, pady=6)
    ttk.Label(row2, text="ElevenLabs API-Schlüssel:").pack(side="left")
    api_entry = ttk.Entry(row2, textvariable=api_key_var, width=40, show="*")
    api_entry.pack(side="left", padx=6)

    def on_api_key_change(*_):
        render_dependencies()

    api_key_var.trace_add("write", on_api_key_change)

    row3 = ttk.Frame(form_frame)
    row3.pack(fill="x", padx=8, pady=6)
    ttk.Label(row3, text="Anzahl Sprecher:").pack(side="left")
    speakers_combo = ttk.Combobox(
        row3, textvariable=speakers_var, values=["Automatisch", "1", "2", "3", "4"], width=12, state="readonly"
    )
    speakers_combo.pack(side="left", padx=6)

    # --- Log / Fortschritt ------------------------------------------
    log_frame = ttk.LabelFrame(root, text="Fortschritt")
    log_frame.pack(fill="both", expand=True, padx=16, pady=8)

    log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
    log_text.pack(fill="both", expand=True, padx=8, pady=8)

    def log_cb(msg):
        def _update():
            log_text.config(state="normal")
            log_text.insert("end", msg + "\n")
            log_text.see("end")
            log_text.config(state="disabled")
        root.after(0, _update)

    def set_busy(busy):
        start_btn.config(state=("disabled" if busy else "normal"))
        video_entry.config(state=("disabled" if busy else "normal"))
        api_entry.config(state=("disabled" if busy else "normal"))
        speakers_combo.config(state=("disabled" if busy else "readonly"))

    def done_cb(out_path):
        def _update():
            set_busy(False)
            messagebox.showinfo(APP_NAME, f"Fertig!\n\nDatei gespeichert unter:\n{out_path}")
        root.after(0, _update)

    def error_cb(msg):
        def _update():
            set_busy(False)
            log_cb(f"FEHLER: {msg}")
            messagebox.showerror(APP_NAME, msg)
        root.after(0, _update)

    def start():
        video_path = video_path_var.get().strip()
        api_key = api_key_var.get().strip()
        speakers_raw = speakers_var.get()
        num_speakers = None if speakers_raw == "Automatisch" else int(speakers_raw)

        if not video_path or not os.path.isfile(video_path):
            messagebox.showwarning(APP_NAME, "Bitte zuerst eine gültige Video-Datei auswählen.")
            return
        if not api_key:
            messagebox.showwarning(APP_NAME, "Bitte zuerst den ElevenLabs API-Schlüssel eintragen.")
            return

        save_config({"api_key": api_key, "num_speakers": speakers_raw})

        set_busy(True)
        log_text.config(state="normal")
        log_text.delete("1.0", "end")
        log_text.config(state="disabled")

        thread = threading.Thread(
            target=run_dubbing_job,
            args=(video_path, api_key, "de", num_speakers, log_cb, done_cb, error_cb),
            daemon=True,
        )
        thread.start()

    start_btn = ttk.Button(root, text="Synchronisierung starten", command=start)
    start_btn.pack(pady=10)

    render_dependencies()
    root.mainloop()


# ---------------------------------------------------------------------
# Selbsttest für die automatisierte Prüfung im Build (ohne GUI-Fenster)
# ---------------------------------------------------------------------
def selftest():
    print("== Selbsttest: Deutscher Video-Synchronisierer ==")
    ok = True

    ffmpeg = bundled_ffmpeg_path()
    if not ffmpeg:
        print("FAIL: ffmpeg.exe wurde nicht gefunden.")
        ok = False
    else:
        import subprocess
        try:
            result = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, timeout=20)
            if result.returncode == 0 and "ffmpeg version" in result.stdout.lower():
                print(f"OK: ffmpeg funktioniert ({ffmpeg})")
            else:
                print(f"FAIL: ffmpeg lief, aber unerwartete Ausgabe: {result.stdout[:200]}")
                ok = False
        except Exception as exc:
            print(f"FAIL: ffmpeg konnte nicht ausgeführt werden: {exc}")
            ok = False

    deps = check_dependencies(api_key=None)
    print("Abhängigkeits-Check (ohne API-Key, Key-Zeile MUSS fehlend sein):")
    for d in deps:
        print(f"  - {d['name']}: ok={d['ok']} info={d['info']}")

    # ffmpeg muss ok sein, der API-Key-Eintrag darf (erwartungsgemäß) fehlen
    ffmpeg_dep = next(d for d in deps if "ffmpeg" in d["name"])
    if not ffmpeg_dep["ok"]:
        ok = False

    try:
        import requests  # noqa: F401
        import tkinter  # noqa: F401
        print("OK: benötigte Python-Module (requests, tkinter) sind vorhanden.")
    except Exception as exc:
        print(f"FAIL: Modul fehlt: {exc}")
        ok = False

    if ok:
        print("SELFTEST RESULT: PASS")
        sys.exit(0)
    else:
        print("SELFTEST RESULT: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        build_gui()
