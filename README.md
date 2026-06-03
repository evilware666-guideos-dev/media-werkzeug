
# Media-Werkzeug

Ein leistungsstarkes GTK4/Libadwaita-Multi-Tool für Video-Download, Audio-Extraktion und Medien-Konvertierung.
---

## 📋 Beschreibung

**Media-Werkzeug** ist eine All-in-One-Lösung für die Medienbearbeitung unter Linux. Es kombiniert einen Video-Downloader (yt-dlp) mit einem leistungsfähigen Medien-Konverter (ffmpeg) in einer modernen, benutzerfreundlichen Oberfläche.

**Autoren:** evilware666 & Helga  
**Version:** 1.1  
**Lizenz:** MIT

---

## ✨ Hauptfunktionen

### 🎬 Video Downloader
- **URL-basierter Download** von YouTube und vielen anderen Plattformen
- **Qualitätsauswahl** – Beste, 1080p, 720p, 480p, 360p
- **Formatauswahl** – MP4, MKV, WEBM, AVI
- **Playlist-Unterstützung** (einzeln oder komplett)

### 🎵 Audio Extraktion
- **Formate:** MP3, M4A, OGG, OPUS, FLAC, WAV
- **Qualitätsstufen** für verlustbehaftete Formate
- **Thumbnail-Einbettung** als Cover-Bild

### 🔄 Media Konverter
- **Drag & Drop** – Dateien einfach ins Fenster ziehen
- **Batch-Verarbeitung** – Mehrere Dateien auf einmal konvertieren
- **Video-Konvertierung** – MP4, AVI, MKV, MOV, WEBM mit Auflösungsanpassung
- **Audio-Konvertierung** – Alle gängigen Formate, auch verlustfrei (FLAC, WAV)
- **Bild-Konvertierung** – JPG, PNG, WEBP, BMP mit einstellbarer Qualität

### ⚙️ Einstellungen
- **Standard-Speicherort** für Downloads und Konvertierungen
- **Originaldateien behalten/löschen** nach Konvertierung

---

## 🚀 Installation

### Abhängigkeiten

```bash
sudo apt update
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 yt-dlp ffmpeg
```

### Ausführung

```bash
python3 media-werkzeug.py
```

---

## 🖥️ Bedienung

### Navigation

Die App verfügt über eine seitliche Navigationsleiste mit drei Hauptbereichen:

| Symbol | Bereich | Beschreibung |
|--------|---------|--------------|
| 🎬 | **Video Downloader** | Videos und Audio von Webseiten herunterladen |
| 🔄 | **Media Konverter** | Lokale Mediendateien konvertieren |
| ⚙️ | **Einstellungen** | Programmkonfiguration |

---

### 1. Video Downloader

1. **URL eingeben** – Video- oder Playlist-Link in das Feld einfügen
2. **Modus wählen** – Video oder Nur Audio
3. **Optionen einstellen** – Qualität, Format, Thumbnail (bei Audio)
4. **Speicherort** – Zielordner auswählen
5. **Download starten** – Fortschritt wird live angezeigt

---

### 2. Media Konverter

#### Dateien hinzufügen
- **Drag & Drop** – Dateien direkt in das markierte Feld ziehen
- **Durchsuchen** – Über den Button Dateien auswählen

#### Format wählen
- **Video** – Zielformat + Auflösung (Original/1080p/720p/480p/360p)
- **Audio** – Zielformat + Bitrate (bei MP3/M4A/OGG)
- **Bild** – Zielformat + Qualität (Hoch/Mittel/Niedrig)



> 💡 **Tipp:** Während der Konvertierung mit **ESC** abbrechen!
- Originaldateien können automatisch gelöscht werden
---

## 📊 Fortschrittsanzeige

Beide Module zeigen Live-Fortschritt:

- **Downloader** – Prozentuale Anzeige + Live-yt-dlp-Log
- **Konverter** – Fortschrittsbalken + Zeitfortschritt (bei Video/Audio)

---

## 🛠️ Technische Details

### Unterstützte Formate

#### Video (Konverter)
| Format | Beschreibung |
|--------|--------------|
| MP4 | Universelles Format, beste Kompatibilität |
| AVI | Älteres Format, breite Unterstützung |
| MKV | Container für hohe Flexibilität |
| MOV | Apple-kompatibel |
| WEBM | Optimal für Web-Anwendungen |

#### Audio (Downloader & Konverter)
| Format | Typ | Qualitätseinstellung |
|--------|-----|---------------------|
| MP3 | Verlustbehaftet | 320k, 256k, 192k, 128k |
| M4A/AAC | Verlustbehaftet | 320k, 256k, 192k, 128k |
| OGG | Verlustbehaftet | 320k, 192k, 128k, 96k |
| OPUS | Verlustbehaftet | Beste/Hoch/Mittel/Niedrig |
| FLAC | Verlustfrei | – |
| WAV | Unkomprimiert | – |

#### Bilder (Konverter)
| Format | Qualitätseinstellung |
|--------|---------------------|
| JPG | 90% / 75% / 50% |
| PNG | – (verlustfrei) |
| WEBP | 90% / 75% / 50% |
| BMP | – (unkomprimiert) |

---

## 📁 Konfigurationsdatei

Die Einstellungen werden in `~/.config/media-werkzeug.ini` gespeichert:

```ini
[general]
default_save_path = /home/user/Downloads

[converter]
keep_original = true
```

---

## 🧪 Fehlersuche

### Abhängigkeiten prüfen
Klicke auf **„Abhängigkeiten prüfen“** in der Kopfleiste.

### Fehlende Pakete
```bash
sudo apt install yt-dlp ffmpeg
```

### Logs
- Der **Downloader** zeigt alle yt-dlp-Ausgaben im unteren Log-Bereich
- Der **Konverter** hat ein separates Log-Fenster
- Mit **„🗑 Leeren“** kannst du die Logs zurücksetzen

---

## ⌨️ Tastenkürzel

| Taste | Aktion |
|-------|--------|
| `ESC` | Konvertierung abbrechen (während des Vorgangs) |

---

## ⚠️ Bekannte Einschränkungen

- Funktioniert nur unter **Linux** (Debian/Ubuntu & Derivate)
- Benötigt `yt-dlp` und `ffmpeg` für vollständige Funktionalität
- Manche Video-Formate erfordern ggf. zusätzliche Codecs

---


## 🙏 Danksagung

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) – Videodownload-Backend
- [FFmpeg](https://ffmpeg.org/) – Medienkonvertierung
- [GTK](https://gtk.org/) / [Libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) – GUI-Framework

---

