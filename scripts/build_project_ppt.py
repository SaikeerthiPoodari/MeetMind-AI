"""Populate the supplied academic PowerPoint template with MeetMind AI content."""
from pathlib import Path
import html
import re
import shutil
import zipfile

TEMPLATE = Path(r"C:\Users\pooda\OneDrive\Pictures\Desktop\Project-Title.pptx")
OUTPUT = Path(__file__).resolve().parents[1] / "MeetMindAI_Project_Presentation.pptx"

REPLACEMENTS = {
    "[Project Title]": "MeetMind AI",
    "[Student Name]": "MeetMind AI Project Team",
    "[College / Institute Name]": "Academic Project Submission",
    "Department of [Department Name] · Academic Year: [Final / Pre-Final] · [20XX–20XX]": "Generative AI Application · Academic Year: 2026",
    "[Mentor Name]": "Project Mentor",
    "[the identified problem]": "turning unstructured meetings into traceable intelligence",
    "[target users]": "product, engineering, operations, and client-facing teams",
    "[GenAI model / API]": "a provider-independent AI adapter with a grounded demo provider and optional OpenAI provider",
    "[Feature A]": "evidence-linked summaries",
    "[Feature B]": "decision and action intelligence",
    "[Feature C]": "meeting Q&A and search",
    "[Feature 1]": "transcript intelligence",
    "[Feature 2]": "decision and action extraction",
    "[Feature 3]": "grounded meeting assistant",
    "[Feature 4]": "reports, sharing, and follow-up",
    "[specific application domain]": "meeting intelligence",
    "[specific problem domain and use case(s)]": "capturing meetings and converting transcripts into evidence-linked summaries, decisions, actions, risks, and questions",
    "[User group]": "teams that run recurring product, project, sprint, client, and management meetings",
    "[key expectation 1]": "traceable evidence",
    "[key expectation 2]": "secure, actionable follow-through",
    "[Input / Output Types]": "Input / Output Types",
    "[text prompt / form data / uploaded file / image]": "meeting recordings, transcripts, live captions, and natural-language questions",
    "[text / image / code]": "summaries, decisions, actions, risks, questions, reports, and grounded answers",
    "Supports a single language (English) only": "Multilingual support is implemented through localization catalogs and configurable translation providers",
    "[specific scope]": "authorized workspace meetings and the included Apollo demo dataset",
    "[specific scenario]": "uncertain ownership, missing evidence, and provider outages",
    "[content generation / query answering / personalisation]": "grounded query answering, summarization, classification, and structured extraction",
    "[text / image / code / audio]": "structured text and evidence-linked meeting intelligence",
    "[expected result]": "a searchable, reviewable meeting record with clear next steps",
    "[output type]": "evidence-linked meeting intelligence",
    "[accurate / relevant / useful]": "reviewable, traceable, and actionable",
    "[time / effort]": "manual note-taking and follow-up effort",
    "[web app / chatbot / tool]": "full-stack meeting intelligence web application",
    "[GPT-4 / Gemini / DALL·E / other]": "OpenAI-compatible provider through a server-side adapter, with a provider-safe demo mode",
    "[GenAI Model / Platform]": "OpenAI API Documentation",
    "[API Provider] Developer Reference": "FastAPI Documentation",
    "[SDK / Library] Documentation": "React and Vite Documentation",
    "[Dataset Name] · [Source / URL]": "Project Apollo demo dataset · generated and clearly labelled as DEMO DATA",
    "[External Resource Name] · [Source / URL]": "WebRTC API · https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API",
    "[Tutorial / Website Name] · [URL]": "FastAPI · https://fastapi.tiangolo.com/",
    "[Repository Name] · [GitHub URL]": "MeetMind AI · https://github.com/SaikeerthiPoodari/MeetMind-AI",
}

FULL_TEXT = {
    "The application follows a structured end-to-end pipeline · from user input collection through AI processing to final output delivery.": "MeetMind AI follows a resumable evidence-first pipeline: recording or transcript → transcription → language detection → cleaning → speaker and topic extraction → summary → decisions → actions and commitments → risks → open questions → timeline → meeting health → knowledge indexing.",
    "The architecture diagram below illustrates the complete data flow from user interaction to AI-generated response and back.": "The architecture separates the React frontend, FastAPI backend, SQLAlchemy persistence, storage abstraction, and provider adapters. User requests are authenticated, scoped to authorized meetings, processed server-side, and returned with evidence references.",
    "The following screens represent the complete user journey through the application · from landing on the home screen to receiving AI-generated results.": "The application journey is: sign in → dashboard → create or join a meeting → consent and record → persist transcript → process intelligence → inspect evidence → ask the meeting assistant → compare meetings → export and follow up.",
    "Replace the placeholder images above with actual screenshots of your working application. Include captions for each screenshot as shown.": "Screens shown in this section should be captured from the running MeetMind AI application at the dashboard, meeting room, intelligence view, and assistant panel.",
    "This project successfully demonstrates the development and deployment of a GenAI-powered application that addresses [the identified problem] for [target users]. By integrating [GenAI model / API], the system automates [key task], replacing a slow and error-prone manual process with an intelligent, responsive solution.": "This project demonstrates a GenAI-powered meeting intelligence application for product, engineering, operations, and client-facing teams. MeetMind AI automates transcript analysis and follow-up preparation while preserving source evidence and refusing unsupported claims.",
}

def replace_text(xml: str) -> str:
    pattern = re.compile(r"(<a:t(?: [^>]*)?>)(.*?)(</a:t>)", re.DOTALL)
    def repl(match: re.Match[str]) -> str:
        value = html.unescape(match.group(2))
        value = FULL_TEXT.get(value, REPLACEMENTS.get(value, value))
        for old, new in REPLACEMENTS.items():
            value = value.replace(old, new)
        return match.group(1) + html.escape(value, quote=False) + match.group(3)
    return pattern.sub(repl, xml)

def main() -> None:
    if not TEMPLATE.exists():
        raise FileNotFoundError(TEMPLATE)
    with zipfile.ZipFile(TEMPLATE, "r") as source, zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename.startswith("ppt/slides/slide") and item.filename.endswith(".xml"):
                data = replace_text(data.decode("utf-8")).encode("utf-8")
            target.writestr(item, data)
    print(OUTPUT)

if __name__ == "__main__":
    main()
