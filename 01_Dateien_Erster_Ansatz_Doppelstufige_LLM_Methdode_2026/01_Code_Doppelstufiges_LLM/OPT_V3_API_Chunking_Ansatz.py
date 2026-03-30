"""
ISO / INCOSE Anforderungsextraktion – Prozesskette V1 (NORMATIV, DEUTSCH)

Eigenschaften:
- Chunking des Textes
- Vollständige ISO 29148 / INCOSE Regelbasis (normativ referenziert)
- Explizite Behandlung fehlender Informationen
- Chunk-Traceability
- Excel-Ausgabe
"""

# =========================
# 1. Imports
# =========================

import os
import uuid
import json
import re
import time
from typing import List, Dict

import fitz  # PyMuPDF
import pandas as pd
from tqdm import tqdm
from openai import OpenAI

# Lade das externe INCOSE-Regelwerk
try:
    from INCOSE_REGELWERK import INCOSE_RULES
except ImportError:
    print("WARNUNG: INCOSE_REGELWERK.py nicht gefunden. Bitte sicherstellen, dass die Datei existiert.")
    INCOSE_RULES = {}

import spacy

# --- NEU: spaCy Sprachmodell laden ---
try:
    nlp = spacy.load("de_core_news_sm")
except OSError:
    print("FEHLER: Das deutsche spaCy Modell fehlt. Bitte führe in der Konsole aus:")
    print("python -m spacy download de_core_news_sm")
    exit(1)
# -------------------------------------

import base64
import pdfplumber # <-- NEU für Tabellen

# =========================
# 2. Konfiguration
# =========================

import os
from openai import OpenAI
from dotenv import load_dotenv

# Lade die Variablen aus der .env Datei
load_dotenv()

# SAIA / Academic Cloud API Setup (Werte kommen jetzt aus der .env)
# Variablen auslesen (mit leerem String als Fallback, damit Pylance nicht meckert)
API_KEY = os.getenv("SAIA_API_KEY", "")
API_BASE = os.getenv("SAIA_API_BASE", "")
PDF_INPUT = os.getenv("TARGET_PDF", "")

# --- MAX_CHUNKS aus der .env laden ---
try:
    MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", 150))
except ValueError:
    print("Warnung: MAX_CHUNKS in der .env ist ungültig. Setze Limit auf 150.")
    MAX_CHUNKS = 150
# ------------------------------------------

# --- Sicherheits-Check ---
if not API_KEY or not API_BASE or not PDF_INPUT:
    raise ValueError("Fehler: API_KEY, API_BASE oder PDF_INPUT fehlen in der .env Datei!")
# -------------------------

# Initialisierung des Clients mit dem spezifischen Endpunkt
client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE
)

OUTPUT_EXCEL = "ISO_29148_Requirements_Ergebnis.xlsx"
CHECKPOINT_FILE = "checkpoint_iso29148.json"

# Modelle der SAIA-Plattform
GENERATOR_MODEL = "llama-3.1-sauerkrautlm-70b-instruct"    # Für die Anforderungsextraktion
CRITIC_MODEL = "llama-3.3-70b-instruct"       # Für die komplexe Regelprüfung
VISION_MODEL = "qwen3-vl-30b-a3b-instruct" # Wird zur detaillierten Analyse von Skizzen, Abbildungen und Tabellen eingesetzt.

LLM_OPTIONS = {
    "temperature": 0.0,
    "top_p": 1.0,
    # HINWEIS ZUM JSON-MODUS:
    # Falls die Academic Cloud bei diesen Open-Source-Modellen einen Fehler bezüglich 
    # "response_format" auswirft, kommentiere die folgende Zeile einfach aus. 
    # Die Modelle sind im Prompt ohnehin auf STRICT JSON instruiert.
    "response_format": { "type": "json_object" } 
}

# =========================
# 3. Multimodales PDF Parsing (Text, Tabellen & Skizzen)
# =========================

