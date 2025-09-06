from logging import Logger, getLogger

import gradio as gr
import gradio.themes as gr_themes

from privacy_enabled_agents import PEASettings
from privacy_enabled_agents.frontend.helpers import create_chat_function
from privacy_enabled_agents.runtime import create_privacy_agent

# Create logger for this module
logger: Logger = getLogger(__name__)

pea_settings = PEASettings()

user_chat_doc = """
**Unterhaltungen aus Nutzersicht**<br/>
Dies ist die Unterhaltung aus Sicht des Nutzers.<br/>
Nachrichten hier können personenbezogene Daten (pbD) enthalten, so wie in einer normalen Konversation.
"""

bot_chat_doc = """
**Unterhaltungen aus Bot-Sicht**<br/>
Dies ist die "tatsächliche" Unterhaltung aus Sicht des Bots.<br/>
Nachrichten hier enthalten Platzhalter anstelle personenbezogener Daten.<br/>
Das KI-Modell arbeitet mit diesen Platzhaltern, z. B. für Tool-Aufrufe.
"""

basic_scenario_description = """
Ein simpler Agent mit Datenschutz-Funktion.

Nutzende können mit dem Agenten interagieren, während ihre personenbezogenen Daten geschützt bleiben.
Der Agent beantwortet Anfragen, ohne sensible Informationen offenzulegen.
Dieser Agent verfügt über keine speziellen Werkzeuge oder Fähigkeiten.
Er ist zum Beispiel hilfreich beim Ausformulieren einer E-Mail-Antwort.
"""

websearch_scenario_description = """
Ein hilfreicher und professioneller Web-Suchassistent.

Der Agent findet Informationen effizient und präzise in Online-Quellen.
Websuchen werden über Google durchgeführt, wobei die Privatsphäre der Nutzenden geschützt bleibt.
Dies unterstützt z.B. bei der Recherche zu aktuellen Themen oder Persönlichkeiten.
"""

overview_content = """
#### Was sind KI-Agenten mit Datenschutz?

KI-Agenten mit Datenschutz sind KI-Systeme, die automatisiert personenbezogene Daten während Unterhaltungen schützen. <br/>
Wenn Sie mit diesen Agenten chatten, werden empfindliche Daten wie Namen, Adressen, Telefonnummern oder medizinische Informationen erkannt und durch sichere Platzhalter ersetzt.

#### Wie funktioniert das?

- 🔍 **Automatische Erkennung**: Das System findet personenbezogene Informationen in Ihren Nachrichten
- 🔒 **Sichere Ersetzung**: Sensible Daten werden durch Platzhalter wie `[PERSON-01]` ersetzt
- 🤖 **KI-Verarbeitung**: Der Agent arbeitet mit den geschützten Daten und bleibt voll funktionsfähig
- 🔄 **Wiederherstellung**: Ihre Originaldaten werden sicher gespeichert und können bei Bedarf wiederhergestellt werden

#### Warum sollte ich so etwas verwenden?

Dieses Konzept ist ideal für sensitive Bereiche wie
- Gesundheitswesen
- Finanzdienstleistungen
- Öffentliche Verwaltung
- oder jede andere Anwendung, in der sie ihre Daten privat halten möchten.

Es stellt sicher, dass Betreiber von KI-Modellen und Drittanbietern keine direkten Einblicke in Ihre persönlichen Informationen erhalten. <br/>
Gleichzeitig ermöglicht es Institutionen wie Krankenhäusern, Banken oder Regierungsbehörden, KI-Agenten zu nutzen, ohne selbst kostspielig KI-Modelle auf eigener Infrastruktur betreiben zu müssen.

#### Probieren Sie gerne die Agenten aus!
"""


