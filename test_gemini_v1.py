import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_v1():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        return

    # Initialize client explicitly using v1 (stable) instead of v1beta
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
    
    model_id = 'gemini-1.5-flash'
    
    print(f"Attempting to call {model_id} using API version v1...")
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents="Say 'Hello, Gemini 1.5 is working on v1!'"
        )
        print("\n✅ Success! Gemini response:")
        print(response.text)
    except Exception as e:
        print(f"\n❌ API Call Failed: {str(e)}")

if __name__ == "__main__":
    test_gemini_v1()
