import streamlit as st
import os
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from fpdf import FPDF

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
    PROFESSIONAL FIX: Uses Supadata API to bypass YouTube IP blocking.
    This service handles all proxies and anti-bot measures internally.
    """
    try:
        # 1. Retrieve the Supadata API Key from Streamlit Secrets
        supadata_key = st.secrets.get("SUPADATA_API_KEY")
        
        if not supadata_key:
            st.error("Missing SUPADATA_API_KEY in Streamlit Secrets.")
            return None

        # 2. Call the Supadata endpoint
        url = "https://api.supadata.ai/v1/youtube/transcript"
        params = {"videoId": video_id}
        headers = {"x-api-key": supadata_key}
        
        response = requests.get(url, params=params, headers=headers)
        
        # 3. Handle the response
        if response.status_code == 200:
            data = response.json()
            # Supadata returns a list of segments: [{'text': '...', 'start': 0}, ...]
            transcript_segments = data.get("content", [])
            return " ".join([seg["text"] for seg in transcript_segments])
        else:
            st.error(f"Supadata Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Transcript Retrieval Failed: {e}")
        return None

def generate_pdf(text):
    """Generates a downloadable PDF with character sanitization."""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # CLEANING STEP: Replace common problematic characters
        clean_text = text.replace('–', '-').replace('—', '-').replace('•', '*')
        clean_text = clean_text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
        
        # Encode to Latin-1 and ignore what we can't translate to stay safe
        final_text = clean_text.encode('latin-1', 'ignore').decode('latin-1')
        
        pdf.multi_cell(0, 10, txt=final_text)
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        # Fallback to very basic text if it fails
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt="Error generating full PDF. Please use the Markdown export.")
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
    st.subheader("⚡ Quick Actions")
    
    # Task selection buttons
    task_type = None
    if st.button("🎴 Generate Flashcards", use_container_width=True):
        task_type = "Flashcards"
    
    if st.button("📝 Generate Quiz", use_container_width=True):
        task_type = "Quiz"

# Main Interface
st.title("YouTube Personal Project Manager using AI ")
st.write("Convert any YouTube tutorial into a structured, multilingual action plan.")

video_url = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

# Logic to trigger processing
if st.button("Generate Action Plan") or task_type:
    if not video_url:
        st.warning("Please enter a valid URL.")
    else:
        # Determine the specific instruction based on the button clicked
        if task_type == "Flashcards":
            final_instruction = "Create a set of 5-10 clear Flashcard-style Q&A pairs."
            active_label = "Flashcards"
        elif task_type == "Quiz":
            final_instruction = "Create a 5-question multiple choice quiz with an answer key."
            active_label = "Quiz"
        else:
            final_instruction = "create a professional, chronological action plan."
            active_label = "Action Plan"

        v_id = get_video_id(video_url)
        if not v_id:
            st.error("Invalid YouTube URL format.")
        else:
            # Step 1: Extraction
            with st.spinner(f"🔍 Extracting intelligence for {active_label}..."):
                raw_transcript = get_transcript(v_id)
            
            if raw_transcript:
                # Step 2: AI Processing
                with st.spinner(f"🧠 Synthesizing {active_label} in {target_lang}..."):
                    # Dynamic System Instruction
                    sys_prompt = (
                        f"You are a Senior Project Manager and Academic Expert. Your task is to analyze the provided video transcript "
                        f"and {final_instruction} "
                        f"IMPORTANT: Write the entire response in {target_lang}. "
                        f"If the transcript is in Hinglish or Hindi, translate it accurately to {target_lang}. "
                        f"Use bullet points, and different font sizes for clarity."
                    )
                    
                    user_prompt = f"User Goal: {user_goal}\n\nTranscript: {raw_transcript}"

                    response = client.models.generate_content(
                        model="gemini-3-flash-preview",
                        contents=user_prompt,
                        config=types.GenerateContentConfig(system_instruction=sys_prompt)
                    )
                    
                    # Step 3: Display & Download
                    st.success(f"🎯 Your {active_label} is Ready!")
                    
                    plan_text = response.text # Store response in a variable
                    st.markdown(plan_text)
                    
                    st.divider()
                    st.subheader(f"📥 Export Your {active_label}")
                    
                    # Create two columns for the buttons
                    col1, col2 = st.columns(2)
                    
                    # --- Update the Download Buttons in Section 5 ---
                    with col1:
                        # Generate the PDF inside the button logic
                        try:
                            pdf_bytes = generate_pdf(plan_text)
                            st.download_button(
                                label="📄 Download as PDF",
                                data=pdf_bytes,
                                file_name=f"{active_label}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        except:
                            st.error("PDF generation failed. Use Markdown for now.")

                    with col2:
                        # Ensure UTF-8 encoding for the Markdown file
                        md_bytes = plan_text.encode('utf-8')
                        st.download_button(
                            label="📝 Download as Markdown (.md)",
                            data=md_bytes,
                            file_name=f"{active_label}.md",
                            mime="text/markdown",
                            use_container_width=True
                        )