def describe_sketches_on_page(pixmap_bytes: bytes) -> str:
    """Sendet ein Seitenbild an Qwen VL, um bemaßte Skizzen und Zeichnungen auszulesen."""
    base64_image = base64.b64encode(pixmap_bytes).decode('utf-8')
    
    # Prompt, der Qwen zwingt, nur die Zeichnungen zu beachten (vermeidet Text-Duplikate)
    prompt = (
        "Du bist ein technischer Requirements Engineer. Analysiere das angehängte Bild einer PDF-Seite. "
        "Finde ALLE technischen Skizzen, Diagramme und Risszeichnungen. "
        "Extrahiere daraus ausschließlich die physikalischen Maße und technischen Werte des dargestellten Bauteils. "
        "WICHTIG: Beschreibe NIEMALS die Zeichnung selbst (vermeide Wörter wie 'Skizze', 'Zeile', 'Skala', 'Achse', 'Linie'). "
        "Formuliere nur die harten Fakten über das System (z.B. 'Der Abstand zwischen den Stützen beträgt 120 cm'). "
        "Ignoriere normalen Fließtext! Antworte nur, wenn Skizzen vorhanden sind, ansonsten antworte mit 'LEER'."
    )
    
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            temperature=0.0,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        # FIX 1: Prüfen, ob der Inhalt leer ist (Behebt den .strip() Pylance-Fehler)
        if not content:
            return ""
            
        result = content.strip()
        
        if "LEER" in result or len(result) < 15:
            return ""
        return result
        
    except Exception as e:
        print(f"Warnung: Fehler bei der Vision-API (Qwen): {e}")
        return ""

def load_pdf_text(path: str) -> List[Dict]:
    doc = fitz.open(path)
    blocks = []
    
    current_chapter = "Allgemeines Dokument" # <-- NEU: Merkt sich das aktuelle Kapitel
    
    # Öffne pdfplumber einmal für das gesamte Dokument (für Tabellen)
    with pdfplumber.open(path) as pb_doc:
        
        # FIX 2: Zählen über range statt doc direkt (Behebt den tqdm Pylance-Fehler)
        for page_num in tqdm(range(len(doc)), desc="PDF Auslesen (Multimodal)"):
            page = doc[page_num]
            real_page = page_num + 1  # Für den Menschen lesbare Seitenzahl (1-basiert)
            
            # --- 1. NORMALEN TEXT EXTRAHIEREN ---
            for block_index, block in enumerate(page.get_text("blocks")):
                text = block[4].strip()
                # Text-Bereinigung
                text = re.sub(r'-\n\s*', '', text)
                text = text.replace('\n', ' ')
                text = re.sub(r'\s{2,}', ' ', text).strip()
                
             # --- NEU & HOCHPRÄZISE: Kapitel-Erkennung (Nummeriert & Zeilenweise) ---
                # Wir zerlegen den Block in einzelne Zeilen. Das verhindert, dass Kapitel 
                # verschluckt werden, falls das PDF sie mit dem Fließtext darunter verklebt hat.
                for line in text.split('\n'):
                    line_clean = line.strip()
                    
                    # REGEX-Magie: Sucht nach echten ISO-Kapiteln (z.B. "4.1.1.1 Kapazität" oder "3. System")
                    # ^\d+       = Startet zwingend mit einer Zahl
                    # (?:\.\d+)* = Optional weitere Punkte und Zahlen (wie .1.1)
                    # \s+        = Gefolgt von mindestens einem Leerzeichen
                    # [A-ZÄÖÜ]   = Das erste Wort MUSS mit einem Großbuchstaben beginnen!
                    if re.match(r'^\d+(?:\.\d+)*\s+[A-ZÄÖÜ]', line_clean):
                        
                        # Sicherheits-Check: Nicht zu lang und endet nicht auf einen Zuweisungs-Doppelpunkt
                        if len(line_clean) <= 100 and not line_clean.endswith((':', '?', '!')):
                            current_chapter = line_clean
                            break  # Kapitel gefunden! Restliche Zeilen im Block ignorieren.
                 # -----------------------------------------------------------------------    

                # Wir prüfen, ob der Text reiner Müll ist (z.B. nur eine isolierte Seitenzahl)
                is_pure_junk = text.strip().isdigit()

                if len(text) > 20 and not is_pure_junk:
                    blocks.append({
                        "text": text,
                        "page": real_page,
                        "location_detail": f"Fließtext (Abschnitt {block_index + 1})",
                        "chapter": current_chapter # <-- NEU: Kapitel-Stempel aufdrücken
                    })

            # --- 2. TABELLEN EXTRAHIEREN (pdfplumber) ---
            pb_page = pb_doc.pages[page_num]
            tables = pb_page.extract_tables()
            for table_idx, table in enumerate(tables):
                cleaned_table = [[str(cell).replace('\n', ' ').strip() if cell is not None else "" for cell in row] for row in table]
                
                if cleaned_table and len(cleaned_table) > 1:
                    # 1. Erste Zeile als Überschriften (Header) definieren
                    headers = cleaned_table[0]
                    
                    # 2. Ab der zweiten Zeile Werte mit Überschriften verknüpfen
                    for row_idx, row in enumerate(cleaned_table[1:]):
                        if not any(row): # Leere Zeilen überspringen
                            continue
                            
                        row_statements = []
                        for i, cell_value in enumerate(row):
                            if cell_value and i < len(headers):
                                header_name = headers[i]
                                if header_name:
                                    row_statements.append(f"{header_name} ist {cell_value}")
                                else:
                                    row_statements.append(cell_value)
                        
                        # 3. Wenn Daten da sind, einen zusammenhängenden Satz daraus bauen!
                        if row_statements:
                            sentence = f"Spezifikation aus Tabelle (Seite {real_page}) - Für das Bauteil oder System gilt - " + ", ".join(row_statements) + "."
                            blocks.append({
                                "text": sentence,
                                "page": real_page,
                                "location_detail": f"Tabelle {table_idx + 1}, Datenzeile {row_idx + 1}",
                                "chapter": current_chapter # <-- NEU
                            })

            # --- 3. SKIZZEN EXTRAHIEREN (Qwen VL) ---
            # Wir rendern die Seite als Bild (dpi=150 reicht für Zahlen gut aus)
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            
            # Hole Beschreibung der Skizzen
            vision_description = describe_sketches_on_page(img_bytes)
            if vision_description:
                blocks.append({
                    "text": f"Zusätzliche Informationen aus Skizzen (Seite {real_page}) - {vision_description}",
                    "page": real_page,
                    "location_detail": "Bemaßte Skizze / Zeichnung",
                    "chapter": current_chapter # <-- NEU
                })

    return blocks

