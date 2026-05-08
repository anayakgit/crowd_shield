import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        return

    # Initialize the new Google GenAI client
    client = genai.Client(api_key=api_key)
    
    # We'll try gemini-2.0-flash as it's the latest and highly supported
    # Alternatively, use 'gemini-1.5-flash'
    model_id = 'gemini-2.0-flash' 
    
    print(f"Attempting to call {model_id}...")
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents="Say 'Hello, Gemini is working!' if you can hear me."
        )
        print("\n✅ Success! Gemini response:")
        print("-" * 30)
        print(response.text)
        print("-" * 30)
    except Exception as e:
        print(f"\n❌ API Call Failed: {str(e)}")
        
        # If it failed, let's try a fallback model name
        print("\nTrying fallback model: gemini-1.5-flash...")
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents="Say 'Hello, Gemini 1.5 is working!'"
            )
            print("\n✅ Success with fallback! Gemini response:")
            print(response.text)
        except Exception as e2:
            print(f"❌ Fallback also failed: {str(e2)}")

if __name__ == "__main__":
    test_gemini()
