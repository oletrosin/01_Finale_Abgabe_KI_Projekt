# ============================================================
# ISO 29148 / INCOSE REQUIREMENT PIPELINE (OPTIMIERT)
# ============================================================

import os
import json
import re
import uuid
import time
import threading
import base64
import concurrent.futures
from typing import List, Dict

import pandas as pd
import numpy as np
import faiss
import fitz
import pdfplumber
from tqdm import tqdm
from openpyxl.styles import Alignment

import spacy
# spaCy Modell laden - Vorher ggf. installieren: python -m spacy download de_core_news_sm
nlp = spacy.load("de_core_news_sm")

from sentence_transformers import SentenceTransformer
from openai import OpenAI


# ============================================================
# INCOSE RULE IMPORT
# ============================================================

try:
    from INCOSE_REGELWERK import INCOSE_RULES
except ImportError:
    print("WARNUNG: INCOSE_REGELWERK.py nicht gefunden. Nutze leeres Regelwerk.")
    INCOSE_RULES = {}

def build_incose_rule_text():
    lines = []
    for rid, rule in INCOSE_RULES.items():
        titel = rule.get("titel", "")
        beschreibung = rule.get("beschreibung", "")
        lines.append(f"{rid}: {titel} – {beschreibung}")
    return "\n".join(lines)

INCOSE_RULE_TEXT = build_incose_rule_text()


# ============================================================
# CONFIG
# ============================================================

# SICHERHEIT: API Key niemals im Code hartcodieren! Bitte den eigenen API Key nutzen.
API_KEY = #"Ihren individuellen Token einfügen."
API_BASE = #"Die Endpunkt-URL (Default: https://www.google.com/search?q=https://chat-ai.academiccloud.de/v1)"

MODEL = "llama-3.1-sauerkrautlm-70b-instruct"
VISION_MODEL = "qwen3-vl-30b-a3b-instruct"
CRITIC_MODEL = "llama-3.3-70b-instruct"

PDF_INPUT = "V2_Pflichtenheft_komprimiert.pdf"
PDF_VALIDATION = "Erklärung_Analyse_Inspektion_Test_Demonstration_260208_210650.PDF"

OUTPUT_EXCEL = "ISO_29148_Requirements_Ergebnis.xlsx"

LLM_OPTIONS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "response_format": {"type": "json_object"}
}

client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE
)


# ============================================================
# TOPICS
# ============================================================

TOPICS = {
    "GEOMETRIE": ["Abmessungen Ladehilfsmittel", "max. Ladungsgrößen", "max. Höhe der Transporteinheiten", "Gassen-/AST-Maße"],
    "KINEMATIK": ["Stabilität der Ladegüter", "Max. Fahrgeschwindigkeit", "Anforderungen an Bewegungsabläufe"],
    "KRÄFTE": ["max. Gewicht der Transporteinheiten", "Resttragfähigkeit des Fahrzeugs", "Durchbiegung"],
    "ENERGIE": ["Batteriespannung", "Ersatzstromanlage", "Schutzarten"],
    "STOFF": ["Material und Produktspezifikationen"],
    "SIGNAL": ["Schnittstellen", "Scan und Identifikationen"],
    "SICHERHEIT": ["Brandschutz", "Ausrüstung", "Lichtverhältnisse", "Notstrom"],
    "ERGONOMIE": ["Bediengeräte", "Wartungsbereiche"],
    "KONTROLLE": ["Qualifizierung und Normen", "Detektionseinheiten"],
    "MONTAGE": ["Aufbauspezifikationen", "Montageabwicklung"],
    "TRANSPORT": ["Transporteinheiten", "Transportdauer"],
    "GEBRAUCH": ["Betriebsbedingungen"],
    "INSTANDHALTUNG": ["Wartungsabwicklung", "Verschleißreduzierende Materialien"],
    "KOSTEN": ["Mehrkosten", "Budget"]
}


# ============================================================
# REQUEST MANAGER (Zentral für ALLE API Calls)
# ============================================================