# =========================
# 4. Chunking
# =========================

# =========================
# 4.1 Chunking Ansatz und Trennungsstrategie
# =========================

def iso_atomic_chunk_text(text: str) -> List[str]:
    """
    Erzeugt kontextbewahrende Chunks mithilfe von NLP (spaCy):
    - Trennt semantisch korrekt nach Sätzen (erkennt Satzstrukturen).
    - Ignoriert Abkürzungen (z. B., bzw., etc.), Normen (DIN EN) und Dezimalzahlen.
    """
    doc = nlp(text)
    valid_chunks = []

    for sent in doc.sents:
        sentence = sent.text.strip()

        # Zu kurze Fragmente verwerfen (z.B. Seitenzahlen oder Artefakte)
        if len(sentence) < 20:
            continue
        
        valid_chunks.append(sentence)

    return valid_chunks

# =========================
# 4.2 ISO‑konforme Chunk-Erzeugung mit Traceability
# =========================

def create_chunks(sections: List[Dict]) -> List[Dict]:
    """
    Erzeugt nachvollziehbare ISO-Chunks.
    Nutzt ein "Sliding Window" für Fließtext, ignoriert dieses aber bei harten Tabellen-/Skizzendaten.
    Reicht Metadaten (Seite, Ort) verlustfrei an die Ausgabe weiter.
    """
    chunks: List[Dict] = []
    seen_chunks = set()
    
    last_valid_context = "Allgemeine Systembeschreibung"
    
    # NEU: Ein kleiner Zwischenspeicher für die letzten 3 normalen Text-Chunks
    recent_text_window = []

    for section_index, section_data in enumerate(sections):
        # Daten aus dem Dictionary entpacken
        raw_text = section_data["text"]
        page_num = section_data["page"]
        loc_detail = section_data["location_detail"]
        chapter_name = section_data.get("chapter", "Unbekannt") # <-- NEU: Kapitel abrufen
        
        atomic_chunks = iso_atomic_chunk_text(raw_text)
        current_context = raw_text.strip()
        
        if len(current_context) < 15:
            current_context = last_valid_context
        else:
            last_valid_context = current_context

        # Prüfen, ob der Block aus Tabellen oder Skizzen (Qwen) stammt
        is_technical_data = "Spezifikation aus Tabelle" in current_context or "Zusätzliche Informationen aus Skizzen" in current_context

        for chunk_index, chunk in enumerate(atomic_chunks):
            normalized_chunk = re.sub(r'\s+', ' ', chunk.strip()).lower()
            
            # Signatur zur Duplikatsprüfung
            unique_signature = f"{current_context} || {normalized_chunk}"
            if unique_signature in seen_chunks:
                continue 
            seen_chunks.add(unique_signature)

            # --- Dynamische Kontext-Zuweisung inkl. Kapitel ---
            if is_technical_data:
                # Bei Skizzen und Tabellen: Nur den direkten Satz als Kontext nehmen (kein Sliding Window)
                final_context = f"Übergeordnetes Kapitel: {chapter_name} - Aktuelle Daten: {current_context}"
            else:
                # Bei normalem Fließtext: Letzte 3 Sätze + den aktuellen Absatz als Kontext nehmen
                if recent_text_window:
                    window_text = " ".join(recent_text_window)
                    final_context = f"Übergeordnetes Kapitel: {chapter_name} - Letzte Sätze davor: {window_text} - Aktueller Absatz: {current_context}"
                else:
                    final_context = f"Übergeordnetes Kapitel: {chapter_name} - Aktueller Absatz: {current_context}"
                
                # Den aktuellen Chunk für die nächsten Sätze merken (maximal 3 speichern)
                recent_text_window.append(chunk)
                if len(recent_text_window) > 3:
                    recent_text_window.pop(0)
            # -----------------------------------------

            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "source_section": section_index,
                "chunk_index": chunk_index,
                "chunk_text": chunk,
                "context_text": final_context, # Hier wird der dynamische Kontext übergeben
                "page": page_num,              # Metadaten durchreichen
                "location_detail": loc_detail, # Metadaten durchreichen
                "chapter": chapter_name        # <-- NEU: Durchreichen für Excel
            })

    return chunks

