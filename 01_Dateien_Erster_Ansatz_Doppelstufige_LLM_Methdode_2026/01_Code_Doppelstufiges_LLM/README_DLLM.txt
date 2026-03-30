=============================================================================
DETAILLIERTE DOKUMENTATION: ISO / INCOSE Anforderungsextraktion V3 (Multimodal)
=============================================================================

Dieses Dokument erklärt den vollständigen Ablauf des Skripts
"OPT_V3_API_Chunking_Ansatz.py" bis ins kleinste Detail und zeigt auf,
wie die Umgebung eingerichtet wird, wie der Code Schritt für Schritt
funktioniert und welche Ausgabe am Ende erzeugt wird.

Zielgruppe: Python-Einsteiger mit VS Code (kein tiefes Vorwissen nötig).


=============================================================================
TEIL A: SETUP UND VORBEREITUNG DER UMGEBUNG (SCHRITT FÜR SCHRITT)
=============================================================================

Bevor du das Skript starten kannst, musst du einmalig die Umgebung
einrichten. Das dauert ca. 5–10 Minuten.

--------------------------------------------------
A.1  Voraussetzungen (Was du brauchst)
--------------------------------------------------

1.  Python 3.11
    Prüfe deine Version im Terminal mit: python --version
    Falls nicht vorhanden: https://www.python.org/downloads/

2.  Visual Studio Code (VS Code)
    Download: https://code.visualstudio.com/
    Empfohlene Erweiterungen:
    - "Python" (von Microsoft) – installierst du im Extensions-Tab (Strg+Shift+X)

3.  Die folgenden Dateien müssen sich im SELBEN Ordner befinden:
    - OPT_V3_API_Chunking_Ansatz.py    (das Hauptskript)
    - INCOSE_REGELWERK.py              (die 42 INCOSE-Regeln als Python-Datei)
    - .env                             (deine API-Zugangsdaten – siehe A.3)
    - dein PDF (z. B. Pflichtenheft.pdf)

--------------------------------------------------
A.2  Projektordner in VS Code öffnen
--------------------------------------------------

1.  Öffne VS Code.
2.  Klicke oben links auf "Datei" → "Ordner öffnen..."
3.  Wähle den Ordner aus, in dem deine Skript-Dateien liegen.
4.  Öffne ein neues Terminal innerhalb von VS Code:
    Menü → "Terminal" → "Neues Terminal"

--------------------------------------------------
A.3  Die .env-Datei anlegen (API-Zugangsdaten)
--------------------------------------------------

Das Skript liest alle geheimen Zugangsdaten aus einer Datei namens ".env".
Diese Datei erstellst du MANUELL in deinem Projektordner.

Erstelle eine neue Datei mit dem Namen genau: .env  
Inhalt der .env-Datei:

    SAIA_API_KEY=dein-api-schluessel-hier-eintragen
    SAIA_API_BASE=https://deine-academic-cloud-url/v1
    TARGET_PDF=Pflichtenheft.pdf
    MAX_CHUNKS=50 

Erklärung der Variablen:
    SAIA_API_KEY  → Dein persönlicher API-Schlüssel von der Academic Cloud
    SAIA_API_BASE → Die Basis-URL der SAIA / Academic Cloud API
    TARGET_PDF    → Dateiname deines PDFs (muss im selben Ordner liegen!)
    MAX_CHUNKS    → Wie viele Textabschnitte maximal verarbeitet werden sollen
                    (Empfehlung für Tests: 50; für Produktion: 150 oder mehr)

WICHTIG: Die .env-Datei enthält geheime Daten. Teile sie niemals mit anderen
und lade sie nicht in GitHub oder andere Dienste hoch!

--------------------------------------------------
A.4  Virtuelle Umgebung erstellen und aktivieren
--------------------------------------------------

Eine virtuelle Umgebung (venv) ist ein isolierter Python-Bereich nur für
dieses Projekt. Sie verhindert Konflikte mit anderen Python-Projekten auf
deinem PC.

Schritt 1: Virtuelle Umgebung erstellen
Im Terminal (in deinem Projektordner) eingeben:

    py -3.11 -m venv .venv

→ Es wird ein versteckter Ordner ".venv" erstellt. Das ist normal.

Schritt 2: Virtuelle Umgebung aktivieren
Windows:
    .\.venv\Scripts\activate

