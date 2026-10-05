# Academic project notes

## Problem and objective

Important decisions, commitments, deadlines, and risks are routinely lost in unstructured meeting conversation. The objective is to convert conversation into traceable knowledge and follow-up without presenting model inference as fact.

## GenAI role

The planned provider adapter performs structured summarization, decision/action/risk extraction, topic chapters, speaker-observable analytics, and retrieval-grounded question answering. Every output schema reserves evidence, timestamp, speaker, confidence, and provenance fields.

## Limitations and future scope

The demo uses controlled data and does not claim measured model accuracy. Future work includes a real evaluation harness with labelled transcripts, PostgreSQL persistence, provider adapters, async job queues, export generation, and meeting-to-meeting comparison.
