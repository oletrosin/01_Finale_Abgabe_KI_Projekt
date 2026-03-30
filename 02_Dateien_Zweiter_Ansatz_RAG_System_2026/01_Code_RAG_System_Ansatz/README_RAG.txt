=============================================================================
DETAILLIERTE DOKUMENTATION: ISO 29148 / INCOSE REQUIREMENT PIPELINE V2 (RAG)
=============================================================================

Dieses Dokument dient als umfassendes Handbuch für die Implementierung, den
Betrieb und die technologische Architektur des "ISO 29148 / INCOSE Requirement
Pipeline" Skripts. Die Lösung stellt ein hochmodernes System zur automatisierten
Anforderungsextraktion dar, das auf der Kombination von Retrieval-Augmented
Generation (RAG), Computer Vision und iterativen KI-Prüfzyklen basiert.

Zielgruppe: Systems Engineers, Data Scientists und Python-Entwickler, die eine
revisionssichere Überführung von unstrukturierten Lastenheften in normative
Anforderungsdatenbanken anstreben.
============================================================================= 
TEIL A: ARCHITEKTUR UND TECHNOLOGISCHER STACK
=============================================================================

Die Pipeline ist nicht lediglich ein Skript, sondern ein verteiltes System,
das lokale Rechenleistung (für Embeddings und PDF-Parsing) mit hochperformanten
Cloud-Sprachmodellen (LLMs) kombiniert.

--------------------------------------------------
A.1  Kernkomponenten des Systems
--------------------------------------------------

    Multimodales Parsing: Nutzung von PyMuPDF (fitz) für Text, pdfplumber
    für Tabellenstrukturen und Qwen-VL (Vision-Language Model) für Skizzen.

    Vektordatenbank (FAISS): Ein lokaler In-Memory-Index, der semantische
    Vektoren speichert, um eine blitzschnelle Ähnlichkeitssuche zu      
    ermöglichen.

    NLP-Engine (spaCy): Einsatz des "de_core_news_sm" Modells zur
    grammatikalisch korrekten Zerlegung von komplexen deutschen Sätzen.

    Orchestrierung (LLMRequestManager): Eine Eigenentwicklung zur
    Steuerung der API-Last (Throttling) und zur Sicherstellung der
    Resilienz gegen Netzwerkfehler.

    Qualitätssicherung (Critic-Loop): Ein Multi-Agenten-System, bei dem
    ein "Generator-Modell" Anforderungen erstellt und ein "Critic-Modell"
    diese gegen 42 INCOSE-Regeln validiert.

--------------------------------------------------
A.2  Voraussetzungen und Umgebung (Setup)
--------------------------------------------------

Bevor die Pipeline gestartet werden kann, muss die Laufzeitumgebung
präzise konfiguriert werden.

Schritt 1: Python-Basis
Empfohlen wird Python 3.11. Höhere Versionen sind kompatibel, 3.11 bietet
jedoch die stabilste Unterstützung für die Vektordatenbank-Bibliotheken.

Schritt 2: Virtuelle Umgebung (Best Practice)
Um Abhängigkeitskonflikte zu vermeiden, führen Sie folgende Befehle aus:

py -3.11 -m venv .venv
.\.venv\Scripts\activate (Windows)
source .venv/bin/activate (Linux/Mac)

Schritt 3: Installation der High-Level Bibliotheken
Die Installation umfasst Pakete für Datenverarbeitung, KI-Schnittstellen
und mathematische Operationen:

pip install pandas numpy faiss-cpu PyMuPDF pdfplumber 
pip install tqdm openpyxl spacy sentence-transformers openai

Schritt 4: Download der Sprachressourcen
Ohne das lokale Sprachmodell kann spaCy keine Satzgrenzen erkennen:

python -m spacy download de_core_news_sm

--------------------------------------------------
A.3  Konfiguration der API-Schnittstellen
--------------------------------------------------

