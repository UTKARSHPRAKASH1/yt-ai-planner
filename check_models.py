from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# This will print every model your key is allowed to use
for model in client.models.list():
    print(model.name)