# Deutscher Video-Synchronisierer (Windows-App)

Eine Windows-Anwendung, die die gesprochene Sprache in **eigenen** Videos
ins Deutsche übersetzt und die Originalstimme durch eine deutsche
KI-Stimme (Voice Cloning) ersetzt - über die ElevenLabs Dubbing-API.

## Wichtig: nur für eigene Inhalte

Diese App ist für Videos gedacht, an denen du die Rechte hast (eigene
Aufnahmen, eigene Projekte, Kundenprojekte mit entsprechender
Beauftragung, lizenziertes Material). **Nicht** für fremde kommerzielle
Filme oder Serien ohne Erlaubnis des Rechteinhabers.

## Installation

1. Lade die neueste `GermanVideoDubber-Setup.exe` von der
   [Releases-Seite](../../releases) herunter.
2. Doppelklick auf die Datei, Installationsassistent durchklicken. Das
   war's - `ffmpeg` ist bereits enthalten, nichts weiter nötig.

## Einmalige Einrichtung (kann niemand automatisieren)

Die App braucht einen eigenen **ElevenLabs API-Schlüssel**:

1. Kostenlos/kostenpflichtig registrieren auf [elevenlabs.io](https://elevenlabs.io)
   (die Dubbing-Funktion mit Stimmklonen braucht i. d. R. einen
   kostenpflichtigen Plan - aktuelle Preise dort prüfen).
2. API-Schlüssel kopieren.
3. In der App beim Start in das Feld "ElevenLabs API-Schlüssel" einfügen.

Die App zeigt beim Start eine Liste der Voraussetzungen mit Status
(✅/❌) an. Fehlt etwas, erscheint daneben ein Link zum Herunterladen /
Einrichten, und ein Button "Erneut prüfen" zeigt an, sobald alles bereit
ist.

## Build-Pipeline (automatisch)

Jeder Push auf `main` löst `.github/workflows/build-windows.yml` aus:

1. Baut die App mit PyInstaller auf einem echten Windows-Server.
2. Bündelt `ffmpeg.exe` automatisch mit ein.
3. Führt einen Selbsttest der gebauten .exe aus.
4. Baut mit Inno Setup einen fertigen Installer.
5. **Installiert den Installer tatsächlich (silent) und führt den
   Selbsttest an der installierten Version erneut aus** - erst wenn das
   klappt, gilt der Build als erfolgreich.
6. Lädt den fertigen Installer als Artefakt hoch und veröffentlicht ihn
   als GitHub Release.

## Projektstruktur

```
app/              Quellcode der GUI-App (main.py)
installer/        Inno-Setup-Skript für den Installer
.github/workflows/  Automatischer Build + Test auf Windows
```