macOS / Linux:
    source .venv/bin/activate

Wenn die Aktivierung geklappt hat, siehst du im Terminal links das Präfix:
    (.venv) C:\dein\Projektordner>

Tipp: Du musst die Umgebung JEDES MAL aktivieren, wenn du ein neues
Terminal öffnest. VS Code kann das auch automatisch machen (siehe A.6).

--------------------------------------------------
A.5  Alle benötigten Bibliotheken installieren
--------------------------------------------------

Gib im Terminal (mit aktivierter .venv) diesen Befehl ein:

    pip install PyMuPDF pandas tqdm openai spacy pdfplumber openpyxl python-dotenv

Was die einzelnen Pakete machen:
    PyMuPDF (fitz)   → Öffnet und liest PDF-Dateien (Text und Bilder)
    pandas           → Verwaltet und exportiert die Tabellendaten nach Excel
    tqdm             → Zeigt einen Fortschrittsbalken im Terminal
    openai           → Kommuniziert mit den KI-Modellen über die API
    spacy            → Analysiert deutschen Text (Satzzerlegung)
    pdfplumber       → Extrahiert Tabellen aus PDFs
    openpyxl         → Schreibt die finale Excel-Datei
    python-dotenv    → Liest die geheimen Werte aus deiner .env-Datei

--------------------------------------------------
A.6  Deutsches Sprachmodell für spaCy laden
--------------------------------------------------

spaCy braucht ein Sprachmodell, um deutsche Sätze korrekt zu erkennen.
Gib im Terminal ein:

    python -m spacy download de_core_news_sm

→ Das Modell wird automatisch heruntergeladen (ca. 15 MB).

--------------------------------------------------
A.7  VS Code für automatische venv-Aktivierung einrichten (Optional)
--------------------------------------------------

Damit VS Code die virtuelle Umgebung automatisch erkennt:
1.  Drücke Strg+Shift+P → Tippe "Python: Select Interpreter"
2.  Wähle die Option mit ".venv" (z.B. ".\.venv\Scripts\python.exe")
→ Ab jetzt wird die venv im Terminal automatisch aktiviert.

--------------------------------------------------
A.8  Skript starten
--------------------------------------------------

Wenn alles eingerichtet ist, starte das Skript mit:

    python OPT_V3_API_Chunking_Ansatz.py

Du siehst dann Fortschrittsbalken im Terminal, z.B.:
    PDF Auslesen (Multimodal): 100%|████████| 12/12 [01:23<00:00]
    ISO-29148 Verarbeitung:  45%|████░░░░| 23/50 [02:11<02:40]

Am Ende erscheint: ✅ Fertig: ISO_29148_Requirements_Ergebnis.xlsx


=============================================================================
TEIL B: DER CODE SCHRITT FÜR SCHRITT ERKLÄRT
=============================================================================

Der Code ist in 9 nummerierte Abschnitte (Sections) aufgeteilt.
Hier folgt eine detaillierte Erklärung jedes Abschnitts:

--------------------------------------------------
B.1  Abschnitt 1 – Importe & Initialisierung
--------------------------------------------------

Am Anfang des Skripts werden alle nötigen Bibliotheken geladen:

    import fitz        → Zum Lesen von PDFs
    import pandas      → Für die spätere Excel-Ausgabe
    import spacy       → Für die intelligente Satzzerlegung
    import pdfplumber  → Für die Tabellen-Extraktion aus PDFs

Das Skript versucht außerdem, die externe Datei INCOSE_REGELWERK.py zu
laden. Diese Datei enthält die 42 normativen INCOSE-Regeln als Python-
Dictionary. Fehlt diese Datei, gibt das Skript eine Warnung aus und macht
mit einer leeren Regelbasis weiter.

Danach wird die .env-Datei eingelesen (über python-dotenv) und die drei
KI-Modelle werden definiert:

    GENERATOR_MODEL  → llama-3.1-sauerkrautlm-70b-instruct
                        Zuständig für das Formulieren der Anforderungen

    CRITIC_MODEL     → llama-3.3-70b-instruct
                        Zuständig für die strenge Regelprüfung (INCOSE)

    VISION_MODEL     → qwen3-vl-30b-a3b-instruct
                        Zuständig für das Auslesen von Skizzen und
                        technischen Zeichnungen im PDF (Vision KI)

