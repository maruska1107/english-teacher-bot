PROMPT_VERSION = "lesson-analysis-v3"

LESSON_ANALYSIS_PROMPT_TEMPLATE = """Analyze this English lesson transcript.
Return strictly valid JSON and nothing else.

Profile context:
{profile_context}

Addressing rules:
{addressing_rules}

The JSON must match this structure:
{{
  "summary": "short teacher-facing summary",
  "strengths": ["student strengths"],
  "mistakes": [
    {{"quote": "original phrase", "correction": "corrected phrase", "explanation": "brief explanation"}}
  ],
  "vocabulary": ["useful vocabulary"],
  "vocabulary_cards": [
    {{
      "term": "word or phrase for a flashcard",
      "translation_ru": "Russian translation",
      "definition_en": "short English definition or null",
      "example_sentence": "clear example sentence or null",
      "source_phrase": "phrase from the lesson transcript or null",
      "level": "CEFR level if obvious, e.g. A2/B1/B2, or null"
    }}
  ],
  "homework": ["specific homework item"],
  "teacher_recommendations": ["teacher recommendation"],
  "student_message": "ready-to-send message to students in Russian"
}}

Transcript:
{transcript}
"""