class LLMRequestManager:
    def __init__(self, client, default_model, rpm_limit=18):
        self.client = client
        self.default_model = default_model
        self.interval = 60.0 / rpm_limit
        self.last_call = 0.0
        self.lock = threading.Lock()

    def throttle(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            self.last_call = time.time()

    def call_api(self, messages, model=None, response_format=None, temperature=0.0, max_tokens=None, retries=3):
        model_to_use = model if model else self.default_model
        
        for attempt in range(retries):
            try:
                self.throttle()
                kwargs = {
                    "model": model_to_use,
                    "messages": messages,
                    "temperature": temperature,
                    "top_p": 1.0
                }
                if response_format:
                    kwargs["response_format"] = response_format
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content

            except Exception as e:
                error_msg = str(e).lower()
                print(f"API Fehler ({model_to_use}): {e}")
                
                if attempt < retries - 1:
                    wait = 10 * (attempt + 1)
                    if "429" in error_msg or "rate limit" in error_msg:
                        wait *= 2 # Länger warten bei Rate Limits
                    print(f"Warte {wait}s und versuche erneut...")
                    time.sleep(wait)
                else:
                    print("Maximale Versuche erreicht.")
                    return None

    def call_json(self, prompt, model=None):
        content = self.call_api(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            response_format={"type": "json_object"}
        )
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                print("Fehler beim Parsen der JSON-Antwort.")
        return {}


# Manager Instanz erstellen (RPM ggf. an deinen Account anpassen)
llm = LLMRequestManager(client, MODEL, rpm_limit=15)


# ============================================================
# PDF READER
# ============================================================

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
    
def extract_display_page_number(page_text: str, default_index: int) -> str:
    """Sucht nach dem Muster 'XX/YYY' oder 'XX / YYY' im Text."""
    # Findet bspw. "35/132" oder "35 / 132"
    match = re.search(r"(\d+)\s*/\s*\d+", page_text)
    if match:
        return match.group(0) # Gibt den gefundenen String "35/132" zurück
    return f"S. {default_index + 1}" # Fallback, falls nichts gefunden wird

def read_pdf(path: str) -> List[dict]:  # Geändert zu List[dict]
    doc = fitz.open(path)
    blocks = []
    
    with pdfplumber.open(path) as pb_doc:
        for page_num in tqdm(range(len(doc)), desc="PDF Auslesen (Multimodal)"):
            page = doc[page_num]
            
            # --- NEU: ECHTE SEITENZAHL AUSLESEN ---
            full_page_text = page.get_text()
            display_page = extract_display_page_number(full_page_text, page_num)
            
            # --- 1. NORMALEN TEXT EXTRAHIEREN ---
            for block in page.get_text("blocks"):
                text = block[4].strip()
                text = re.sub(r'-\n\s*', '', text)
                text = text.replace('\n', ' ')
                text = re.sub(r'\s{2,}', ' ', text).strip()
                if len(text) > 50:
                    # Geändert: Speichere Text UND Seite
                    blocks.append({"text": text, "page": display_page})

            # --- 2. TABELLEN EXTRAHIEREN ---
            pb_page = pb_doc.pages[page_num]
            tables = pb_page.extract_tables()
            for table in tables:
                cleaned_table = [[str(cell).replace('\n', ' ').strip() if cell is not None else "" for cell in row] for row in table]
                
                if cleaned_table and len(cleaned_table) > 1:
                    headers = cleaned_table[0]
                    for row in cleaned_table[1:]:
                        if not any(row): continue
                        row_statements = []
                        for i, cell_value in enumerate(row):
                            if cell_value and i < len(headers):
                                header_name = headers[i]
                                if header_name:
                                    row_statements.append(f"{header_name} ist {cell_value}")
                                else:
                                    row_statements.append(cell_value)
                        
                        if row_statements:
                            # Hier nutzen wir display_page im Satz
                            sentence = f"Spezifikation aus Tabelle (Seite {display_page}) - Für das Bauteil/System gilt: " + ", ".join(row_statements) + "."
                            blocks.append({"text": sentence, "page": display_page})

            # --- 3. SKIZZEN EXTRAHIEREN ---
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            vision_description = describe_sketches_on_page(img_bytes)
            if vision_description:
                # Hier nutzen wir display_page in der Beschreibung
                info_text = f"Zusätzliche Informationen aus Skizzen (Seite {display_page}) - {vision_description}"
                blocks.append({"text": info_text, "page": display_page})

    return blocks


# ============================================================
# CHUNKING
# ============================================================

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
# ISO‑konforme Chunk-Erzeugung mit Traceability
# =========================

def create_chunks(sections: List[Dict]) -> List[Dict]: # Geändert: List[Dict] statt List[str]
    """
    Erzeugt nachvollziehbare ISO-Chunks.
    Nutzt ein "Sliding Window" für Fließtext, ignoriert dieses aber bei harten Tabellen-/Skizzendaten.
    """
    chunks: List[Dict] = []
    seen_chunks = set()
    
    last_valid_context = "Allgemeine Systembeschreibung"
    recent_text_window = []

    # Wir iterieren nun über Dictionaries
    for section_index, section_data in enumerate(sections):
        # Text und Seite aus dem Dictionary extrahieren
        section_text = section_data["text"]
        real_page = section_data["page"] # Das ist jetzt z.B. "35/132"

        atomic_chunks = iso_atomic_chunk_text(section_text)
        current_context = section_text.strip()
        
        if len(current_context) < 15:
            current_context = last_valid_context
        else:
            last_valid_context = current_context

        # Prüfung bleibt gleich, da sie auf den Text schaut
        is_technical_data = "Spezifikation aus Tabelle" in current_context or "Zusätzliche Informationen aus Skizzen" in current_context

        for chunk_index, chunk in enumerate(atomic_chunks):
            normalized_chunk = re.sub(r'\s+', ' ', chunk.strip()).lower()
            
            unique_signature = f"{current_context} || {normalized_chunk}"
            if unique_signature in seen_chunks:
                continue 
            seen_chunks.add(unique_signature)

            if is_technical_data:
                final_context = current_context
            else:
                if recent_text_window:
                    window_text = " ".join(recent_text_window)
                    final_context = f"Letzte Sätze davor: {window_text}\nAktueller Absatz: {current_context}"
                else:
                    final_context = f"Aktueller Absatz: {current_context}"
                
                recent_text_window.append(chunk)
                if len(recent_text_window) > 3:
                    recent_text_window.pop(0)

            # --- ÄNDERUNG HIER: "page" nutzt jetzt die echte Seitenzahl ---
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "source_section": section_index,
                "chunk_index": chunk_index,
                "chunk_text": chunk,
                "context_text": final_context,
                "page": real_page  # Nutzt den extrahierten Wert (z.B. "35/132")
            })

    return chunks