footer_content = """
### Kernkomponenten des Datenschutzsystems

Datenschutzfähige Agenten bieten ein Rahmenwerk zum Erkennen, Ersetzen und Verwalten personenbezogener Daten (pbD) in KI-gestützten Unterhaltungen. Sensible Daten werden erkannt, durch sichere Platzhalter ersetzt und während des gesamten Konversationsablaufs verwaltet, ohne die Funktionalität der Agenten zu beeinträchtigen.

**Kernkomponenten:**
- **Erkennungsschicht**: pbD-Erkennung mithilfe von GLiNER-Modellen und Regex-Regeln
- **Ersetzungsschicht**: Verschiedene Ersetzungsstrategien (Platzhalter, Verschlüsselung, Hashing, Pseudonyme)
- **Speicherschicht**: Sichere Speicherung von Entitäten und Konversationen (z. B. Redis/Valkey)
- **Agentenschicht**: Spezialisierte Agenten für verschiedene Domänen (Medizin, Finanzen, öffentliche Dienste, Websuche)

### Datenschutzfunktionen

- 🔍 **Erweiterte Erkennung**: Erkennt Namen, Adressen, E-Mails, Telefonnummern, medizinische IDs, Kennzeichen und benutzerdefinierte Entitätstypen
- 🔒 **Verschiedene Ersetzungsstrategien**: Platzhalter, Verschlüsselung, Hashing oder Pseudonyme
- 💾 **Sichere Speicherung**: Geschützte Speicherung der Originaldaten mit Thread-Isolation
- 🔄 **Bidirektionale Verarbeitung**: Nahtlose Umwandlung zwischen Nutzer- und KI-Sicht
- 🎯 **Domänenspezifische Agenten**: Datenschutzbewusste Werkzeuge für verschiedene Anwendungsfälle
- 📊 **Monitoring & Evaluation**: Evaluationsrahmen und optionale Langfuse-Integration

### Systemarchitektur

**Ablauf:**
1. **personenbezogene Daten erkennen**: Eingaben der Nutzenden werden auf pbD untersucht
2. **Daten ersetzen**: Gefundene pbD werden durch sichere Platzhalter ersetzt
3. **KI-Verarbeitung**: Der Agent verarbeitet die geschützten Nachrichten und erstellt Antworten oder nutzt Werkzeuge
4. **Ausgabe wiederherstellen**: Platzhalter in der Ausgabe werden durch die Originaldaten ersetzt
5. **Rückgabe oder Ausführung**: Die Antwort wird dem Nutzenden zurückgegeben oder ein Werkzeug wird mit den Originaldaten ausgeführt

**Unterstützte Entitätstypen:**
- Basis: Namen, Orte, Organisationen, Adressen, E-Mails, Telefonnummern
- Benutzerdefiniert: Erweiterbares Framework für domänenspezifische Entitäten, z. B. medizinische IDs, Kennzeichen, Kontonummern


### Verfügbare Agententypen

- **🤖 Basis-Agent**: Demonstriert die grundlegenden Datenschutzfunktionen ohne spezielle Werkzeuge im Hintergrund.
- **🌐 Agent mit Websuche**: Führt Websuchen durch und schützt Benutzeranfragen durch Platzhalter.

### Anwendungsfälle

Besonders nützlich für:
- Gesundheitswesen
- Finanzdienstleistungen
- Öffentliche Verwaltung
- Jede Anwendung mit GDPR/HIPAA-Anforderungen
- Forschung und Entwicklung mit sensiblen Datensätzen

### Entwicklung & Forschung

Dieses Projekt ist Teil laufender Forschung zu datenschutzfreundlichen KI-Systemen. Das Framework ist erweiterbar und konfigurierbar, um Integration in bestehende Anwendungen und Forschungsprojekte zu erleichtern.

**Forschungsgebiete:**
- Datenschutzfreundliches maschinelles Lernen
- Sichere Mehrparteienberechnung in KI
- Automatisierung von Regulierungs-Compliance
- Domänenspezifischer Datenschutz
- Evaluationsmetriken für Privacy-Systeme
"""

poll_banner = """
<div style="background-color: #23272f; border: 1px solid #ffd700; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 20px; color: #ffd700;">
    <strong style="color: #ffd700;">
    Nehmen Sie bitte an einer kurzen Umfrage (ca. 5 Minuten) zur Evaluation des Systems teil!<br/>
    Testen Sie zuvor beide Agenten, um fundiertes Feedback geben zu können.
    </strong>
</div>
"""


