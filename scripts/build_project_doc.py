"""Generate a fully formatted Word report for the MeetMind AI project."""
from pathlib import Path
from xml.sax.saxutils import escape
import zipfile

OUT = Path(__file__).resolve().parents[1] / "MeetMindAI_Project_Documentation_Final.docx"

chapters = [
    ("1. Introduction", [
        ("MeetMind AI", "MeetMind AI is a Generative AI-powered meeting intelligence web application. It converts meeting recordings and transcripts into structured, searchable, and evidence-linked intelligence for product, engineering, operations, management, and client-facing teams."),
        ("Purpose of the Project", "The project addresses the gap between a meeting conversation and the reliable follow-through required after it. Instead of leaving decisions, action items, risks, and questions inside long recordings or handwritten notes, MeetMind AI creates a persistent meeting record that users can review, search, compare, share, and export."),
        ("Role of Generative AI", "Generative AI supports grounded summarisation, question answering, language detection, structured extraction, follow-up drafting, and meeting assistance. AI output is constrained by persisted transcript evidence. The application distinguishes FACT, AI INFERENCE, and AI RECOMMENDATION and refuses to invent unsupported participants, decisions, deadlines, owners, or quotations."),
        ("Key Features", "The application includes transcript ingestion, resumable AI processing, executive and detailed summaries, decision intelligence, action and commitment tracking, risk radar, open questions, speaker statistics, meeting health, timeline navigation, multilingual interfaces, a browser meeting room, meeting sharing, a persistent AI assistant, reports, downloads, search, notifications, privacy controls, and demo mode."),
        ("Target Users", "The target users are teams conducting recurring product planning, sprint planning, project, client, management, engineering, and operational meetings. These users need traceable evidence, clear ownership, secure access, and actionable follow-up."),
    ]),
    ("2. Problem Statement", [
        ("The Problem Today", "Meeting information is often fragmented across recordings, chat messages, personal notes, and follow-up emails. Manual review is slow and inconsistent. Teams may remember that a topic was discussed without being able to identify the exact speaker, timestamp, decision status, action owner, or evidence supporting the conclusion."),
        ("Limitations of Existing Workflows", "Manual workflows are slow and error-prone. Simple rule-based tools cannot reliably understand context, distinguish a proposal from a confirmed decision, connect actions to evidence, or compare how decisions change across recurring meetings. Important risks and open questions can remain unresolved because they are not represented as persistent records."),
        ("Why GenAI Is Appropriate", "A grounded Generative AI system can interpret natural language, summarise long conversations, classify important statements, extract structured records, and answer questions in context. MeetMind AI combines those capabilities with authentication, evidence references, persistence, validation, and explicit provider boundaries."),
        ("Expected Outcome", "The expected outcome is a reviewable meeting record that reduces manual note-taking and follow-up effort while improving traceability. Users receive useful summaries and suggestions without losing the original transcript or being presented with unsupported facts."),
    ]),
    ("3. Objectives", [
        ("Objective 1: Build a Functional Application", "Develop a working full-stack application accessible through a browser, with authenticated users, meeting creation, transcript upload, recording entry, meeting intelligence, search, exports, actions, notifications, and privacy controls."),
        ("Objective 2: Integrate a Suitable AI Boundary", "Use a replaceable server-side AI provider interface. Demo mode operates without external credentials, while an optional OpenAI provider can be configured through backend environment variables. API keys are never exposed to frontend code."),
        ("Objective 3: Engineer Reliable Inputs and Prompts", "Use structured request models, provider adapters, transcript evidence, output validation, fallback responses, confidence values, and explicit insufficient-evidence messages. The processing pipeline stores stage status so failed work can be retried."),
        ("Objective 4: Deliver an Intuitive Interface", "Provide a premium responsive workspace with dashboard, meeting room, meeting intelligence, action center, calendar, analytics, settings, profile, search, notifications, and a persistent grounded AI assistant."),
        ("Objective 5: Evaluate Output Quality", "Evaluate API behaviour with unit and integration-style tests for authentication, authorization, meeting lifecycle, upload, processing, Q&A, decisions, actions, risks, questions, exports, sharing, profile updates, and notification persistence."),
    ]),
    ("4. Project Scope", [
        ("Included Use Cases", "MeetMind AI supports creating a meeting, uploading text or supported media, recording locally in a browser, joining a meeting by link, persisting transcript segments, processing intelligence, asking grounded questions, comparing meetings, generating follow-up drafts, exporting records, sharing meeting links, and reviewing action status."),
        ("AI Features", "The AI features include executive, short, standard, and detailed summaries; key discussion points; topics; important moments; follow-up recommendations; decisions and Decision DNA; decision drift; action extraction; Commitment Radar; risk detection; open question detection; speaker statistics; meeting health; timeline events; cross-meeting retrieval; pre-meeting intelligence; and the application assistant."),
        ("Input and Output Types", "Inputs include meeting titles, descriptions, natural-language questions, text transcripts, SRT and VTT captions, audio, video, browser recordings, and profile images. Outputs include structured JSON, TXT, Markdown, PDF, DOCX, SRT, VTT, summaries, decisions, actions, risks, questions, evidence references, notifications, and follow-up drafts."),
        ("Boundaries", "External transcription, translation, OAuth integrations, production TURN infrastructure, and external AI providers require configuration. Demo mode uses an isolated seeded Apollo dataset and is clearly labelled DEMO DATA. Production mode is designed to use real backend records rather than hardcoded dashboard metrics."),
    ]),
    ("5. Proposed System and Methodology", [
        ("End-to-End Pipeline", "The pipeline is: recording or transcript → transcription → language detection → transcript cleaning → speaker detection → topic extraction → summary → decisions → actions → commitments → risks → open questions → speaker intelligence → timeline → meeting health → knowledge indexing."),
        ("Resumable Processing", "Processing state is stored in processing_stages. Each stage records its name, status, attempt count, start time, completion time, error text, and evidence references. Supported meeting states include QUEUED, PROCESSING, TRANSCRIBING, ANALYZING, COMPLETED, and FAILED. A failed meeting can be retried without losing previously completed records."),
        ("Evidence-First Processing", "Transcript segments retain timestamp, speaker, text, and topic. Extracted decisions, actions, risks, and questions carry timestamps, evidence, confidence, and status. If evidence is insufficient, the system returns an explicit refusal rather than generating a plausible but unsupported answer."),
        ("Meeting Lifecycle", "A meeting can be created, joined, started, recorded, stopped, saved, processed, analysed, shared, and joined by other authenticated users. Recording consent is required before browser capture begins."),
    ]),
    ("6. System Architecture and Workflow", [
        ("Frontend Layer", "The frontend is a React and TypeScript single-page application served by Vite. It provides authenticated navigation, dashboard cards, meeting intelligence views, the Meeting Room, action controls, profile management, multilingual selectors, export controls, and the persistent AI Assistant."),
        ("Backend Layer", "The backend is a FastAPI application. It provides authentication, JWT-protected routes, owner and participant access checks, meeting lifecycle endpoints, transcript and recording upload, processing, search, Q&A, exports, sharing, profile updates, notifications, audit logging, and administrative routes."),
        ("Persistence Layer", "SQLAlchemy models persist users, preferences, meetings, actions, recordings, transcript segments, decisions, risks, open questions, meeting sessions, questions, notifications, audit logs, chat messages, follow-up drafts, processing stages, and meeting share codes. SQLite supports local demonstration and the schema is designed for migration to PostgreSQL."),
        ("Provider Layer", "AI, transcription, and translation are isolated behind provider interfaces. Demo providers support a complete local walkthrough. Configured providers can be substituted without exposing secrets to the browser."),
        ("Workflow", "The browser sends authenticated requests to the backend. The backend verifies the user, validates input, checks meeting authorization, performs provider or demo processing, persists results, and returns structured records. Important outputs link back to source evidence."),
    ]),
    ("7. Implementation", [
        ("Technology Stack", "Frontend: React, TypeScript, Vite, Lucide icons, CSS, and Vitest. Backend: Python, FastAPI, Pydantic, SQLAlchemy, Uvicorn, JWT authentication, and provider adapters. Storage: local storage abstraction for recordings and SQLite for local persistence, with Alembic migrations. Testing: pytest and Vitest."),
        ("Authentication and Security", "Passwords are securely hashed. JWTs protect API requests. CORS is configured for local development. Inputs use Pydantic validation. Uploads have type and size checks. API keys remain server-side. Owner and participant access checks prevent unauthorized meeting intelligence retrieval. Audit logs capture important account and resource operations."),
        ("AI Assistant", "The persistent assistant receives the current page and selected meeting context. In workspace mode it searches authorized meetings; in meeting mode it restricts answers to the selected meeting. Answers contain a FACT or INSUFFICIENT EVIDENCE label, confidence, evidence text, speaker, timestamp, and source meeting where available."),
        ("Multilingual Support", "The UI has localization catalogs for English, Hindi, Telugu, Tamil, Kannada, Malayalam, Marathi, and Bengali. The selected preference is persisted per user. Meeting language detection, original transcript preservation, and provider-based translation are separate from the original source record."),
        ("Meeting Room", "The Meeting Room uses browser media APIs for local camera and microphone capture, MediaRecorder for recording, optional SpeechRecognition for captions, camera and microphone controls, screen sharing, elapsed time, chat, invite links, join codes, and QR sharing. Audio-only fallback is supported when camera access is unavailable."),
        ("Meeting Sharing", "Each meeting has a share code and share URL. A public preview exposes limited metadata, while authenticated join-by-link creates a participant session before meeting intelligence can be accessed. The live Meeting Room displays the invite link, meeting ID, join code, and QR code."),
    ]),
    ("8. User Interface and Application Screens", [
        ("Dashboard", "The dashboard shows persisted meetings, open actions, evidence coverage, meeting health, recent intelligence, and quick actions for analysing a meeting or starting a live meeting."),
        ("Meeting Room", "The Meeting Room includes the meeting title, consent control, camera preview, Start recording button, microphone and camera toggles, screen sharing, elapsed recording state, browser captions, meeting chat, invite sharing, and Stop and save control."),
        ("Meeting Intelligence", "A meeting page presents summary, transcript, decisions, actions, risks, open questions, speakers, timeline, comparison, translation, exports, follow-up drafts, and an Ask about this meeting button. The assistant clears its previous conversation when the selected meeting changes."),
        ("Action Center", "The Action Center supports filtering and status updates for persisted tasks. Actions contain task, owner, deadline, priority, status, timestamp, evidence, confidence, and source meeting information."),
        ("Profile and Settings", "The profile page displays basic account details, editable full name, email, workspace role, sign out, and a clickable profile photo uploader. Settings provide language preferences and account-level interface configuration."),
        ("Screenshots", "Screenshots for the final academic submission should be captured from the running application at the dashboard, Meeting Room, meeting intelligence page, assistant panel, action center, sharing panel, and profile page."),
    ]),
    ("9. Results, Challenges, and Limitations", [
        ("Implemented Results", "The project provides a working authenticated application with persisted demo data, a 46-segment Apollo transcript, decisions, action items, risks, open questions, meeting health, evidence-linked Q&A, resumable pipeline state, sharing, profile management, downloads, notifications, localization, and a cross-application assistant."),
        ("Technical Challenges", "Challenges included coordinating browser permissions, recording media formats, transcript availability, data migrations for existing local databases, provider-safe AI behaviour, owner and participant authorization, and preserving evidence through partial processing failures."),
        ("AI Output Challenges", "Generative models can produce incomplete or off-topic output if unconstrained. MeetMind AI addresses this through provider boundaries, grounded transcript context, structured extraction, confidence values, evidence fields, insufficient-evidence fallbacks, and tests for unknown facts."),
        ("Current Limitations", "Local browser recording captures one participant. Production multi-user WebRTC requires signaling and TURN infrastructure. Real transcription, translation, email, calendar, Zoom, Google Meet, Teams, Slack, Notion, Jira, and Trello integrations require provider credentials and OAuth configuration. These integrations are not falsely shown as connected."),
        ("Privacy Limitations", "Users should configure retention, storage, consent, and provider policies before production use. The local demonstration uses SQLite and local storage. A production deployment should use managed database and object storage, HTTPS, secret management, monitoring, and formal retention controls."),
    ]),
    ("10. Conclusion", [
        ("What Was Built", "MeetMind AI is a full-stack Generative AI meeting intelligence application featuring transcript processing, evidence-linked summaries, decision intelligence, action and commitment tracking, risks, open questions, a real browser Meeting Room, sharing, multilingual UI, reports, downloads, search, notifications, profile management, and a grounded AI assistant."),
        ("Impact", "The application turns a meeting conversation into a structured record that can be searched, reviewed, compared, shared, and acted upon. This reduces manual follow-up effort and makes important decisions and responsibilities easier to verify."),
        ("Key Learnings", "The project provided practical experience in full-stack development, prompt and provider boundaries, structured AI output, evidence validation, browser media APIs, authentication, persistence, migrations, localization, access control, and testing of both successful and insufficient-evidence cases."),
    ]),
    ("11. Future Scope", [
        ("Production Real-Time Infrastructure", "Add a signaling service, multi-user WebRTC sessions, TURN servers, participant identity, reconnection, moderation, and production recording storage."),
        ("Provider Integrations", "Add authenticated Google Calendar, Outlook Calendar, Google Meet, Zoom, Microsoft Teams, Slack, email, Notion, Jira, and Trello adapters. Integrations should report NOT CONFIGURED until real authentication succeeds."),
        ("Advanced AI", "Add background workers, queue-based processing, richer diarization, multimodal analysis, improved multilingual translation, semantic vector retrieval, decision drift timelines, and human confirmation workflows for uncertain actions."),
        ("Deployment and Scale", "Deploy with PostgreSQL, managed object storage, HTTPS, secure secret management, monitoring, rate limiting, cache layers, pagination, lazy loading, and production backup and retention policies."),
        ("Mobile and Accessibility", "Provide mobile clients, stronger keyboard navigation, screen-reader support, captions, accessible color contrast, and offline-aware meeting capture."),
    ]),
    ("12. References", [
        ("Official Documentation", "FastAPI: https://fastapi.tiangolo.com/\nReact: https://react.dev/\nVite: https://vite.dev/\nSQLAlchemy: https://www.sqlalchemy.org/\nAlembic: https://alembic.sqlalchemy.org/\nOpenAI API: https://platform.openai.com/docs/\nMDN WebRTC API: https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API\nMDN MediaRecorder API: https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder"),
        ("Project Repository", "MeetMind AI GitHub repository: https://github.com/SaikeerthiPoodari/MeetMind-AI"),
        ("Demo Dataset", "Project Apollo demo data is generated for application demonstration and is clearly labelled DEMO DATA. It is not presented as real customer or employee data."),
    ]),
]

