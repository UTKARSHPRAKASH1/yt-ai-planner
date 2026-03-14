import streamlit as st
import os
import re
from dotenv import load_dotenv
import requests

# --- 2026 STANDARDIZED IMPORTS ---
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from fpdf import FPDF

# 1. Setup & Configuration
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# 2. Logic Functions
def get_video_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_transcript(video_id):
    try:
        # Step A: Manually load the cookies into a session
        session = requests.Session()
        
        # We manually check the cookie file from Render
        if os.path.exists('youtube.com_cookies.txt'):
            # This is the standard Netscape cookie loading logic
            from http.cookiejar import MozillaCookieJar
            cj = MozillaCookieJar('youtube.com_cookies.txt')
            cj.load(ignore_discard=True, ignore_expires=True)
            session.cookies = cj
        
        # Step B: Initialize the API with this specific session
        # In 2026, passing the session is the only way to use cookies
        ytt_api = YouTubeTranscriptApi(http_client=session)
        
        # Step C: Now call list() without any arguments
        transcript_list = ytt_api.list(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['en', 'hi'])
        except:
            transcript = next(iter(transcript_list))
            
        data = transcript.fetch()
        return " ".join([snippet.text for snippet in data])
        
    except Exception as e:
        st.error(f"Transcript Error: {e}")
        return None

def generate_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

# 3. Streamlit Interface
st.set_page_config(page_title="AI Video Planner", page_icon="🌍", layout="wide")

with st.sidebar:
    st.title("⚙️ Project Control")
    user_goal = st.text_area("Your Focus:", placeholder="e.g., Only summarize the Python code...")
    universal_mode = st.toggle("Translate to English", value=True)
    
    # Debug Tool: Verify if Render see your cookies
    if os.path.exists('youtube.com_cookies.txt'):
        st.success("✅ Cookies Active")
    else:
        st.warning("⚠️ Cookies Missing (Check Render Environment)")

st.title("🌍 Universal YouTube Action Planner")
video_url = st.text_input("YouTube URL:")

if st.button("Generate Plan"):
    if video_url:
        v_id = get_video_id(video_url)
        if v_id:
            with st.spinner("Extracting from YouTube..."):
                raw_text = get_transcript(v_id)
            
            if raw_text:
                with st.spinner("AI Planning in progress..."):
                    # Dynamic Instruction
                    sys_instr = "You are a professional project manager. Use Markdown headers."
                    if universal_mode:
                        sys_instr += " Translate input to English if it is in Hindi/Hinglish."

                    response = client.models.generate_content(
                        model="gemini-3-flash-preview",
                        contents=f"Goal: {user_goal}\n\nTranscript: {raw_text}",
                        config=types.GenerateContentConfig(system_instruction=sys_instr)
                    )
                    
                    st.success("Plan Ready!")
                    st.markdown(response.text)
                    st.download_button("📥 Download PDF", data=generate_pdf(response.text), file_name="plan.pdf")