# =========================
# 5. ISO‑Anforderungserzeugung (NORMATIV!)
# =========================

def llm_generate_requirements(chunk_text: str, max_retries=5) -> List[str]:
    prompt = f"""
Du agierst ausschließlich als normativ arbeitender Requirements Engineer
gemäß ISO/IEC/IEEE 29148:2018 und dem INCOSE Guide for Writing Requirements.

==============================
NORMATIVE BASIS (VERBINDLICH)
==============================
- ISO/IEC/IEEE 29148:2018
- INCOSE Guide for Writing Requirements
- Keine Abweichungen erlaubt

==============================
GRUNDSÄTZLICHE REGELN & ZERO-HALLUCINATION-POLICY
==============================
- KEINE kreativen Ergänzungen
- KEINE impliziten Annahmen
- KEINE Interpretation über den Text hinaus
- ABSOLUTES VERBOT von Halluzinationen!
- Verwende ausschließlich Informationen aus dem Eingabetext.

Wenn der Eingabetext nicht ausreicht, um eine normkonforme Anforderung
abzuleiten, MUSS exakt folgende Ausgabe in das Array geschrieben werden:
"Nicht genügend Information zur Ableitung einer ISO-konformen Anforderung."

==============================
ZIEL & VERARBEITUNG DES EINGABETEXTES (STRIKTE TRENNUNG)
==============================
Du erhältst im Eingabetext zwei Bereiche: "KONTEXT" und "EIGENTLICHE AUSSAGE".
Hier gilt eine strikte Firewall:
1. Die "EIGENTLICHE AUSSAGE" ist deine EINZIGE zulässige Datenquelle für Fakten, Maße, Zahlen und technische Eigenschaften der Anforderung. Formuliere die normative Anforderung NUR aus diesen Daten.
2. Den "KONTEXT" darfst du AUSSCHLIESSLICH nutzen, um herauszufinden, zu welchem übergeordneten Bauteil, Regal oder System die Maße/Werte gehören (z.B. um das Subjekt im Satz korrekt zu benennen).
3. DATEN-VERBOT: Du darfst unter keinen Umständen Zahlen, Spezifikationen oder Vorgaben aus dem "KONTEXT" in die Anforderung übernehmen.
4. ABLEHNUNGS-TRIGGER: Wenn die "EIGENTLICHE AUSSAGE" nur aus Metatext, Referenzen oder Überschriften besteht (z.B. "Spezifikation aus Tabelle:", "Seite 2", "Zeile 6 zeigt") und selbst KEINE konkreten technischen Werte enthält, falls sie also absolut nicht ausreicht, lehne zwingend ab.

==============================
VERBINDLICHE ANFORDERUNGSKRITERIEN (VERSCHÄRFT)
==============================
1. NOTWENDIG: Beschreibt eine notwendige Eigenschaft/Funktion.
2. ABSTRAKT: Beschreibe WAS gefordert ist, NICHT WIE.
3. EINDEUTIG: Absolute Klarheit. Wenn der Text vage Wörter enthält (z.B. "hoch", "schnell", "ausreichend", "benutzerfreundlich") und diese nicht durch Zahlen belegt, MUSS die Anforderung abgelehnt werden.
4. VOLLSTÄNDIG: Ohne weitere Kontextinformationen verständlich. Das grammatikalische Subjekt MUSS immer das System oder das konkrete Bauteil sein (z.B. "Das Regal", "Die Bühne", "Das System"). Nutze den mitgelieferten "KONTEXT", um das richtige Bauteil im Satz zu benennen (z.B. "Das Regal Typ A muss..."). Niemals darf eine physikalische Eigenschaft (wie "Die Ebene", "Die Höhe") das alleinige Subjekt sein.
5. ATOMAR: Eine Anforderung darf nur einen logischen Systemzustand beschreiben. ABER: Zusammengehörige physikalische Parameter (z.B. Länge, Breite, Höhe) EINES Bauteils oder EINER Systemebene DÜRFEN UND SOLLEN in einer einzigen Anforderung zusammengefasst werden, damit der Kontext erhalten bleibt. Zerschneide keine zusammengehörigen Maße aus Tabellen!
6. UMSETZBAR: Realistisch und widerspruchsfrei.
7. VERIFIZIERBAR: Die Anforderung muss objektiv testbar sein (Pass/Fail). Fehlt ein konkreter Wert, ein Maß oder ein klarer Zustand im Text, lehne ab.
8. REFERENZEN (KONFORMITÄT): Normen (z.B. DIN, ISO, EN) MÜSSEN in den Satz übernommen werden.
9. SYSTEMFOKUS: Anforderungen gelten AUSSCHLIESSLICH für das zu bauende System. Lehne jeden Satz ab, der das Aussehen des Dokuments, der Tabelle oder der Skizze beschreibt (z.B. "Die Skizze muss...", "Zeile 6 muss...", "Die Tabelle zeigt...").

==============================
BEISPIELE FÜR DIE TRANSFORMATION & ABLEHNUNG
==============================
EINGABE: 
KONTEXT: Spezifikation für Regal Typ A. (Länge: 200mm)
EIGENTLICHE AUSSAGE: Die Breite der einzelnen Fächer beträgt 100 mm.
AUSGABE: {{"requirements": ["Die Fächer des Regals Typ A müssen eine Breite von 100 mm aufweisen."]}}

EINGABE:
KONTEXT: Allgemeine Systemdaten, Höhe 1110 mm
EIGENTLICHE AUSSAGE: Spezifikation aus Tabelle (Seite 2) -
AUSGABE: {{"requirements": ["Nicht genügend Information zur Ableitung einer ISO-konformen Anforderung."]}}
(Erklärung: Abgelehnt, da die eigentliche Aussage nur ein Verweis ist. Die Daten aus dem Kontext dürfen nicht genutzt werden!)

EINGABE:
KONTEXT: Allgemeine Systemdaten
EIGENTLICHE AUSSAGE: Spezifikation aus Tabelle: Für das Bauteil/System gilt: Ebene ist 1, Lichte Höhe ist 1110 mm.
AUSGABE: {{"requirements": ["Das Bauteil in Ebene 1 muss eine lichte Höhe von 1.110 mm aufweisen."]}}

EINGABE:
KONTEXT: Zeichnungsbeschreibung
EIGENTLICHE AUSSAGE: Die Zeile 6 zeigt eine horizontale Skala mit Abständen von 120 cm.
AUSGABE: {{"requirements": ["Nicht genügend Information zur Ableitung einer ISO-konformen Anforderung."]}}

==============================
SPRACH- UND FORMALREGELN
==============================
- Sprache: Deutsch
- Aktivform
- Explizites verantwortliches Subjekt (z. B. "Das System", "Die Software", "Das Regal")
- Korrektes Modalverb (muss, soll, darf, kann)

==============================
AUSGABEFORMAT (STRICT JSON)
==============================
{{
  "requirements": [
    "Die formulierte Anforderung."
  ]
}}

==============================
EINGABETEXT
==============================
\"\"\"
{chunk_text}
\"\"\"
"""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GENERATOR_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLM_OPTIONS["temperature"],
                top_p=LLM_OPTIONS["top_p"],
                response_format=LLM_OPTIONS["response_format"]
            )
                    
            content = response.choices[0].message.content
            if not content:
                return ["Nicht genügend Information zur Ableitung einer ISO-konformen Anforderung."]
                
            result_json = json.loads(content)
            return result_json.get("requirements", ["Nicht genügend Information zur Ableitung einer ISO-konformen Anforderung."])
        
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg:
                wait_time = 4 * (attempt + 1)
                print(f"\nAPI Limit bei Generierung. Warte {wait_time} Sekunden...")
                time.sleep(wait_time)
            else:
                print(f"\nFehler bei der Generierung: {e}")
                return ["Nicht genügend Information zur Ableitung einer ISO-konformen Anforderung."]

    return ["Nicht genügend Information zur Ableitung einer ISO-konformen Anforderung."]

