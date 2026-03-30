# =========================
# 3. INCOSE REGELWERK (Externe, normativ referenzierte Regeln)
# =========================

INCOSE_RULES = {
    "R1": {
        "titel": "Strukturierte Anforderungen",
        "beschreibung": "Anforderungen sollen einer konsistenten Struktur folgen: [Bedingung] [Subjekt] [Modalverb] [Handlung] [Objekt] [Leistungsmerkmal].",
        "beispiel": "Wenn Benutzeranfragen verarbeitet werden, soll das Datenbanksystem Suchergebnisse innerhalb von 2,0 ± 0,5 Sekunden liefern."
    },
    "R2": {
        "titel": "Aktivform",
        "beschreibung": "Die verantwortliche Einheit muss am Satzanfang stehen; Passivkonstruktionen sind zu vermeiden.",
        "beispiel": "Das Sicherheitsmodul verschlüsselt die Daten."
    },
    "R3": {
        "titel": "Geeignetes Subjekt",
        "beschreibung": "Systemanforderungen müssen das System oder eine Systemkomponente als Subjekt haben, nicht den Benutzer.",
        "beispiel": "Das Authentifizierungssystem prüft die Zugangsdaten."
    },
    "R4": {
        "titel": "Definierte Begriffe",
        "beschreibung": "Alle technischen Begriffe müssen im Glossar definiert und konsistent verwendet werden.",
        "beispiel": "Der Begriff Benutzerkonto wird im gesamten Dokument einheitlich verwendet."
    },
    "R5": {
        "titel": "Bestimmte Artikel",
        "beschreibung": "Für eindeutig definierte Entitäten ist der bestimmte Artikel zu verwenden.",
        "beispiel": "Die Datenbank speichert die Konfigurationsdaten."
    },
    "R6": {
        "titel": "Einheitliche Maßeinheiten",
        "beschreibung": "Maßeinheiten müssen im gesamten Dokument konsistent verwendet werden.",
        "beispiel": "Alle Zeitangaben erfolgen in Sekunden."
    },
    "R7": {
        "titel": "Keine vagen Begriffe",
        "beschreibung": "Subjektive oder mehrdeutige Begriffe sind durch messbare Kriterien zu ersetzen.",
        "beispiel": "Die Antwortzeit beträgt maximal 2 Sekunden."
    },
    "R8": {
        "titel": "Keine Ausweichklauseln",
        "beschreibung": "Formulierungen wie „falls möglich“ oder „soweit erforderlich“ sind zu vermeiden.",
        "beispiel": "Das System speichert die Daten dauerhaft."
    },
    "R9": {
        "titel": "Keine offenen Aufzählungen",
        "beschreibung": "Offene Formulierungen wie „unter anderem“ oder „etc.“ sind zu vermeiden.",
        "beispiel": "Das System unterstützt die Formate PDF, DOCX und TXT."
    },
    "R10": {
        "titel": "Keine überflüssigen Infinitive",
        "beschreibung": "Formulierungen wie „soll in der Lage sein“ sind zu vermeiden.",
        "beispiel": "Das System verarbeitet Benutzereingaben."
    },
    "R11": {
        "titel": "Getrennte Bedingungen",
        "beschreibung": "Jede Bedingung oder Einschränkung muss klar und getrennt formuliert werden.",
        "beispiel": "Wenn Bedingung A erfüllt ist, soll das System Aktion X ausführen."
    },
    "R12": {
        "titel": "Korrekte Grammatik",
        "beschreibung": "Anforderungen müssen grammatikalisch korrekt formuliert sein.",
        "beispiel": "Die Software speichert die Konfigurationsdatei."
    },
    "R13": {
        "titel": "Korrekte Rechtschreibung",
        "beschreibung": "Rechtschreibfehler sind zu vermeiden, da sie zu Fehlinterpretationen führen können.",
        "beispiel": "Das System initialisiert die Benutzerverwaltung."
    },
    "R14": {
        "titel": "Korrekte Zeichensetzung",
        "beschreibung": "Satzzeichen müssen korrekt verwendet werden, um die Bedeutung eindeutig zu machen.",
        "beispiel": "Wenn der Modus aktiv ist, soll das System eine Warnmeldung anzeigen."
    },
    "R15": {
        "titel": "Logische Ausdrücke",
        "beschreibung": "Logische Verknüpfungen müssen eindeutig formuliert sein.",
        "beispiel": "Wenn Bedingung A UND Bedingung B erfüllt sind, soll das System starten."
    },
    "R16": {
        "titel": "Vermeidung negativer Anforderungen",
        "beschreibung": "Negative Formulierungen sind zu vermeiden; positive Aussagen sind zu bevorzugen.",
        "beispiel": "Das System erreicht eine Verfügbarkeit von mindestens 99,9 %."
    },
    "R17": {
        "titel": "Kein Schrägstrich",
        "beschreibung": "Der Schrägstrich darf nicht zur Bedeutungsverkürzung verwendet werden.",
        "beispiel": "Das System speichert Daten pro Benutzer und pro Sitzung."
    },
    "R18": {
        "titel": "Einzelne Aussage",
        "beschreibung": "Eine Anforderung darf nur eine Fähigkeit oder Eigenschaft beschreiben.",
        "beispiel": "Das System protokolliert Benutzeranmeldungen."
    },
    "R19": {
        "titel": "Vermeidung von Kombinatoren",
        "beschreibung": "Wörter wie „und“, „oder“, „dann“ deuten auf mehrere Anforderungen hin und sind aufzutrennen.",
        "beispiel": "Das System validiert Eingaben."
    },
    "R20": {
        "titel": "Keine Zweckformulierungen",
        "beschreibung": "Zweckerklärungen gehören nicht in den Anforderungstext.",
        "beispiel": "Das System speichert die Daten verschlüsselt."
    },
    "R21": {
        "titel": "Keine Klammern",
        "beschreibung": "Zusatzinformationen dürfen nicht in Klammern stehen.",
        "beispiel": "Das System verwendet AES2_56 zur Verschlüsselung."
    },
    "R22": {
        "titel": "Keine Aufzählungen",
        "beschreibung": "Mehrere Objekte sind in getrennte Anforderungen zu überführen.",
        "beispiel": "Das System verarbeitet XML-Dateien."
    },
    "R23": {
        "titel": "Unterstützende Diagramme",
        "beschreibung": "Komplexe Zusammenhänge sollen durch Modelle oder Diagramme ergänzt werden.",
        "beispiel": "Das Ablaufdiagramm beschreibt den Anmeldeprozess."
    },
    "R24": {
        "titel": "Keine Pronomen",
        "beschreibung": "Pronomen wie „es“ oder „dies“ sind zu vermeiden.",
        "beispiel": "Das System speichert den Datensatz."
    },
    "R25": {
        "titel": "Unabhängigkeit von Überschriften",
        "beschreibung": "Anforderungen müssen ohne Kontext verständlich sein.",
        "beispiel": "Das System erzeugt täglich einen Statusbericht."
    },
    "R26": {
        "titel": "Vermeidung absoluter Aussagen",
        "beschreibung": "Absolute Begriffe wie „immer“ oder „nie“ sind zu vermeiden.",
        "beispiel": "Das System erreicht eine Verfügbarkeit von mindestens 99,9 %."
    },
    "R27": {
        "titel": "Explizite Bedingungen",
        "beschreibung": "Alle relevanten Bedingungen müssen explizit genannt werden.",
        "beispiel": "Bei Datenübertragung über öffentliche Netzwerke verschlüsselt das System die Daten."
    },
    "R28": {
        "titel": "Mehrere Bedingungen klarstellen",
        "beschreibung": "Mehrere Bedingungen müssen logisch eindeutig verknüpft sein.",
        "beispiel": "Wenn Bedingung A ODER Bedingung B erfüllt ist, soll das System starten."
    },
    "R29": {
        "titel": "Klassifikation",
        "beschreibung": "Anforderungen sollen nach Typ klassifiziert werden.",
        "beispiel": "Dies ist eine Leistungsanforderung."
    },
    "R30": {
        "titel": "Eindeutige Formulierung",
        "beschreibung": "Jede Anforderung darf nur einmal existieren.",
        "beispiel": "Die Anforderung wird nicht doppelt formuliert."
    },
    "R31": {
        "titel": "Lösungsneutralität",
        "beschreibung": "Anforderungen beschreiben WAS, nicht WIE.",
        "beispiel": "Das System speichert Daten persistent."
    },
    "R32": {
        "titel": "Universelle Quantifizierung",
        "beschreibung": "Begriffe wie „jede“ sind präziser als Sammelbegriffe.",
        "beispiel": "Jede Sitzung wird protokolliert."
    },
    "R33": {
        "titel": "Wertebereiche",
        "beschreibung": "Leistungswerte müssen mit Toleranzen angegeben werden.",
        "beispiel": "Die Antwortzeit beträgt 2,0 ± 0,3 Sekunden."
    },
    "R34": {
        "titel": "Messbare Leistung",
        "beschreibung": "Leistungsanforderungen müssen messbar sein.",
        "beispiel": "Das System verarbeitet 100 Anfragen pro Sekunde."
    },
    "R35": {
        "titel": "Zeitliche Abhängigkeiten",
        "beschreibung": "Zeitangaben müssen präzise formuliert sein.",
        "beispiel": "Die Verarbeitung erfolgt innerhalb von 5 ± 1 Minuten."
    },
    "R36": {
        "titel": "Konsistente Begriffe und Einheiten",
        "beschreibung": "Begriffe und Einheiten müssen über alle Artefakte hinweg konsistent sein.",
        "beispiel": "Der Begriff Antwortzeit wird einheitlich verwendet."
    },
    "R37": {
        "titel": "Abkürzungen",
        "beschreibung": "Abkürzungen müssen konsistent verwendet werden.",
        "beispiel": "GPS wird nicht abwechselnd ausgeschrieben."
    },
    "R38": {
        "titel": "Vermeidung unklarer Abkürzungen",
        "beschreibung": "Abkürzungen mit mehreren Bedeutungen sind zu vermeiden.",
        "beispiel": "CPU wird eindeutig definiert."
    },
    "R39": {
        "titel": "Styleguide",
        "beschreibung": "Ein organisationsweiter Stilguide ist einzuhalten.",
        "beispiel": "Alle Anforderungen folgen dem gleichen Satzmuster."
    },
    "R40": {
        "titel": "Dezimalformat",
        "beschreibung": "Dezimalzahlen müssen konsistent dargestellt werden.",
        "beispiel": "5,0 Sekunden statt 5 oder 5,00."
    },
    "R41": {
        "titel": "Verwandte Anforderungen",
        "beschreibung": "Zusammengehörige Anforderungen sollen logisch gruppiert werden.",
        "beispiel": "Alle Sicherheitsanforderungen sind gemeinsam aufgeführt."
    },
    "R42": {
        "titel": "Strukturierte Anforderungssätze",
        "beschreibung": "Alle Anforderungstypen müssen systematisch berücksichtigt werden.",
        "beispiel": "Funktionale, Leistungs- und Sicherheitsanforderungen sind enthalten."
    }
}