--------------------------------------------------
B.2  Abschnitt 2 – Konfiguration & Sicherheits-Check
--------------------------------------------------

Das Skript liest alle Konfigurationswerte aus der .env-Datei:

    API_KEY     → Dein Zugangscode zur KI-Plattform
    API_BASE    → Die URL der API
    PDF_INPUT   → Welches PDF verarbeitet werden soll
    MAX_CHUNKS  → Maximale Anzahl Textabschnitte (Sicherheitsbremse)

Fehlt einer dieser Werte in der .env, bricht das Skript sofort mit einer
klaren Fehlermeldung ab:
    "Fehler: API_KEY, API_BASE oder PDF_INPUT fehlen in der .env Datei!"

Das verhindert versehentliche Läufe ohne korrekte Konfiguration.

--------------------------------------------------
B.3  Abschnitt 3 – Multimodales PDF Auslesen (load_pdf_text)
--------------------------------------------------

Dies ist der erste große Verarbeitungsschritt. Das PDF wird Seite für Seite
geöffnet und auf DREI verschiedene Arten analysiert:

  --- 3a. Normalen Text extrahieren (PyMuPDF / fitz) ---

  Für jede Seite werden alle Textblöcke herausgelesen.
  Danach reinigt das Skript den Text mit regulären Ausdrücken (Regex):
    - Falsche Zeilenumbrüche mitten im Wort werden entfernt (Trennstriche)
    - Mehrfache Leerzeichen werden auf eines reduziert
    - Isolierte Seitenzahlen (reiner Zahlenmüll) werden verworfen

  Parallel dazu erkennt das Skript Kapitelüberschriften automatisch:
  Es sucht nach Zeilen, die mit einer Zahl beginnen und einem Großbuchstaben
  folgen, z.B. "4.1.1 Systemanforderungen". Diese werden als Kapitelname
  gespeichert und jedem nachfolgenden Textblock "aufgestempelt".
  Beispiel: "3.2 Lastannahmen" → alle folgenden Blöcke erhalten diesen Namen

  --- 3b. Tabellen extrahieren (pdfplumber) ---

  pdfplumber erkennt automatisch Tabellen im PDF.
  Das Skript transformiert jede Tabellenzeile in einen lesbaren deutschen Satz.
  Beispiel: Eine Tabelle mit den Spalten "Ebene | Lichte Höhe" und dem
  Inhalt "1 | 1110 mm" wird zu:
    "Spezifikation aus Tabelle (Seite 5) – Für das Bauteil gilt –
     Ebene ist 1, Lichte Höhe ist 1110 mm."

  Das ist wichtig, weil die KI später mit natürlichem Text arbeitet,
  nicht mit rohen Tabellenspalten.

  --- 3c. Skizzen & Zeichnungen auslesen (Qwen Vision KI) ---

  Jede PDF-Seite wird in ein PNG-Bild umgewandelt (150 DPI).
  Dieses Bild wird an die Vision-KI (Qwen VL) gesendet.
  Der KI wird genau erklärt, was sie tun soll:
    "Finde alle Skizzen und Zeichnungen. Extrahiere nur Maße und
    physikalische Werte. Beschreibe NICHT die Zeichnung selbst."
  Gibt die KI "LEER" zurück oder einen zu kurzen Text, wird das Ergebnis
  verworfen. Nur echte technische Maße werden weiterverarbeitet.

--------------------------------------------------
B.4  Abschnitt 4 – Textzerlegung in Chunks (Chunking)
--------------------------------------------------