# =========================
# 6. ISO‑29148 / INCOSE Regelprüfung (VOLLSTÄNDIG)
# =========================

def llm_check_incose_compliance(requirement: str, max_retries=5) -> Dict:
    """
    Prüft eine einzelne Anforderung regelweise gegen das externe INCOSE-Regelwerk (R1-R42)
    und gibt die Ergebnisse ausschließlich in Kurzschreibweise zurück.
    """
    
    if not INCOSE_RULES:
        rules_formatted = "Keine Regeln geladen."
    else:
        rules_formatted = "\n".join(
            [f"{rule_id}: {rule.get('beschreibung', '')}" for rule_id, rule in INCOSE_RULES.items()]
        )

    prompt = f"""
Du bist ein unabhängiger INCOSE Requirements Auditor.

AUFGABE:
Bewerte die folgende Anforderung EXPLIZIT und EINZELN
gegen jede der aufgeführten INCOSE-Regeln (R1 bis R42).

BEWERTUNGSKATEGORIEN (pro Regel):
- "erfüllt"
- "nicht erfüllt"
- "nicht beurteilbar"

VORGABEN:
- KEINE Annahmen, KEINE Begründungen, KEINE zusätzlichen Regeln.
- Jede Regel MUSS bewertet werden.

AUSGABEFORMAT (STRICT JSON):
{{
  "R1": "erfüllt | nicht erfüllt | nicht beurteilbar",
  "R2": "erfüllt | nicht erfüllt | nicht beurteilbar",
  "...": "..."
}}

INCOSE-REGELN:
{rules_formatted}

ANFORDERUNG:
\"\"\"
{requirement}
\"\"\"
"""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=CRITIC_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLM_OPTIONS["temperature"],
                top_p=LLM_OPTIONS["top_p"],
                response_format=LLM_OPTIONS["response_format"]
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Die API hat eine leere Antwort zurückgegeben.")

            rule_results = json.loads(content)

            # Ergebnisse sammeln (Kurzschreibweise)
            erfuellt: List[str] = []
            nicht_erfuellt: List[str] = []
            nicht_beurteilbar: List[str] = []

            for rule_id, status in rule_results.items():
                if status == "erfüllt":
                    erfuellt.append(rule_id)
                elif status == "nicht erfüllt":
                    nicht_erfuellt.append(rule_id)
                else:
                    nicht_beurteilbar.append(rule_id)

            overall_status = (
                "perfekt formuliert"
                if len(nicht_erfuellt) == 0
                else "nicht perfekt formuliert"
            )

            return {
                "requirement": requirement,
                "overall_status": overall_status,
                "erfuellt": sorted(erfuellt),
                "nicht_erfuellt": sorted(nicht_erfuellt),
                "nicht_beurteilbar": sorted(nicht_beurteilbar)
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg:
                wait_time = 4 * (attempt + 1)
                print(f"\nAPI Limit bei Regelprüfung. Warte {wait_time} Sekunden...")
                time.sleep(wait_time)
            else:
                print(f"\nFehler bei der Validierung: {e}")
                return {
                    "requirement": requirement,
                    "overall_status": "Fehler bei der Prüfung",
                    "erfuellt": [],
                    "nicht_erfuellt": [],
                    "nicht_beurteilbar": []
                }

    return {
        "requirement": requirement,
        "overall_status": "API Timeout",
        "erfuellt": [],
        "nicht_erfuellt": [],
        "nicht_beurteilbar": []
    }

# =========================
# 6.5 Nachweismethode bestimmen (Inspektion, Analyse, Demonstration, Test)
# =========================

def llm_determine_verification_method(requirement: str, max_retries=5) -> Dict:
    """
    Klassifiziert eine Anforderung in eine der vier Nachweismethoden 
    gemäß den bereitgestellten Leitregeln (INCOSE/ISO 29148).
    Arbeitet streng deterministisch (Temperature = 0.0).
    """
    prompt = f"""
Du bist ein streng normativ arbeitender Requirements Engineer. 
Bestimme für die folgende Systemanforderung die am besten geeignete Nachweismethode (Verification Method).

Wähle AUSSCHLIESSLICH aus den folgenden exakt vier Kategorien (keine Abweichungen, keine Kombinationen):
1. Inspektion: Überprüfung von Eigenschaften, die insbes. durch visuelle Untersuchung und Beobachtung sichergestellt werden können (z. B. Farbe, Gewicht).
2. Analyse: Verwendung analytischer Modelle oder numerischer Simulationen, mit dem Ziel, eine theoretische Übereinstimmung nachzuweisen. Wird eingesetzt, wenn ein Nachweis unter realistischen Einschränkungen nicht erreicht werden kann oder nicht kosteneffizient ist.
3. Demonstration: (Qualitative) Vorführung der funktionalen Leistungsfähigkeit, welche üblicherweise ohne oder mit geringer Instrumentierung erreicht wird. Zeigt, dass das Produkt angemessen auf spezifische Stimuli reagiert. Ebenfalls angemessen für statistische Daten (z. B. durchschnittlicher Stromverbrauch).
4. Test: Handlung, durch welche die Betriebsfähigkeit, Instandsetzbarkeit oder Leistungsfähigkeit eines Produkts nachgewiesen werden, wenn dieses Produkt kontrollierten Bedingungen unterworfen wird, die real oder nachgebildet sein können. Nutzt häufig spezielles Gerät oder Instrumentierung, um genaue quantitative Daten für Analysen zu erhalten.

==============================
BEISPIELE FÜR DIE KLASSIFIZIERUNG
==============================
EINGABE: "Das System muss rot lackiert sein."
AUSGABE: {{"Nachweismethode": "Inspektion", "Begruendung": "Die Farbe kann durch einfache visuelle Beobachtung überprüft werden."}}

EINGABE: "Die Software muss bei 10.000 simulierten gleichzeitigen Zugriffen stabil laufen."
AUSGABE: {{"Nachweismethode": "Analyse", "Begruendung": "Ein Nachweis unter realen Einschränkungen ist schwer, daher wird hier eine Simulation/Analyse genutzt."}}

EINGABE: "Das Display muss sich bei Inaktivität nach 5 Minuten ausschalten."
AUSGABE: {{"Nachweismethode": "Demonstration", "Begruendung": "Dies ist eine qualitative Vorführung der funktionalen Leistungsfähigkeit ohne komplexe Instrumentierung."}}

EINGABE: "Die Reaktionszeit der Notbremse muss unter 200 Millisekunden liegen."
AUSGABE: {{"Nachweismethode": "Test", "Begruendung": "Erfordert kontrollierte Bedingungen und spezielle Instrumentierung, um genaue quantitative Daten zu erhalten."}}

==============================
AUSGABEFORMAT (STRICT JSON)
==============================
{{
  "Nachweismethode": "Inspektion | Analyse | Demonstration | Test",
  "Begruendung": "Kurze, präzise Begründung (max. 2 Sätze)."
}}

ANFORDERUNG:
\"\"\"
{requirement}
\"\"\"
"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GENERATOR_MODEL, 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0, 
                top_p=0.1,       
                response_format={"type": "json_object"} 
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Leere Antwort bei der Bestimmung der Nachweismethode.")

            return json.loads(content)
            
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg:
                wait_time = 4 * (attempt + 1)
                print(f"\nAPI Limit bei Nachweismethode. Warte {wait_time} Sekunden...")
                time.sleep(wait_time)
            else:
                print(f"\nFehler bei der Bestimmung der Nachweismethode: {e}")
                return {
                    "Nachweismethode": "Fehler",
                    "Begruendung": f"Konnte nicht ermittelt werden: {e}"
                }
                
    return {
        "Nachweismethode": "Fehler",
        "Begruendung": "API Timeout nach mehreren Versuchen."
    }


# =========================
# 7. Pipeline
# =========================

def run_pipeline() -> pd.DataFrame:
    sections = load_pdf_text(PDF_INPUT)
    chunks = create_chunks(sections)

    # Sicherheitslimit anwenden (MAX_CHUNKS kommt automatisch aus der .env-Datei, falls dort definiert)
    chunks = chunks[:MAX_CHUNKS]

    rows = []
    processed_chunk_ids = set()

    # Checkpoint laden
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            try:
                rows = json.load(f)
                processed_chunk_ids = {r["Chunk-ID"] for r in rows}
            except json.JSONDecodeError:
                print("Warnung: Checkpoint-Datei fehlerhaft, starte neu.")

    # Hauptverarbeitung
    for chunk in tqdm(chunks, desc="ISO-29148 Verarbeitung"):

        # Bereits verarbeitete Chunks überspringen
        if chunk["chunk_id"] in processed_chunk_ids:
            continue

        # --- NEU: Wir bauen den Text inkl. Kontext für das LLM zusammen ---
        # .get('context_text', '') sorgt dafür, dass alte Checkpoints nicht crashen, falls das Feld fehlt
        combined_text_for_llm = f"KONTEXT (Vorheriger Text im PDF zur Zuordnung):\n{chunk.get('context_text', '')}\n\nEIGENTLICHE AUSSAGE:\n{chunk['chunk_text']}"

        # Wir übergeben den kombinierten Text an den Generator
        requirements = llm_generate_requirements(combined_text_for_llm)

        for req in requirements:
            
            # Normative Ablehnung überspringen
            if req.strip().startswith("Nicht genügend Information"):
                rows.append({
                    "Chunk-ID": chunk["chunk_id"],
                    "Kapitelbezeichnung": chunk.get("chapter", "Unbekannt"), # <-- NEUE SPALTE
                    "Seitenangabe": chunk.get("page", "Unbekannt"),            
                    "Referenz": chunk.get("location_detail", "Unbekannt"), 
                    "Kontext": chunk.get("context_text", ""), 
                    "Original-Chunk-Text": chunk["chunk_text"],
                    "ISO-Anforderung": req,
                    "Finale ISO-Bewertung": "Abgelehnt (Nicht generierbar)",
                    "ISO-29148 / INCOSE Konformität": "nicht prüfbar (Ablehnung)",
                    "Empfohlene Nachweismethode": "-",
                    "Nachweis-Begründung": "-"
                })
                continue
         
            # INCOSE-Prüfung
            compliance = llm_check_incose_compliance(req)
            
            # Nachweismethode bestimmen
            verification = llm_determine_verification_method(req)

            rows.append({
                "Chunk-ID": chunk["chunk_id"],
                "Kapitelbezeichnung": chunk.get("chapter", "Unbekannt"), # <-- NEUE SPALTE
                "Seitenangabe": chunk.get("page", "Unbekannt"),            
                "Referenz": chunk.get("location_detail", "Unbekannt"), 
                "Kontext": chunk.get("context_text", ""), 
                "Original-Chunk-Text": chunk["chunk_text"],
                "ISO-Anforderung": req,
                "Finale ISO-Bewertung": compliance.get("overall_status", "Fehler"),
                "ISO-29148 / INCOSE Konformität": json.dumps(compliance, ensure_ascii=False),
                "Empfohlene Nachweismethode": verification.get("Nachweismethode", "Fehler"),
                "Nachweis-Begründung": verification.get("Begruendung", "Keine Begründung verfügbar.")
            })

        # Checkpoint NACH jedem Chunk (Robust gegen Windows-Dateisperren)
        temp_file = CHECKPOINT_FILE + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, CHECKPOINT_FILE)
        except Exception as e:
            # Falls Windows die Datei für eine Millisekunde sperrt, stürzt das Skript nicht mehr ab, 
            # sondern speichert einfach beim nächsten Chunk wieder.
            print(f"\nWarnung beim Speichern des Checkpoints: {e}")

    return pd.DataFrame(rows)


# =========================
# 8. Excel Export
# =========================

def export_to_excel(df: pd.DataFrame):
    df.to_excel(OUTPUT_EXCEL, index=False)

# =========================
# 9. Main
# =========================

def main():
    print("📄 Starte ISO-29148 Prozesskette (OpenAI, normativ, halluzinationsfrei) …")
    df = run_pipeline()
    export_to_excel(df)
    print(f"✅ Fertig: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()