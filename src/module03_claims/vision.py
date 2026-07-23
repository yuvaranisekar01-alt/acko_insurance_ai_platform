import os
import json
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

VISION_PROMPT = """
You are an insurance claims damage assessor. Look at this vehicle damage photo and extract
structured information about the damage.

Respond ONLY with valid JSON (no markdown, no extra text) in exactly this format:
{
  "damage_type": "<one short category, e.g. 'collision damage', 'panel damage', 'bumper damage', 'dent', 'scratch', 'windshield damage', 'fire damage', 'flood damage', 'theft', 'rollover', 'total loss', 'crack'>",
  "damage_severity_score": <integer 1-10, where 1 is minor cosmetic damage and 10 is total loss>,
  "num_parts_affected": <integer, count of distinct vehicle parts visibly damaged>,
  "affected_parts": "<comma-separated list of specific parts visibly damaged, e.g. 'front bumper, left headlight'>"
}

Base your assessment only on what is visibly damaged in the photo. Be realistic and conservative
with severity scoring — most everyday damage (dents, scratches, minor panel damage) should score
2-5, not 8-10. Reserve 8-10 for damage that is clearly severe (total loss, major structural damage, fire).
"""


def extract_damage_info(image: Image.Image) -> dict:
    """
    Sends an uploaded damage photo to Gemini Vision and returns structured
    damage information as a dict. Raises an exception if parsing fails.
    """
    model = genai.GenerativeModel("gemini-3.5-flash")
    response = model.generate_content([VISION_PROMPT, image])

    text = response.text.strip()
    # strip markdown code fences if Gemini adds them despite instructions
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)

