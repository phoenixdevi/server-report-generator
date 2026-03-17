import os
import sys
from pathlib import Path

# Add current directory to path so we can import ai_service
sys.path.append(str(Path(__file__).parent))

from ai_service import extract_data_from_images

def test_extraction():
    # Use the generated mock image
    mock_image_path = Path(r"C:\Users\vohiovbeunu\.gemini\antigravity\brain\3949632b-64cf-4409-af5e-a915b03ee767\mock_grafana_dashboard_1773726798325.png")
    
    if not mock_image_path.exists():
        print(f"Error: Mock image not found at {mock_image_path}")
        return

    print(f"Testing extraction with image: {mock_image_path.name}")
    
    with open(mock_image_path, "rb") as f:
        img_bytes = f.read()
    
    try:
        # Note: This will actually call the Gemini API if GOOGLE_API_KEY is set
        # If not, it will fail or use LM Studio if provider is switched
        results = extract_data_from_images([img_bytes])
        
        print("\n--- EXTRACTION RESULTS ---")
        import json
        print(json.dumps(results, indent=2))
        
        # Basic validation
        one_day = results.get("one_day", [])
        under_utilized = results.get("under_utilized", [])
        
        if one_day or under_utilized:
            print("\nSUCCESS: Data extracted successfully!")
        else:
            print("\nWARNING: No data extracted. Check API key and image content.")
            
    except Exception as e:
        print(f"\nERROR during extraction: {e}")

if __name__ == "__main__":
    test_extraction()
