# AI processing pipeline

MeetMind persists processing state in `processing_stages`. The ordered stages are:

`TRANSCRIPTION`, `LANGUAGE_DETECTION`, `CLEANING`, `SPEAKER_DETECTION`, `TOPIC_EXTRACTION`, `SUMMARY`, `DECISIONS`, `ACTIONS`, `COMMITMENTS`, `RISKS`, `OPEN_QUESTIONS`, `SPEAKER_INTELLIGENCE`, `TIMELINE`, `MEETING_HEALTH`, and `KNOWLEDGE_INDEXING`.

Each stage has `PENDING`, `PROCESSING`, `COMPLETED`, or `FAILED` state, attempt count, timestamps, error text, and evidence references. A failed meeting can be retried at `POST /api/meetings/{id}/retry`; completed persisted records are retained. The current API exposes the state at `GET /api/meetings/{id}/processing`.

AI output is only persisted with transcript evidence. Provider configuration is server-side, and an unavailable provider returns an explicit error rather than inventing intelligence.
