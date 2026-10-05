# Provider configuration

MeetMind keeps AI, translation, and transcription behind provider boundaries. The default `AI_PROVIDER=demo` uses controlled demo behavior and does not call an external service.

For structured AI analysis and grounded Q&A, configure:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=...
AI_MODEL=gpt-4o-mini
AI_TIMEOUT_SECONDS=30
```

The OpenAI adapter uses structured JSON responses and the dedicated grounding prompts. If the key is absent, the API reports `ai_configured=false` and does not claim that production AI ran.

Translation and media transcription currently expose explicit provider boundaries. With no provider credentials they return a clear `503 Not Configured` response. TXT/SRT/VTT ingestion remains available locally through the deterministic parser and preserves original transcript content.
