import streamlit as st
import os
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from fpdf import FPDF

# --- 2. CONFIGURATION & CLIENT SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 3. LOGIC FUNCTIONS ---

def get_video_id(url):
    """Extracts the 11-character YouTube Video ID."""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_transcript(video_id):
    """Uses Supadata API to bypass YouTube IP blocking."""
    try:
        supadata_key = st.secrets.get("SUPADATA_API_KEY")
        if not supadata_key:
            st.error("Missing SUPADATA_API_KEY in Streamlit Secrets.")
            return None

        url = "https://api.supadata.ai/v1/youtube/transcript"
        params = {"videoId": video_id}
        headers = {"x-api-key": supadata_key}
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            transcript_segments = data.get("content", [])
            return " ".join([seg["text"] for seg in transcript_segments])
        else:
            st.error(f"Supadata Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        st.error(f"Transcript Retrieval Failed: {e}")
        return None

def generate_pdf(text):
    """Generates a downloadable PDF with basic character sanitization."""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        # Replacing common problematic characters for Latin-1 compatibility
        clean_text = text.replace('–', '-').replace('—', '-').replace('•', '*')
        clean_text = clean_text.encode('latin-1', 'ignore').decode('latin-1')
        pdf.multi_cell(0, 10, txt=clean_text)
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"PDF Error: {e}")
        return None

# --- 4. STREAMLIT UI DESIGN ---

st.set_page_config(page_title="AI Video Action Planner", page_icon="🎯", layout="wide")

# Sidebar Configuration
with st.sidebar:
    st.title("⚙️ Project Control")
    
    target_lang = st.selectbox(
        "Output Language:",
        ["English", "Hindi", "Spanish", "French", "German", "Bengali", "Telugu"]
    )
    
    user_goal = st.text_area(
        "Specific Focus/Goal:", 
        placeholder="e.g., Only extract the Python code snippets..."
    )
    
    st.divider()
    st.subheader("⚡ Quick Actions")
    
    # Task selection buttons
    task_type = None
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎴 Flashcards", use_container_width=True): task_type = "Flashcards"
        if st.button("📚 Notes", use_container_width=True): task_type = "Notes"
    with col2:
        if st.button("📝 Quiz", use_container_width=True): task_type = "Quiz"
        if st.button("📋 Summary", use_container_width=True): task_type = "Summary"
    
    # Question Bank button spans both columns for visibility
    if st.button("📂 Question Bank", use_container_width=True):
        task_type = "Question Bank"

# Main Interface
st.title("YouTube Personal Project Manager using AI ")
st.write("Convert any YouTube tutorial into structured academic or professional artifacts.")

video_url = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

# --- 5. EXECUTION LOGIC ---
if st.button("Generate Action Plan") or task_type:
    if not video_url:
        st.warning("Please enter a valid URL.")
    else:
        # Define Task Instructions
        action_map = {
            "Flashcards": "Create a set of 5-10 clear Flashcard-style Q&A pairs.",
            "Quiz": "Create a 5-question multiple choice quiz with an answer key.",
            "Notes": "Create comprehensive, structured study notes with key definitions and bullet points.",
            "Summary": "Create a concise, high-level executive summary in 5-8 bullet points.",
            "Question Bank": "Generate a comprehensive Question Bank consisting of Short (2 marks), Medium (5 marks), and Long (10 marks) answer questions based on the video content.",
            None: "create a professional, chronological action plan."
        }
        
        final_instruction = action_map.get(task_type)
        active_label = task_type if task_type else "Action Plan"

        v_id = get_video_id(video_url)
        if not v_id:
            st.error("Invalid YouTube URL format.")
        else:
            with st.spinner(f"🔍 Extracting intelligence for {active_label}..."):
                raw_transcript = get_transcript(v_id)
            
            if raw_transcript:
                with st.spinner(f"🧠 Synthesizing {active_label} in {target_lang}..."):
                    sys_prompt = (
                        f"You are a Senior Project Manager and Academic Expert. Your task is to analyze the transcript and {final_instruction} "
                        f"IMPORTANT: Write the entire response in {target_lang}. "
                        f"If the transcript is in Hinglish or Hindi, translate it accurately. "
                        f"Use clear formatting and headers for different question categories."
                    )
                    
                    user_prompt = f"User Goal: {user_goal}\n\nTranscript: {raw_transcript}"

                    response = client.models.generate_content(
                        model="gemini-3-flash-preview",
                        contents=user_prompt,
                        config=types.GenerateContentConfig(system_instruction=sys_prompt)
                    )
                    
                    st.success(f"🎯 Your {active_label} is Ready!")
                    plan_text = response.text 
                    st.markdown(plan_text)
                    
                    st.divider()
                    st.subheader(f"📥 Export Your {active_label}")
                    
                    e_col1, e_col2 = st.columns(2)
                    with e_col1:
                        pdf_bytes = generate_pdf(plan_text)
                        if pdf_bytes:
                            st.download_button(
                                label="📄 Download as PDF",
                                data=pdf_bytes,
                                file_name=f"{active_label}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                    
                    with e_col2:
                        md_bytes = plan_text.encode('utf-8')
                        st.download_button(
                            label="📝 Download as Markdown (.md)",
                            data=md_bytes,
                            file_name=f"{active_label}.md",
                            mime="text/markdown",
                            use_container_width=True
                        )