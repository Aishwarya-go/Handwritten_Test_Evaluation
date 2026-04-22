import json
import os

def evaluate_answer(question_text, model_answer, rubric, student_answer, max_marks, groq_api_key):
    """
    Call Groq LLM to evaluate a student's answer against model answer and rubric.
    Returns structured JSON with score, feedback, matched/missing rubric points.
    """

    # If no API key yet, return mock result for testing
    if not groq_api_key:
        return mock_evaluation(max_marks)

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)

        prompt = f"""You are an expert teacher evaluating a student's handwritten answer.

Question: {question_text}

Model Answer: {model_answer}

Rubric (each point has marks allocated):
{json.dumps(rubric, indent=2)}

Student's Answer (extracted via OCR, may have errors):
{student_answer}

Maximum Marks: {max_marks}

Evaluate the student's answer strictly based on the rubric. Be fair but accurate.
If the OCR text looks garbled or unreadable, set ocr_quality_concern to true.

Respond ONLY with a JSON object in this exact format, no other text:
{{
  "score": <number between 0 and {max_marks}>,
  "confidence": <number between 0 and 1>,
  "matched_points": [<list of rubric points the student covered>],
  "missing_points": [<list of rubric points the student missed>],
  "feedback": "<1-2 sentence qualitative feedback for the student>",
  "ocr_quality_concern": <true or false>
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Validate required fields
        required_fields = ["score", "confidence", "matched_points", "missing_points", "feedback", "ocr_quality_concern"]
        for field in required_fields:
            if field not in result:
                result[field] = get_default(field, max_marks)

        # Clamp score to valid range
        result["score"] = max(0, min(float(result["score"]), max_marks))

        return result

    except Exception as e:
        print(f"LLM evaluation error: {e}")
        return mock_evaluation(max_marks)


def mock_evaluation(max_marks):
    """Returns a mock evaluation when no API key is available"""
    return {
        "score": max_marks * 0.7,
        "confidence": 0.5,
        "matched_points": ["Mock: answer partially correct"],
        "missing_points": ["Mock: some points missing"],
        "feedback": "This is a mock evaluation. Groq API key not configured yet.",
        "ocr_quality_concern": False
    }


def get_default(field, max_marks):
    defaults = {
        "score": 0,
        "confidence": 0.5,
        "matched_points": [],
        "missing_points": [],
        "feedback": "Could not evaluate.",
        "ocr_quality_concern": False
    }
    return defaults.get(field, None)