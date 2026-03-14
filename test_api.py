from youtube_transcript_api import YouTubeTranscriptApi

video_id = "kqtD5dpn9C8" # The Mosh video ID
try:
    print("Attempting to fetch transcript...")
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    print("Success! First 100 characters:", str(transcript)[:100])
except Exception as e:
    print("Error detected:", e)