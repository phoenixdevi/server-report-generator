import os
import google.generativeai as genai

# Use environment variable for key
GOOGLE_API_KEY = os.getenv("GOOGLE_AI_API_KEY")

def list_models():
    genai.configure(api_key=GOOGLE_API_KEY)
    print("Listing available models...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Model: {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