Der Code verwendet die OpenAI-kompatible Schnittstelle der Academic Cloud.
Die Konfiguration erfolgt im Abschnitt CONFIG:

    API_KEY: Ihr individueller Token.

    API_BASE: Die Endpunkt-URL (Default: https://www.google.com/search?q=https://chat-ai.academiccloud.de/v1).

    MODEL: Das primäre Modell für die Generierung (Llama-3.1-SauerkrautLM).

    VISION_MODEL: Das Modell zur Bildanalyse (Qwen3-VL).

    CRITIC_MODEL: Das Modell für die strikte Regelprüfung (Llama-3.3-70B).

============================================================================= 
TEIL B: FUNKTIONSWEISE DER MODULE (STEP-BY-STEP)
=============================================================================

In diesem Abschnitt wird die logische Kette des Programmcodes analysiert,
vom ersten Byte des PDFs bis zur finalen Excel-Zelle.

--------------------------------------------------
B.1  Multimodale Extraktion (The "Eyes" of the System)
--------------------------------------------------

Das Skript verfolgt einen dreigleisigen Ansatz bei der Datenakquise:

1. Text-Extraktion:
Das PDF wird nicht als reiner Stream gelesen, sondern blockweise analysiert.
Dabei werden Trennstriche am Zeilenende ("- \n") entfernt und mehrfache
Leerzeichen normalisiert. Dies stellt sicher, dass Wörter wie "Sicherheits-
einrichtung" korrekt als ein Wort erkannt werden.

2. Tabellen-Transformation:
Tabellen sind für KIs oft schwer zu interpretieren, wenn sie als flacher
Text eingelesen werden. pdfplumber erkennt die Zellstrukturen. Das Skript
iteriert durch jede Zeile und baut einen künstlichen Satz:
"Spezifikation aus Tabelle: Merkmal [Header] ist [Wert]".
Dadurch versteht die KI die Relation der Daten.

3. Vision-Analyse (Computer Vision):
Dies ist das Alleinstellungsmerkmal der Version 2. Jede PDF-Seite wird
gerendert (150 DPI) und als Base64-Bild an das Qwen-VL Modell gesendet.
Die KI sucht nach technischen Zeichnungen und extrahiert Maße (z.B.
Abstände, Radien, Toleranzen), die im Text oft fehlen, aber für die
Anforderungsdefinition kritisch sind.

--------------------------------------------------
B.2  Semantisches Chunking & Kontext-Fenster
--------------------------------------------------

Nachdem die Rohdaten vorliegen, müssen sie in verarbeitbare Stücke
("Chunks") zerlegt werden.

    Atomares Chunking: Das System nutzt spaCy, um Sätze zu identifizieren.
    Dabei werden Abkürzungen wie "DIN EN" geschützt, damit der Satz nicht
    fälschlicherweise am Punkt getrennt wird.

    Sliding Window Kontext: Um die Bedeutung zu erhalten (Traceability),
    wird jedem Chunk der Text der vorangegangenen drei Sätze angehängt.
    Wenn im Chunk steht "Es muss 5 kg wiegen", weiß die KI durch den Kontext
    davor, dass "Es" sich auf das "Steuergerät X" bezieht.

--------------------------------------------------
B.3  Retrieval-Augmented Generation (RAG)
--------------------------------------------------

Die Pipeline arbeitet themenbasiert (TOPICS). Für jedes Thema (z.B. GEOMETRIE)
und jedes Keyword (z.B. "Abmessungen") führt das System eine Vektorsuche durch.

    Embedding: Der Suchbegriff wird in einen 384-dimensionalen Vektor
    umgewandelt.

    FAISS-Search: Das System findet die Top-15 Textstellen im Dokument,
    die mathematisch am nächsten am Suchbegriff liegen.

    Knowledge-Injection: Diese Textstellen werden zusammen mit einem
    strengen System-Prompt an das LLM gesendet. Das LLM agiert nun als
    "Requirements Engineer" und darf nur Informationen nutzen, die
    tatsächlich im Kontext stehen (Halluzinations-Schutz).

--------------------------------------------------
B.4  Der iterative Qualitäts-Loop (INCOSE Critic)
--------------------------------------------------

Eine Besonderheit dieses Skripts ist der integrierte Feedback-Mechanismus:

    Generierung: Eine Anforderung wird erstellt.

    Audit: Das Critic-Modell lädt die 42 INCOSE-Regeln (z.B. Vermeidung
    von Passiv, Eindeutigkeit, Messbarkeit).

    Bewertung: Jede Regel wird mit "erfüllt", "nicht erfüllt" oder
    "nicht beurteilbar" gelabelt.

    Verbesserung: Falls Regeln verletzt wurden, wird die Anforderung
    automatisch mit dem Hinweis auf die spezifischen Fehler zur
    Überarbeitung zurückgegeben. Dieser Prozess wiederholt sich bis zu
    dreimal, bis die Qualität optimal ist.

--------------------------------------------------
B.5  Verifikations-Engineering
--------------------------------------------------

Für jede bestätigte Anforderung wird ein Verifikationsschritt generiert.
Hierbei muss die KI entscheiden, welche der vier ISO-Kategorien greift:

    Inspection: Visuelle Prüfung.

    Analysis: Theoretische Berechnung/Simulation.

    Demonstration: Funktionsvorführung ohne Messung.

    Test: Quantitative Messung mit Instrumenten.

Das System nutzt hierfür ein zweites Validierungs-PDF als Referenz, um
sicherzustellen, dass die Testpläne Industriestandards entsprechen.

============================================================================= 
TEIL C: DATENSTRUKTUR DER AUSGABE (EXCEL)
=============================================================================

Die finale Excel-Datei ist so konzipiert, dass sie direkt in ALM-Tools
(wie Siemens Polarion oder IBM DOORS) importiert werden kann.

--------------------------------------------------
C.1  Spaltendefinitionen
--------------------------------------------------

Spalte	Inhalt	Nutzen
Hauptmerkmal	Thema (z.B. ENERGIE)	Filterung nach Fachbereichen
Keyword	Genutzter Suchbegriff	Nachvollziehbarkeit der Suche
Requirement	Die finale ISO-Anforderung	Normative Vorgabe ("Das System muss...")
Verifiz.-Methode	z.B. "Test"	Planung der QS-Phasen
Verifiz.-Plan	Schritt-für-Schritt Anleitung	Basis für Testprotokolle
INCOSE Bewertung	Gegeben / Nicht gegeben	Qualitätsindikator
Regel-Details	Erfüllte/Verletzte Regeln	Revisionssicherheit
Verwendete Chunks	Original-Textquelle + Seite	Beweislast/Traceability

--------------------------------------------------
C.2  Formatierung und Usability
--------------------------------------------------

Das Skript nutzt openpyxl, um die Excel-Datei nicht nur mit Daten zu
füllen, sondern auch optisch aufzubereiten:

    Automatischer Zeilenumbruch (Wrap Text).

    Fixierte Spaltenbreiten (35 Einheiten).

    Vertikale Ausrichtung am oberen Rand für bessere Lesbarkeit langer Texte.

============================================================================= 
TEIL D: FEHLERMANAGEMENT UND RESILIENZ
=============================================================================

Da KI-APIs instabil sein können oder strikten Limits unterliegen, enthält
das Skript Schutzmechanismen auf Unternehmensebene.

--------------------------------------------------
D.1  Der LLMRequestManager (Throttling)
--------------------------------------------------

Um den HTTP-Fehler 429 ("Too many requests") zu vermeiden, berechnet der
Manager ein Zeitintervall basierend auf den erlaubten Requests per Minute
(RPM). Jede Anfrage wird erst freigegeben, wenn das Zeitfenster offen ist.
Bei Kollisionen wird ein Thread-Lock verwendet, um Race-Conditions zu
vermeiden.

--------------------------------------------------
D.2  Exception Handling & JSON-Sanitizing
--------------------------------------------------

KI-Modelle neigen dazu, manchmal Erklärungen um das JSON herum zu schreiben
(z.B. "Hier ist das Ergebnis: { ... }"). Das Skript verwendet robuste
Parser-Logiken, die nur den JSON-Kern extrahieren. Schlägt dies fehl,
wird der Versuch protokolliert und die Pipeline läuft stabil weiter,
anstatt komplett abzubrechen.

--------------------------------------------------
D.3  Absturzsicherung (Checkpoints)
--------------------------------------------------

Die Pipeline verarbeitet die Themen sequenziell. Ergebnisse werden
kontinuierlich im Arbeitsspeicher gesammelt und am Ende atomar
geschrieben. Für extrem große Dokumente wird empfohlen, das Skript
über ein Logging-System zu überwachen, um im Falle eines Netzwerkabbruchs
den Fortschritt zu sehen.
============================================================================= 
TEIL E: ANWENDER-HINWEISE UND BEST PRACTICES
=============================================================================

Um die besten Ergebnisse zu erzielen, sollten Anwender folgende Punkte
beachten:

    PDF-Qualität: Das Skript kann zwar Bilder analysieren, aber
    hochwertige "Born-Digital" PDFs (direkt aus Word/LaTeX exportiert)
    liefern 30-40% präzisere Ergebnisse als eingescannte Dokumente.

    Regelwerk-Anpassung: Die Datei INCOSE_REGELWERK.py kann erweitert
    werden. Wenn Ihr Unternehmen spezifische Phrasen verbietet, fügen
    Sie diese dort als neue Regel hinzu.

    Modellwahl: Das SauerkrautLM ist hervorragend für deutsche
    Grammatik. Für die Logikprüfung (Critic) ist jedoch das Llama-3.3-70B
    Modell aufgrund seiner höheren Parameteranzahl überlegen.

    Hardware: Da die Embeddings lokal berechnet werden, profitiert das
    Skript von einer CPU mit vielen Kernen. Eine GPU ist nicht zwingend
    erforderlich, da die "schwere" KI-Arbeit in der Cloud stattfindet.

============================================================================= 
ZUSAMMENFASSUNG DER DATEIEN IM PROJEKT
=============================================================================

    HAUPTSKRIPT: Enthält die RAG-Logik, FAISS-Indexierung und Main-Loop.

    INCOSE_REGELWERK.py: Wissensdatenbank der 42 Prüfregeln.

    V2_Pflichtenheft.pdf: Die primäre Datenquelle (Eingabe).

    Validierungs_Referenz.pdf: Basis für die Verifikationsplanung.

    ISO_29148_Ergebnis.xlsx: Das generierte Endprodukt.

    .venv/: Isolierte Umgebung mit allen Treibern.

============================================================================= 
ENDE DER DOKUMENTATION
=============================================================================