Nach dem Auslesen liegt der gesamte Inhalt als eine Liste von Textblöcken vor.
Diese Blöcke werden jetzt in einzelne, atomare Sätze zerlegt.

  --- 4a. Satzzerlegung mit spaCy (iso_atomic_chunk_text) ---

  Das deutsche spaCy-Modell analysiert jeden Textblock grammatikalisch.
  Es erkennt echte Satzgrenzen und trennt dort – aber es "fällt nicht herein"
  auf Abkürzungen wie "z.B.", "bzw.", "DIN EN 1234.5" oder Dezimalzahlen.
  Sätze kürzer als 20 Zeichen werden als Fragmente verworfen.

  --- 4b. Chunk-Objekte mit Metadaten erzeugen (create_chunks) ---

  Jeder Satz bekommt ein vollständiges Daten-Paket (ein "Chunk"):
    chunk_id        → Eine einmalige Zufalls-ID (UUID) zur Rückverfolgung
    chunk_text      → Der eigentliche Satz
    context_text    → Die letzten 3 Sätze davor als Kontext (Sliding Window)
                      Bei Tabellen/Skizzen: direkt der zugehörige Blockinhalt
    page            → Seitenzahl im Original-PDF
    location_detail → Herkunft: "Fließtext", "Tabelle X", "Skizze"
    chapter         → Das erkannte Kapitel (z.B. "3.2 Lastannahmen")

  Das Sliding-Window-Prinzip bedeutet: Jeder Chunk "weiß", was die 3 Sätze
  davor waren. Das hilft der KI später, Abkürzungen und Rückbezüge korrekt
  einzuordnen (z.B. "Diese Eigenschaft" → KI weiß: Es geht um das Regal Typ A).

  Duplikate werden durch eine Signatur-Prüfung herausgefiltert.

--------------------------------------------------
B.5  Abschnitt 5 – Anforderungen formulieren (llm_generate_requirements)
--------------------------------------------------

