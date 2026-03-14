import streamlit as st
import os
import re
from dotenv import load_dotenv

# --- 2026 STANDARDIZED IMPORTS ---
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from fpdf import FPDF

# 1. Configuration
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Initialize Gemini Client (2026 SDK Style)
client = genai.Client(api_key=api_key)

# 2. Logic Functions
def get_video_id(url):
    """Extracts the 11-char ID from any YouTube URL format."""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_transcript(video_id):
    try:
        # ✅ The most reliable 2026 way:
        # Use the class method directly and pass 'cookies' (plural) to the list call
        # If 'cookies' is a string, it's treated as a file path.
        
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies='youtube.com_cookies.txt')
        
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
    """Simple PDF generator for the final report."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Filter non-latin characters for the basic FPDF version
    clean_text = text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

# 3. Streamlit UI (Wide Layout)
st.set_page_config(page_title="Universal AI Planner", page_icon="🌍", layout="wide")

# Sidebar for controls
with st.sidebar:
    st.title("⚙️ Project Settings")
    user_goal = st.text_area("Custom Persona/Goal:", placeholder="e.g. Focus on the code, or summarize for a beginner...")
    
    # Universal Translation Feature
    universal_mode = st.toggle("Universal Translation", value=True, help="Detects non-English transcripts and translates them instantly.")
    
    st.divider()
    st.info("Stack: Python 3.13 + Gemini 3 + Streamlit")

# Main Content
st.title("🌍 Universal YouTube Action Planner")
st.markdown("Enter a link to any video—even if it's in **Hindi** or **Hinglish**—to get an English Action Plan.")

video_url = st.text_input("YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Generate My Action Plan"):
    if video_url:
        v_id = get_video_id(video_url)
        if v_id:
            with st.spinner("Step 1: Fetching Transcript..."):
                raw_text = get_transcript(v_id)
            
            if raw_text:
                with st.spinner("Step 2: AI Translation & Planning..."):
                    # Define System Persona
                    sys_instr = "You are a professional project manager. Use Markdown with bold headers and checklists."
                    
                    if universal_mode:
                        sys_instr += " IMPORTANT: The transcript might be in Hindi or Hinglish. Translate it to English before writing the plan."

                    # Gemini 3 Model Call (Config contains System Instruction)
                    response = client.models.generate_content(
                        model="gemini-3-flash-preview",
                        contents=f"User Goal: {user_goal if user_goal else 'Detailed Action Plan'}\n\nTranscript: {raw_text}",
                        config=types.GenerateContentConfig(
                            system_instruction=sys_instr
                        )
                    )
                    
                    plan = response.text
                    
                # Display Results
                st.success("Plan Generated Successfully!")
                st.markdown("---")
                st.markdown(plan)
                
                # PDF Download Button
                st.download_button(
                    label="📥 Download Action Plan (PDF)",
                    data=generate_pdf(plan),
                    file_name="Action_Plan.pdf",
                    mime="application/pdf"
                )
        else:
            st.error("Invalid link format. Please paste a full YouTube URL.")