def create_gradio_interface() -> gr.Blocks:
    # # Custom CSS with subtle diagonal gradient background
    # css = """
    # .gradio-container {
    #     background: linear-gradient(135deg, #1F2937 0%, #1a2332 30%, #0f4f47 100%);
    #     min-height: 100vh;
    # }
    # """

    with gr.Blocks(
        theme=gr_themes.Base(primary_hue="teal"),
        # css=css,
        fill_width=True,
    ) as demo:
        demo.title = "Privacy-Enabled Agents / KI-Agenten mit Datenschutz"

        # Main title and simple overview
        gr.Markdown("# Privacy-Enabled Agents / KI-Agenten mit Datenschutz")

        with gr.Sidebar(open=True):
            gr.Markdown(overview_content)

        if pea_settings.poll_link is not None:
            # Poll banner and button
            gr.HTML(value=poll_banner)
            gr.Button("An Umfrage teilnehmen 📝", link=pea_settings.poll_link)

        basic_agent, basic_chat_model = create_privacy_agent({"topic": "basic"})
        basic_chat_fn = create_chat_function("basic", basic_agent, basic_chat_model)

        websearch_agent, websearch_chat_model = create_privacy_agent(
            {
                "topic": "websearch",
                "model_provider": "openai",
                "model_name": "gpt-4.1",
            }
        )
        websearch_chat_fn = create_chat_function("websearch", websearch_agent, websearch_chat_model)

        browser_state = gr.BrowserState(storage_key="privacy_agent_session")

        # Load existing session from browser state when page loads
        @demo.load(inputs=[browser_state], outputs=[browser_state])
        def load_existing_session(saved_state):
            if saved_state and saved_state.get("thread_id"):
                logger.info(f"Loading existing session with thread_id: {saved_state['thread_id']}")
                return saved_state
            else:
                # Generate new thread_id for new session
                logger.info("No existing session found, starting a new one.")
                new_state = {}
                return new_state

        with gr.Tab(label="Basis-Agent"):
            gr.Markdown(basic_scenario_description)
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown(value=user_chat_doc, container=True)
                        basic_user_chatbot: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/person.png", "resources/robot.png"),
                            height=500,
                        )
                        user_input: gr.Textbox = gr.Textbox(
                            placeholder="Nachricht eingeben...",
                            show_label=False,
                            submit_btn=True,
                        )
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown(value=bot_chat_doc, container=True)
                        real_basic_conversation: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/incognito.png", "resources/robot.png"),
                            height=500,
                        )

            user_input.submit(
                fn=basic_chat_fn,
                inputs=[user_input, basic_user_chatbot, browser_state],
                outputs=[basic_user_chatbot, real_basic_conversation, browser_state],
            ).then(
                lambda: "",  # Clear the input after submission
                outputs=[user_input],
            )

        with gr.Tab(label="Agent mit Websuche"):
            gr.Markdown(websearch_scenario_description)
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=user_chat_doc, container=True)
                        websearch_user_chatbot: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/person.png", "resources/robot.png"),
                            height=500,
                        )
                        websearch_input: gr.Textbox = gr.Textbox(
                            placeholder="Nachricht eingeben...",
                            show_label=False,
                            submit_btn=True,
                        )
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=bot_chat_doc, container=True)
                        real_websearch_conversation: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/incognito.png", "resources/robot.png"),
                            height=500,
                        )

            websearch_input.submit(
                fn=websearch_chat_fn,
                inputs=[websearch_input, websearch_user_chatbot, browser_state],
                outputs=[websearch_user_chatbot, real_websearch_conversation, browser_state],
            ).then(
                lambda: "",  # Clear the input after submission
                outputs=[websearch_input],
            )

        # Accordion with detailed technical information
        with gr.Accordion(label="Technische Details & Systemarchitektur", open=False):
            gr.Markdown(footer_content)

    return demo


medical_scenario_description = """
### Medizinischer Transport-Agent

Ein spezialisierter Assistent für medizinische Transportdienste in München, Deutschland.

**Funktionen:**
- Medizinische Transporte zu/von Einrichtungen buchen
- In der Nähe befindliche medizinische Einrichtungen (Krankenhäuser, Ärzte) finden
- Prüfen, ob ein Standort im Servicegebiet liegt
- Bestehende Transporte auflisten und stornieren
- Adressen in Koordinaten umwandeln

**Benötigte Informationen:**
- Deutsche Krankenversicherungs-ID
- Patientenname und Geburtsdatum
- Abhol-/Zielorte

**Servicegebiet:** Münchner Stadtgebiet
"""

public_service_scenario_description = """
### Agent für öffentliche Dienste

Ein professioneller Assistent für die Vergabestelle von Parkgenehmigungen in der Stadtverwaltung.

**Verfügbare Dienste:**
- Aktuelle Parkgenehmigungen prüfen
- Neue Genehmigungen beantragen (Anwohner, Besuch, Gewerbe)
- Gebühren bezahlen
- Bestehende Genehmigungen verlängern

**Genehmigungsarten:**
- Anwohnerparkausweis (120 €/Jahr)
- Besucherausweis (50 €)
- Gewerbeausweis (300 €)

**Voraussetzungen:**
- Mindestens 30 Tage gemeldeter Wohnsitz für die Anspruchsberechtigung
- Maximal ein Ausweis pro Fahrzeug
"""

financial_scenario_description = """
### Banking-Agent

Ein professioneller Finanzassistent und Berater für sichere Bankgeschäfte.

**Bankfunktionen:**
- Kontostände prüfen
- Geld zwischen Konten überweisen (IBAN)
- Erhöhung des Kreditlimits anfragen
- Transaktionsverlauf einsehen

**Sicherheitsmerkmale:**
- Einhaltung regulatorischer Anforderungen
- Verifizierung des Kontoinhabers
- Bestätigung von Transaktionen

**Voraussetzungen:**
- 18+ Jahre für Kreditlimit-Erhöhungen
- Mindestens 30 Tage Kontohistorie
- Einkommensabhängige Kreditlimits
"""
