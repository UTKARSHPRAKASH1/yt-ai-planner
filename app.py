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

import requests

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
                    
                    plan_text = response.text # Store response in a variable
                    st.markdown(plan_text)
                    
                    st.divider()
                    st.subheader("📥 Export Your Plan")
                    
                    # Create two columns for the buttons
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # --- PDF Download ---
                        pdf_bytes = generate_pdf(plan_text)
                        st.download_button(
                            label="📄 Download as PDF",
                            data=pdf_bytes,
                            file_name="Action_Plan.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    with col2:
                        # --- Markdown Download ---
                        # Convert string to bytes for the download button
                        md_bytes = plan_text.encode('utf-8')
                        st.download_button(
                            label="📝 Download as Markdown (.md)",
                            data=md_bytes,
                            file_name="Action_Plan.md",
                            mime="text/markdown",
                            use_container_width=True
                        )