Jetzt beginnt die eigentliche KI-Arbeit. Für jeden Chunk ruft das Skript
das Generator-LLM auf.

  Was der KI übergeben wird:
  Der Chunk-Text wird in zwei Bereiche aufgeteilt:
    "KONTEXT"          → Die letzten Sätze (für Bauteil-Erkennung)
    "EIGENTLICHE AUSSAGE" → Der aktuelle Satz (einzige Datenquelle für Fakten!)

  Die Rolle der KI:
  Das LLM bekommt einen sehr langen, strikten Prompt. Darin steht:
    - Es ist ein normativ arbeitender Requirements Engineer (ISO 29148)
    - Es darf KEINE Fakten erfinden (Zero-Hallucination-Policy)
    - Es darf KEINE kreativen Ergänzungen machen
    - Es darf NUR Werte aus der "EIGENTLICHEN AUSSAGE" nutzen
    - Den "KONTEXT" darf es NUR verwenden, um das richtige Subjekt zu benennen

  Die harten Ablehnungskriterien (Guardrails):
    - Enthält der Satz schwammige Wörter ohne Zahl ("hoch", "schnell",
      "ausreichend") → Anforderung wird ABGELEHNT
    - Ist die Aussage nur Metainformation (Seitenzahl, Tabellenüberschrift)
      ohne echte technische Werte → Anforderung wird ABGELEHNT
    - Anforderungen die nur ein Dokumentmerkmal beschreiben ("Die Tabelle
      zeigt...", "Zeile 6 enthält...") → werden ABGELEHNT

  Beispiel für eine Ablehnung:
    Chunk: "Spezifikation aus Tabelle (Seite 2) –"
    → KI: "Nicht genügend Information zur Ableitung einer ISO-konformen
           Anforderung."

  Beispiel für eine erfolgreiche Anforderung:
    Chunk: "Die Breite der einzelnen Fächer beträgt 100 mm."
    Kontext: "Regal Typ A"
    → KI: "Die Fächer des Regals Typ A müssen eine Breite von 100 mm
           aufweisen."

  Das Ausgabeformat der KI ist immer ein JSON-Objekt:
    { "requirements": ["Formulierte Anforderung Nummer 1."] }

  Bei API-Fehlern: Das Skript versucht es automatisch bis zu 5x erneut.
  Bei einem Rate-Limit-Fehler (Error 429) wartet es 4, 8, 12 ... Sekunden.

--------------------------------------------------
B.6  Abschnitt 6 – INCOSE Regelprüfung (llm_check_incose_compliance)
--------------------------------------------------

Jede erfolgreich formulierte Anforderung durchläuft jetzt eine zweite KI:
das Critic-Modell (llama-3.3-70b).

  Die Aufgabe des Critics:
  Es lädt alle 42 Regeln aus der INCOSE_REGELWERK.py und prüft die
  Anforderung gegen JEDE EINZELNE dieser Regeln.

  Mögliche Bewertungen pro Regel:
    "erfüllt"           → Regel ist eingehalten
    "nicht erfüllt"     → Regel wurde verletzt (z.B. Passivform benutzt,
                          schwammige Formulierung, fehlendes Modalverb)
    "nicht beurteilbar" → Regel kann anhand des Textes nicht beurteilt werden

  Das Gesamtergebnis:
  Nur wenn KEINE einzige Regel als "nicht erfüllt" markiert wurde, erhält die
  Anforderung den Status: "perfekt formuliert"
  Andernfalls: "nicht perfekt formuliert" + Liste der verletzten Regeln

  Das Ergebnis wird als kompaktes JSON gespeichert und später in Excel
  als lesbarer Text ausgegeben.

--------------------------------------------------
B.7  Abschnitt 6.5 – Nachweismethode bestimmen
     (llm_determine_verification_method)
--------------------------------------------------

Für jede Anforderung wird bestimmt, WIE man sie später im echten System
nachweisen kann. Das Generator-LLM muss sich auf genau EINE der vier
ISO-Kategorien festlegen:

  1. Inspektion
     → Für Eigenschaften, die man durch Hinschauen prüfen kann
     → Beispiel: "Das Gehäuse muss blau lackiert sein."
     → Nachweis: Visuelle Prüfung

  2. Analyse
     → Für Eigenschaften, die durch Simulation nachgewiesen werden müssen
     → Beispiel: "Das System muss 10.000 gleichzeitige Nutzer verkraften."
     → Nachweis: Computersimulation / Berechnung

  3. Demonstration
     → Für Funktionen, die man qualitativ vorführen kann
     → Beispiel: "Das Display muss sich nach 5 Minuten Inaktivität abschalten."
     → Nachweis: Einmalige Vorführung, keine komplexe Messtechnik

  4. Test
     → Für quantitative Eigenschaften mit Messwerten
     → Beispiel: "Die Reaktionszeit der Bremse muss < 200 ms betragen."
     → Nachweis: Kontrollierte Messung mit Instrumentierung

  Warum Temperature = 0.0 für diese Funktion?
  Die Einstellung Temperature=0.0 bedeutet, dass die KI immer deterministisch
  antwortet – also bei gleichem Input immer genau dieselbe Antwort liefert.
  Das macht die Klassifizierung reproduzierbar und verhindert zufällige
  Schwankungen in der Kategorienwahl.

  Das Ausgabeformat (JSON):
    { "Nachweismethode": "Test", "Begruendung": "Erfordert kontrollierte
      Bedingungen mit Instrumentierung für präzise Zeitmessung." }

--------------------------------------------------
B.8  Abschnitt 7 – Die Haupt-Pipeline (run_pipeline)
--------------------------------------------------

Die run_pipeline-Funktion steuert den gesamten Ablauf und bringt alle
Einzelfunktionen in die richtige Reihenfolge:

  Schritt 1: PDF einlesen       → load_pdf_text()
  Schritt 2: Chunks erstellen   → create_chunks()
  Schritt 3: Limit anwenden     → chunks = chunks[:MAX_CHUNKS]
  Schritt 4: Checkpoint laden   → Bereits verarbeitete Chunks überspringen
  Schritt 5: Hauptschleife:
             Für jeden unverarbeiteten Chunk:
             a) Anforderung formulieren     → llm_generate_requirements()
             b) INCOSE-Prüfung              → llm_check_incose_compliance()
             c) Nachweismethode bestimmen   → llm_determine_verification_method()
             d) Ergebniszeile zusammenstellen
             e) Checkpoint-Datei sofort speichern (atomar, crash-sicher)

  Das Checkpoint-System (Absturzsicherung):
  Nach JEDEM verarbeiteten Chunk wird der aktuelle Stand gesichert.
  Dazu schreibt das Skript:
    1. Zuerst in eine temporäre Datei: "checkpoint_iso29148.json.tmp"
    2. Dann benennt es diese sofort um in: "checkpoint_iso29148.json"
  Das os.replace() ist atomar – es gibt keinen Moment, in dem die Datei
  beschädigt oder leer sein kann. Bei einem Windows-Absturz mitten im
  Schreiben gehen so maximal 1 Chunk verloren, nie alle Daten.

  WICHTIG: Wenn du das Skript mit einem NEUEN PDF starten willst,
  musst du die Datei "checkpoint_iso29148.json" manuell löschen!
  Sonst überspringt das Skript alle Chunks, die schon mal verarbeitet wurden.