def run(text: str, bold: bool = False) -> str:
    weight = "<w:b/>" if bold else ""
    return f'<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/>{weight}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'

def paragraph(text: str, kind: str = "body") -> str:
    if kind == "title":
        props = '<w:pPr><w:jc w:val="center"/><w:spacing w:after="360"/></w:pPr>'
        run_xml = '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="36"/></w:rPr><w:t>MeetMind AI</w:t></w:r>'
    elif kind == "chapter":
        props = '<w:pPr><w:keepNext/><w:spacing w:before="300" w:after="180"/><w:outlineLvl w:val="0"/></w:pPr>'
        run_xml = '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="28"/></w:rPr><w:t xml:space="preserve">' + escape(text) + '</w:t></w:r>'
    elif kind == "heading":
        props = '<w:pPr><w:keepNext/><w:spacing w:before="180" w:after="100"/><w:outlineLvl w:val="1"/></w:pPr>'
        run_xml = '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="28"/></w:rPr><w:t xml:space="preserve">' + escape(text) + '</w:t></w:r>'
    else:
        props = '<w:pPr><w:jc w:val="both"/><w:ind w:firstLine="360"/><w:spacing w:after="140" w:line="360" w:lineRule="auto"/></w:pPr>'
        run_xml = run(text)
    return f"<w:p>{props}{run_xml}</w:p>"

