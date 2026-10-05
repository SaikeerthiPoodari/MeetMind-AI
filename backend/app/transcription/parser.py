import re

TIME = re.compile(r"(?:\[?)(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\]?)\s*(?:[-|]\s*)?(.*)")

def parse_text(content: str) -> list[dict[str, str]]:
    segments = []
    for index, raw in enumerate(content.splitlines()):
        line = raw.strip()
        if not line or line.upper() in {"WEBVTT", "NOTE"} or line.isdigit() or "-->" in line: continue
        match = TIME.match(line)
        if match:
            hours, minutes, seconds, text = match.groups()
            timestamp = f"{int(hours) * 60 + int(minutes):02d}:{int(seconds or 0):02d}" if seconds is not None else f"{int(hours):02d}:{int(minutes):02d}"
            segments.append({"timestamp": timestamp, "speaker": "Unknown speaker", "text": text.strip(), "topic": "Imported transcript"})
        else:
            segments.append({"timestamp": f"00:{index:02d}", "speaker": "Unknown speaker", "text": line, "topic": "Imported transcript"})
    return segments
