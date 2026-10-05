# Architecture

MeetMind is split into a Vite React client and a FastAPI service. The client owns presentation, navigation state, accessibility, responsive layout, and the evidence explorer. The service owns authentication, validation, authorization boundaries, upload handling, processing orchestration, and grounded Q&A.

The intended production pipeline is: media/transcript → transcription abstraction → cleaned speaker segments → structured analysis schemas → persisted meeting intelligence → evidence-linked UI. Demo mode bypasses external providers and returns a curated Apollo dataset through the same shape.