# ============================================================
# EMBEDDINGS + RETRIEVAL
# ============================================================

def build_vector_index(chunks):
    texts = [c["chunk_text"] for c in chunks]
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = embedder.encode(texts, convert_to_numpy=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index, embedder

def retrieve(query, index, embedder, chunks, k=15):
    vec = embedder.encode([query], convert_to_numpy=True)
    _, idx = index.search(vec, k)
    return [chunks[i] for i in idx[0]]


# ============================================================
# REQUIREMENT & VERIFICATION GENERATION
# ============================================================

def generate_requirements(topic, keyword, context):
    prompt = f"""
Du bist Systems Engineer nach ISO 29148.
NUTZE AUSSCHLIESSLICH die Informationen aus dem bereitgestellten Kontext.
ERFINDE KEINE WERTE ODER ANFORDERUNGEN.

Thema: {topic}
Keyword: {keyword}

Kontext:
{context}

Extrahiere ALLE relevanten, atomaren Anforderungen, die STRIKT zum Thema "{topic}" passen.
Es gibt kein Limit für die Anzahl, aber VERMEIDE zwingend Dopplungen und Widersprüche!
Antworte AUSSCHLIESSLICH auf Deutsch.

Regeln:
- Jede Anforderung MUSS zwingend mit "Das System muss" beginnen.
- Anforderungen müssen atomar und messbar sein
- Ignoriere irrelevante Informationen.
- Wenn im Kontext KEINE konkrete Anforderung zu "{topic}" steht, gib eine LEERE LISTE zurück: []

STRICT JSON
{{
"requirements": [ "Das System muss ..." ]
}}
"""
    result = llm.call_json(prompt)
    return result.get("requirements", [])

def generate_verification(requirement: str, validation_context: str) -> Dict:
    prompt = f"""
Du bist ein ISO 29148 Verification Engineer.
Wähle eine geeignete Verification Methode: Inspection | Analysis | Test | Demonstration

Erstelle einen quantifizierbaren Step-by-Step Verifikationsplan.
Kontext bei Bedarf: {validation_context[:1500]}

Requirement: {requirement}

STRICT JSON
{{
"method": "Inspection | Analysis | Test | Demonstration",
"plan": "Schritt 1: ... Schritt 2: ..."
}}
"""
    result = llm.call_json(prompt)
    return {
        "method": result.get("method", ""),
        "plan": result.get("plan", "")
    }


# ============================================================
# INCOSE RULE CHECK & IMPROVEMENT
# ============================================================

def llm_check_incose_compliance(requirement: str) -> Dict:
    rules_formatted = "\n".join([f"{rule_id}: {rule.get('beschreibung', '')}" for rule_id, rule in INCOSE_RULES.items()]) if INCOSE_RULES else "Keine Regeln geladen."

    prompt = f"""
Du bist ein INCOSE Requirements Auditor.
Bewerte die Anforderung gegen jede INCOSE-Regel.

KATEGORIEN: "erfüllt", "nicht erfüllt", "nicht beurteilbar"

AUSGABEFORMAT (STRICT JSON):
{{ "R1": "erfüllt", "R2": "nicht erfüllt", ... }}

INCOSE-REGELN:
{rules_formatted}

ANFORDERUNG: "{requirement}"
"""
    # CRITIC_MODEL über den Manager aufrufen
    rule_results = llm.call_json(prompt, model=CRITIC_MODEL)

    erfuellt, nicht_erfuellt, nicht_beurteilbar = [], [], []
    for rule_id, status in rule_results.items():
        if status == "erfüllt": erfuellt.append(rule_id)
        elif status == "nicht erfüllt": nicht_erfuellt.append(rule_id)
        else: nicht_beurteilbar.append(rule_id)

    overall_status = "perfekt formuliert" if not nicht_erfuellt else "nicht perfekt formuliert"

    return {
        "overall_status": overall_status,
        "erfuellt": sorted(erfuellt),
        "nicht_erfuellt": sorted(nicht_erfuellt)
    }

def improve_requirement(requirement, violated_rules):
    if not violated_rules: return requirement
    rule_list = ", ".join(violated_rules)
    
    prompt = f"""
Du bist INCOSE Requirements Experte.
Überarbeite die folgende Anforderung, da sie Regeln verletzt: {rule_list}

WICHTIGE REGELN: atomar, messbar, eindeutig, testbar.
Beginne mit "Das System muss".
Die gesamte Ausgabe MUSS auf Deutsch erfolgen. Kein Englisch!

STRICT JSON
{{ "requirement": "Das System muss ..." }}

Anforderung: {requirement}
"""
    result = llm.call_json(prompt)
    return result.get("requirement", requirement)

def improve_requirement_loop(requirement, max_loops=3):
    current_req = requirement
    for i in range(max_loops):
        rule_check = llm_check_incose_compliance(current_req)
        violations = rule_check.get("nicht_erfuellt", [])[:5]

        if not violations:
            return current_req, rule_check

        print(f"  🔧 Verbesserung {i+1} | Verletzte Regeln: {violations}")
        current_req = improve_requirement(current_req, violations)

    return current_req, llm_check_incose_compliance(current_req)


# ============================================================
# EXCEL EXPORT MIT OPENPYXL
# ============================================================

def save_to_excel_formatted(results, output_path):
    # JSON-Daten vorher entpacken für eine saubere Excel-Struktur
    formatted_results = []
    for row in results:
        new_row = row.copy()
        incose_data = new_row.pop("INCOSE_Raw") # Entferne rohes Dictionary
        new_row["Erfüllte INCOSE Regeln"] = ", ".join(incose_data.get("erfuellt", []))
        new_row["Verletzte INCOSE Regeln"] = ", ".join(incose_data.get("nicht_erfuellt", []))
        formatted_results.append(new_row)

    df = pd.DataFrame(formatted_results)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Requirements')
        worksheet = writer.sheets['Requirements']
        
        # Spaltenbreite und Zeilenumbruch anpassen
        for col in worksheet.columns:
            column_letter = col[0].column_letter
            worksheet.column_dimensions[column_letter].width = 35
            for cell in col:
                cell.alignment = Alignment(wrap_text=True, vertical='top')


# ============================================================
# MAIN
# ============================================================

def main():
    print("📄 Lade Pflichtenheft...")
    pdf_blocks = read_pdf(PDF_INPUT)
    
    print("📄 Lade Validation Dokument...")
    raw_val_blocks = read_pdf(PDF_VALIDATION)
    validation_text = "\n".join([b["text"] for b in raw_val_blocks])
    

    print("✂️ Erstelle Chunks...")
    chunks = create_chunks(pdf_blocks)

    print("🧠 Generiere Embeddings...")
    index, embedder = build_vector_index(chunks)

    results = []
    seen_requirements = set()

    for topic, keywords in TOPICS.items():
        print(f"\n{'='*30}\nTHEMA: {topic}\n{'='*30}")

        for keyword in keywords:
            print(f"🔎 Keyword: {keyword}")
            retrieved = retrieve(keyword, index, embedder, chunks)
    
            if not retrieved:
                # FALL A: Gar keine Fundstellen
                results.append({
                    "Hauptmerkmal": topic,
                    "Keyword": keyword,
                    "Requirement": "Anforderung anhand der gegebenen PDF nicht ableitbar.",
                    "Verifizierungsmethode": "N/A",
                    "Verifizierungsplan": "N/A",
                    "Finale INCOSE Bewertung": "N/A",
                    "INCOSE_Raw": {"erfuellt": [], "nicht_erfuellt": []},
                    "Verwendete Chunks": "Keine relevanten Stellen gefunden."
                })
                continue

            # Hier generieren wir direkt die gewünschte Syntax: (Seite X): Text...
            context = "\n".join(f"(Seite {c['page']}): {c['chunk_text']}" for c in retrieved)
            requirements = generate_requirements(topic, keyword, context)
    
            # FALL B: LLM findet keine gültige Anforderung
            if not requirements or len(requirements) == 0:
                results.append({
                    "Hauptmerkmal": topic,
                    "Keyword": keyword,
                    "Requirement": "Anforderung anhand der gegebenen PDF nicht ableitbar.",
                    "Verifizierungsmethode": "N/A",
                    "Verifizierungsplan": "N/A",
                    "Finale INCOSE Bewertung": "N/A",
                    "INCOSE_Raw": {"erfuellt": [], "nicht_erfuellt": []},
                    "Verwendete Chunks": context[:1000] + "..." # Gekürzt für Übersichtlichkeit
                })
                continue

            # FALL C: Anforderungen gefunden
            for req in requirements:
                normalized = req.lower().strip()
                if normalized in seen_requirements:
                    continue
                seen_requirements.add(normalized)

                print(f"  📝 Prüfe Anforderung: {req[:50]}...")
                verification = generate_verification(req, validation_text)
                final_req, rule_check = improve_requirement_loop(req)

                final_rating = "Gegeben" if rule_check["overall_status"] == "perfekt formuliert" else "Nicht gegeben"
                
                # Wir nutzen hier den exakt formatierten 'context' String, der Seiten und Text vereint
                results.append({
                    "Hauptmerkmal": topic,
                    "Keyword": keyword,
                    "Requirement": final_req,
                    "Verifizierungsmethode": verification.get("method",""),
                    "Verifizierungsplan": verification.get("plan",""),
                    "Finale INCOSE Bewertung": final_rating,
                    "INCOSE_Raw": rule_check,
                    "Verwendete Chunks": context[:2500] # Begrenzung auf 2500 Zeichen für Excel-Zellen-Stabilität
                })

    print("\n💾 Speichere Excel Datei (formatiert)...")
    save_to_excel_formatted(results, OUTPUT_EXCEL)
    print("✅ Pipeline erfolgreich abgeschlossen!")

if __name__ == "__main__":
    main()