--------------------------------------------------
B.9  Abschnitte 8 & 9 – Excel-Export und Programmstart
--------------------------------------------------

  export_to_excel():
  Die pandas-Bibliothek wandelt alle gesammelten Zeilen in eine Excel-Datei
  um. Der Dateiname ist: ISO_29148_Requirements_Ergebnis.xlsx

  main():
  Die Einstiegsfunktion. Sie startet die Pipeline und ruft den Export auf.
  Wird ausgeführt, wenn du das Skript direkt startest:
    python OPT_V3_API_Chunking_Ansatz.py


=============================================================================
TEIL C: DER GLOBALE API-SCHUTZ (Retry-Logik im Detail)
=============================================================================

Da das Skript sehr viele API-Anfragen in kurzer Zeit sendet, kann die
KI-Plattform ein Limit auslösen (HTTP-Fehler 429 "Too Many Requests").

Das Skript schützt sich selbst dagegen:
  1. Tritt ein Fehler 429 auf, stürzt das Skript NICHT ab.
  2. Der except-Block greift und wartet eine dynamische Zeit:
     - Versuch 1: 4 Sekunden warten
     - Versuch 2: 8 Sekunden warten
     - Versuch 3: 12 Sekunden warten
     - Versuch 4: 16 Sekunden warten
     - Versuch 5: 20 Sekunden warten, dann aufgeben
  3. Nach der Wartezeit wird die Anfrage automatisch wiederholt.

Das gilt für alle drei KI-Funktionen gleichzeitig:
  - Anforderungsformulierung (Generator)
  - Regelprüfung (Critic)
  - Nachweismethode (Generator)


=============================================================================
TEIL D: DIE FINALE AUSGABE (WAS KOMMT AM ENDE RAUS?)
=============================================================================

Wenn das Skript fertig ist, erscheint im Terminal:
    ✅ Fertig: ISO_29148_Requirements_Ergebnis.xlsx

Du findest dann zwei neue Dateien in deinem Projektordner:

--------------------------------------------------
D.1  Die Checkpoint-Datei: checkpoint_iso29148.json
--------------------------------------------------

Dies ist der "Gedächtnisspeicher" des Skripts.
Sie dient ausschließlich dazu, dass das Skript bei einem Abbruch genau
an der gleichen Stelle weitermachen kann, ohne alles neu zu berechnen.

WICHTIG: Wenn du das Skript mit einem NEUEN PDF starten willst,
         musst du diese Datei zuerst manuell löschen!

--------------------------------------------------
D.2  Die Excel-Datei: ISO_29148_Requirements_Ergebnis.xlsx
--------------------------------------------------

Das ist dein finales Arbeitsergebnis. Die Tabelle hat folgende Spalten:

  Spalte A: Chunk-ID
  → Eine kryptische UUID-Nummer zur lückenlosen Nachverfolgbarkeit.
    Damit kann jede Anforderung immer bis zum Original-Textstelle
    im PDF zurückverfolgt werden.

  Spalte B: Kapitelbezeichnung
  → Das Kapitel des PDFs, aus dem der Chunk stammt.
    Beispiel: "3.2 Lastannahmen und Systemdaten"

  Spalte C: Seitenangabe
  → Die Seitenzahl im Original-PDF.
    Beispiel: 5

  Spalte D: Referenz
  → Wo genau der Text herkommt (Fließtext, Tabelle oder Skizze).
    Beispiel: "Fließtext (Abschnitt 3)" oder "Tabelle 2, Datenzeile 4"

  Spalte E: Kontext
  → Die Umgebungsinformationen, die dem KI-Modell mitgegeben wurden.
    Dient der Transparenz: Hier sieht man, was die KI "wusste".

  Spalte F: Original-Chunk-Text
  → Der rohe, unveränderte Satz aus dem PDF, der Tabelle oder der Skizze.
    Das ist die direkte Grundlage der Anforderung.

  Spalte G: ISO-Anforderung
  → Das KI-Ergebnis: Entweder die fertig formulierte normative Anforderung
    ODER die Standard-Ablehnung:
    "Nicht genügend Information zur Ableitung einer ISO-konformen
     Anforderung."

  Spalte H: Finale ISO-Bewertung
  → Das Gesamturteil der Regelprüfung.
    Mögliche Werte:
    - "perfekt formuliert"              → Alle 42 Regeln eingehalten
    - "nicht perfekt formuliert"        → Mindestens eine Regel verletzt
    - "Abgelehnt (Nicht generierbar)"   → Keine Anforderung ableitbar
    - "Fehler bei der Prüfung"          → Technisches Problem

  Spalte I: ISO-29148 / INCOSE Konformität
  → Ein detaillierter JSON-Text, der für jede der 42 Regeln zeigt:
    "R1: erfüllt", "R7: nicht erfüllt", "R14: nicht beurteilbar" usw.
    Erlaubt eine genaue Analyse, welche Regeln konkret verletzt wurden.

  Spalte J: Empfohlene Nachweismethode
  → Einer der vier Begriffe:
    "Inspektion" | "Analyse" | "Demonstration" | "Test"

  Spalte K: Nachweis-Begründung
  → Ein kurzer Satz der KI, warum genau diese Methode gewählt wurde.
    Beispiel: "Erfordert kontrollierte Messung mit Zeitmessgeräten, da
    ein quantitativer Grenzwert (<200 ms) angegeben ist."


