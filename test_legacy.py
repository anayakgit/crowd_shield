import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_legacy_sdk():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        return

    genai.configure(api_key=api_key)
    
    print("Listing available models with legacy SDK...")
    try:
        found = False
        for m in genai.list_models():
            print(f"- {m.name}")
            found = True
        
        if not found:
            print("No models found!")
            return

        model = genai.GenerativeModel('gemini-1.5-flash')
        print("\nAttempting generation with gemini-1.5-flash...")
        response = model.generate_content("Say 'Hello from legacy SDK!'")
        print(f"Success: {response.text}")
        
    except Exception as e:
        print(f"Legacy SDK Failed: {e}")

if __name__ == "__main__":
    test_legacy_sdk()
