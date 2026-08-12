import os
import json
import base64

from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def encode_image(image_path):
    """
    Convert image to Base64.
    """

    with open(image_path, "rb") as image_file:
        return base64.b64encode(
            image_file.read()
        ).decode("utf-8")


def analyze_visual_difference(
    reference_image,
    actual_image,
    difference_image,
    similarity,
    difference_count
):
    """
    Analyze visual differences using OpenAI Vision.
    """

    try:

        reference_base64 = encode_image(reference_image)
        actual_base64 = encode_image(actual_image)
        difference_base64 = encode_image(difference_image)

        prompt = f"""
You are a Senior Mobile QA Automation Engineer.

You are performing Visual Regression Testing.

You are given three screenshots.

Image 1:
Reference Screenshot

Image 2:
Actual Screenshot

Image 3:
Difference Screenshot generated using OpenCV.

Similarity Score:
{similarity}

Difference Count:
{difference_count}





Ignore the following:

- Device time
- Battery
- Signal
- WiFi
- Notifications
- Dynamic news
- Advertisements
- Live timestamps
- Personalized content
- Scrolling differences
- News headlines
- Article images
- Story thumbnails
- Author names
- Publication times
- Dynamic advertisements
- Personalized content
- Recommendation feeds
- Live news updates

Focus only on genuine UI issues.

Check:

- Header
- Toolbar
- Navigation Bar
- Bottom Navigation
- Icons
- Buttons
- Theme
- Colors
- Alignment
- Padding
- Margins
- Missing UI
- Overlapping UI
- Text Clipping
- Font differences
- Layout
- Missing controls
- Font rendering
- Clipped text
- Overlapping components
- Incorrect spacing
- Color/theme regressions

Return ONLY valid JSON.

Example:

{{
    "overall_status":"FAIL",
    "issue_count":2,
    "summary":"Two visual defects detected.",
    "issues":[
        {{
            "severity":"High",
            "component":"Header",
            "title":"Header alignment changed",
            "description":"Header logo shifted.",
            "recommendation":"Verify toolbar layout."
        }},
        {{
            "severity":"Low",
            "component":"Bottom Navigation",
            "title":"Navigation icon shifted",
            "description":"Games icon moved slightly.",
            "recommendation":"Verify navigation layout."
        }}
    ]
}}
"""

        response = client.responses.create(
            model="gpt-4.1",

            input=[
                {
                    "role": "user",
                    "content": [

                        {
                            "type": "input_text",
                            "text": prompt
                        },

                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{reference_base64}"
                        },

                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{actual_base64}"
                        },

                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{difference_base64}"
                        }

                    ]
                }
            ]
        )




        result = response.output_text.strip()
        print("\n================ AI RAW RESPONSE ================\n")
        print(result)
        print("\n===============================================\n")
        # Remove markdown code block if present
        if result.startswith("```json"):
            result = result.replace("```json", "", 1)

        if result.endswith("```"):
            result = result[:-3]

        result = result.strip()

        return json.loads(result)

    except Exception as e:

        return {

            "overall_status": "ERROR",

            "issue_count": 0,

            "summary": str(e),

            "issues": []

        }