=============================================================================
TEIL E: HÄUFIGE PROBLEME UND LÖSUNGEN
=============================================================================

Problem: "INCOSE_REGELWERK.py nicht gefunden"
Lösung:  Stelle sicher, dass die Datei INCOSE_REGELWERK.py im selben
         Ordner wie das Hauptskript liegt.

Problem: "Fehler: API_KEY, API_BASE oder PDF_INPUT fehlen"
Lösung:  Überprüfe deine .env-Datei. Alle drei Variablen müssen einen
         Wert haben. Achte auf korrekte Schreibweise (keine Leerzeichen
         um das "="-Zeichen).

Problem: "OSError: das deutsche spaCy Modell fehlt"
Lösung:  Führe aus: python -m spacy download de_core_news_sm
         (mit aktivierter .venv!)

Problem: Das Skript hört nach MAX_CHUNKS auf und Excel hat wenig Einträge
Lösung:  Erhöhe MAX_CHUNKS in der .env-Datei, z.B. auf 150 oder 300.

Problem: "ModuleNotFoundError: No module named 'fitz'"
Lösung:  Die .venv ist nicht aktiviert oder PyMuPDF fehlt.
         Aktiviere: .\.venv\Scripts\activate
         Dann: pip install PyMuPDF

Problem: Das Skript wurde abgebrochen. Wie geht es weiter?
Lösung:  Einfach erneut starten: python OPT_V3_API_Chunking_Ansatz.py
         Das Skript liest automatisch den Checkpoint und macht weiter.

Problem: Ich will das Skript mit einem neuen PDF starten
Lösung:  1. Ändere TARGET_PDF in der .env-Datei auf den neuen Dateinamen
         2. Lösche die Datei "checkpoint_iso29148.json"
         3. Starte das Skript neu


=============================================================================
TEIL F: ÜBERSICHT DER DATEIEN IM PROJEKTORDNER
=============================================================================

Nach einem erfolgreichen Durchlauf sieht dein Projektordner so aus:

  PFLICHT (vor dem Start vorhanden):
    OPT_V3_API_Chunking_Ansatz.py         → Das Hauptskript
    INCOSE_REGELWERK.py                    → Die 42 INCOSE-Regeln
    .env                                   → Deine API-Zugangsdaten
    Pflichtenheft.pdf  (o.ä. Name)        → Das zu analysierende PDF

  AUTOMATISCH ERZEUGT (nach dem Start):
    .venv/                                 → Deine virtuelle Umgebung
    checkpoint_iso29148.json               → Absturzsicherung (Fortschritt)
    ISO_29148_Requirements_Ergebnis.xlsx   → Dein fertiges Ergebnis


=============================================================================
KURZ-REFERENZ: WICHTIGSTE BEFEHLE AUF EINEN BLICK
=============================================================================

  venv erstellen:       py -3.11 -m venv .venv
  venv aktivieren:      .\.venv\Scripts\activate          (Windows)
                        source .venv/bin/activate          (macOS/Linux)
  Pakete installieren:  pip install PyMuPDF pandas tqdm openai spacy pdfplumber openpyxl python-dotenv
  Sprachmodell laden:   python -m spacy download de_core_news_sm
  Skript starten:       python OPT_V3_API_Chunking_Ansatz.py

=============================================================================
ENDE DER DOKUMENTATION
=============================================================================