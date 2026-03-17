import os
import base64
import anthropic
from pathlib import Path

# Load API key from environment
API_KEY = os.getenv("ANTHROPIC_API_KEY")

MODELS = [
    "claude-sonnet-4-6",
    "claude-haiku-4-5"
]

IMAGE_PATH = Path(r"C:\Users\vohiovbeunu\.gemini\antigravity\brain\ad49aff9-cf44-4ba1-a930-49a995d6f4c9\media__1773745402112.png")

PROMPT = """
ACT AS A PHOTOCOPIER. Extract every text row from the Grafana dashboard legend.

1. Find every panel. Each panel has a TITLE at the top (e.g., FINGRID SERVERS CPU ABOVE 90).
2. Identify the panel type: CPU, MEM, or DISK.

For EACH panel, output:
---PANEL: [FULL TITLE]---
[Literal Row 1 from Legend]
[Literal Row 2 from Legend]
...

STRICT RULES:
- Copy characters EXACTLY. Do not fix what you think are mistakes.
- Grafana drive labels often start with a backslash and colon, e.g., ( \\C: ). Do not mistake the backslash for an 'I'.
- Do not compress IP addresses (e.g., if you see "10.1.1", do not write "10.11").
- Output every single row you see in the legend.
- If a row is unreadable, write [UNREADABLE].
"""

def compare():
    if not IMAGE_PATH.exists():
        print(f"Error: Image not found at {IMAGE_PATH}")
        return

    with open(IMAGE_PATH, "rb") as f:
        img_bytes = f.read()
    b64_img = base64.b64encode(img_bytes).decode('utf-8')

    client = anthropic.Anthropic(api_key=API_KEY)

    results = {}
    for model_id in MODELS:
        print(f"\n--- Testing Model: {model_id} ---")
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64_img
                            }
                        }
                    ]
                }]
            )
            results[model_id] = response.content[0].text
            print(results[model_id])
        except Exception as e:
            print(f"Error with {model_id}: {e}")

    # Save results to a file for review
    with open("model_comparison_results.txt", "w", encoding="utf-8") as f:
        for model_id, output in results.items():
            f.write(f"MODEL: {model_id}\n")
            f.write("-" * 20 + "\n")
            f.write(output + "\n\n")

if __name__ == "__main__":
    compare()
