import streamlit as st
import os
import re
import requests
from http.cookiejar import MozillaCookieJar
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from fpdf import FPDF

# --- 1. BOOTSTRAP: RECREATE COOKIE FILE FROM SECRETS ---
# This bypasses the YouTube IP block on Streamlit Cloud
if "COOKIE_DATA" in st.secrets:
    with open("youtube.com_cookies.txt", "w") as f:
        f.write(st.secrets["COOKIE_DATA"])

# --- 2. CONFIGURATION & CLIENT SETUP ---
# Fetch API Key from Streamlit Secrets (Settings > Secrets)
api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 3. LOGIC FUNCTIONS ---

def get_video_id(url):
    """Extracts the 11-character YouTube Video ID."""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_transcript(video_id):
    """
    Fetches transcript using a session-based authenticated approach.
    Uses the recreated cookie file to bypass data-center IP blocks.
    """
    try:
        session = requests.Session()
        
        # Load cookies into the session if file exists
        if os.path.exists('youtube.com_cookies.txt'):
            cj = MozillaCookieJar('youtube.com_cookies.txt')
            cj.load(ignore_discard=True, ignore_expires=True)
            session.cookies = cj
        
        # Initialize API with the authenticated session
        ytt_api = YouTubeTranscriptApi(http_client=session)
        
        # Retrieve the transcript list
        transcript_list = ytt_api.list(video_id)
        
        # Priority: English -> Hindi -> First available
        try:
            transcript = transcript_list.find_transcript(['en', 'hi'])
        except:
            transcript = next(iter(transcript_list))
            
        data = transcript.fetch()
        return " ".join([snippet['text'] for snippet in data])
        
    except Exception as e:
        st.error(f"Transcript Error: {e}")
        return None

def generate_pdf(text):
    """Generates a downloadable PDF of the generated plan."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Ensure text is compatible with Latin-1 encoding
    clean_text = text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

# --- 4. STREAMLIT UI DESIGN ---

st.set_page_config(page_title="AI Video Action Planner", page_icon="🎯", layout="wide")

# Sidebar Configuration
with st.sidebar:
    st.title("⚙️ Project Control")
    
    # Feature: Output Language Selector
    target_lang = st.selectbox(
        "Output Language:",
        ["English", "Hindi", "Spanish", "French", "German", "Bengali", "Telugu"]
    )
    
    # Feature: User Goal Customization
    user_goal = st.text_area(
        "Specific Focus/Goal:", 
        placeholder="e.g., Only extract the Python code snippets...",
        help="The AI will tailor the plan to this specific objective."
    )
    
    st.divider()
    
    # Debug Status for Mentor Review
    if os.path.exists('youtube.com_cookies.txt'):
        st.success("✅ Auth Session Active")
    else:
        st.warning("⚠️ Using Public Session (IP Block Risk)")

# Main Interface
st.title("🌍 Universal AI-Driven Video Action Planner")
st.write("Convert any YouTube tutorial into a structured, multilingual action plan.")

video_url = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Generate Action Plan"):
    if not video_url:
        st.warning("Please enter a valid URL.")
    else:
        v_id = get_video_id(video_url)
        if not v_id:
            st.error("Invalid YouTube URL format.")
        else:
            # Step 1: Extraction
            with st.spinner("🔍 Extracting intelligence from YouTube..."):
                raw_transcript = get_transcript(v_id)
            
            if raw_transcript:
                # Step 2: AI Processing
                with st.spinner(f"🧠 Synthesizing Action Plan in {target_lang}..."):
                    # Dynamic System Instruction
                    sys_prompt = (
                        f"You are a Senior Project Manager. Your task is to analyze the provided video transcript "
                        f"and create a professional, chronological action plan. "
                        f"IMPORTANT: Write the entire response in {target_lang}. "
                        f"If the transcript is in Hinglish or Hindi, translate it accurately to {target_lang}. "
                        f"Use Markdown headers, bullet points, and bold text for clarity."
                    )
                    
                    user_prompt = f"User Goal: {user_goal}\n\nTranscript: {raw_transcript}"

                    response = client.models.generate_content(
                        model="gemini-3-flash-preview",
                        contents=user_prompt,
                        config=types.GenerateContentConfig(system_instruction=sys_prompt)
                    )
                    
                    # Step 3: Display & Download
                    st.success("🎯 Your Plan is Ready!")
                    st.markdown(response.text)
                    
                    pdf_bytes = generate_pdf(response.text)
                    st.download_button(
                        label="📥 Download Plan as PDF",
                        data=pdf_bytes,
                        file_name="Action_Plan.pdf",
                        mime="application/pdf"
                    )