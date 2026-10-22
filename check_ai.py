import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors


def main():
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").strip()
    print("Provider:", os.environ.get("AI_PROVIDER"))
    print("Key set:", bool(key) and not key.startswith("your-"))
    print("Model:", model)
    if not key or key.startswith("your-") or not model:
        print("Set GEMINI_API_KEY and GEMINI_MODEL in .env before testing the connection.")
        return

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(model=model, contents="Say hi")
    except genai_errors.APIError as error:
        print(type(error).__name__, str(error)[:400])
        return
    print("SUCCESS:", response.text)


if __name__ == "__main__":
    main()