def build_document() -> str:
    body = [
        paragraph("MeetMind AI Project Documentation", "title"),
        paragraph("Evidence-based Generative AI Meeting Intelligence Platform", "body"),
        paragraph("Academic Project Documentation · 2026", "body"),
        paragraph("Project Abstract", "heading"),
        paragraph("MeetMind AI is a full-stack Generative AI application that transforms meeting recordings and transcripts into reliable, searchable, and actionable intelligence. It preserves the original transcript while extracting summaries, decisions, actions, commitments, risks, open questions, speaker statistics, timelines, and follow-up recommendations."),
        paragraph("The platform combines a React and TypeScript interface with a FastAPI backend, authenticated persistence, provider-independent AI processing, a browser-based Meeting Room, meeting sharing, multilingual support, exports, and a grounded AI Assistant. Important outputs are connected to transcript evidence and the system refuses to invent facts when evidence is insufficient."),
        paragraph("Project Snapshot", "heading"),
        paragraph("Domain: Meeting intelligence and collaboration\nPrimary users: Product, engineering, operations, management, and client-facing teams\nCore value: Convert conversations into traceable decisions and follow-through\nDelivery mode: Working local web application with clearly labelled DEMO DATA\nKey principle: Evidence first, privacy aware, and actionable by design"),
        '<w:p><w:r><w:br w:type="page"/></w:r></w:p>',
    ]
    body.append(paragraph("Table of Contents", "chapter"))
    for index, (chapter, _) in enumerate(chapters, 1):
        body.append(paragraph(f"{index}. {chapter.split('. ', 1)[1]}", "body"))
    body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
    for chapter, sections in chapters:
        body.append(paragraph(chapter, "chapter"))
        for heading, text in sections:
            body.append(paragraph(heading, "heading"))
            for part in text.split("\n"):
                body.append(paragraph(part, "body"))
    body.append('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080"/></w:sectPr>')
    return '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>' + ''.join(body) + '</w:body></w:document>'

STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:jc w:val="both"/><w:spacing w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults></w:styles>'''
CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
DOC_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''

def main() -> None:
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", CONTENT_TYPES)
        docx.writestr("_rels/.rels", RELS)
        docx.writestr("word/document.xml", build_document())
        docx.writestr("word/styles.xml", STYLES)
        docx.writestr("word/_rels/document.xml.rels", DOC_RELS)
    print(OUT)

if __name__ == "__main__":
    main()
