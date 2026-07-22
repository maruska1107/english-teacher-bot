PROMPT_VERSION = "lesson-analysis-v1"

LESSON_ANALYSIS_PROMPT_TEMPLATE = """Analyze this English lesson transcript.
Return strictly valid JSON and nothing else.
The JSON must match this structure:
{{
  "summary": "short teacher-facing summary",
  "strengths": ["student strengths"],
  "mistakes": [
    {{"quote": "original phrase", "correction": "corrected phrase", "explanation": "brief explanation"}}
  ],
  "vocabulary": ["useful vocabulary"],
  "homework": ["specific homework item"],
  "teacher_recommendations": ["teacher recommendation"],
  "student_message": "ready-to-send message to students in Russian"
}}

Transcript:
{transcript}
"""
