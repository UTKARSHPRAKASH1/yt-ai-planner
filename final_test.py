from youtube_transcript_api import YouTubeTranscriptApi

v_id = "kqtD5dpn9C8"

try:
    # 1. In 2026, we first initialize the API object
    ytt_api = YouTubeTranscriptApi()
    
    # 2. Use the .fetch() method instead of .get_transcript()
    # This is now the standard way to grab the text directly
    data = ytt_api.fetch(v_id)
    
    print("✅ SUCCESS! The 2026 method works.")
    print(f"First line of transcript: {data[0]['text']}")
    
except AttributeError:
    print("❌ You are likely using an older tutorial's code with a newer library version.")
except Exception as e:
    print(f"❌ Error: {e}")