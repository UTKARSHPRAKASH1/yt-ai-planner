import streamlit as st
import os
import re
from dotenv import load_dotenv

# Core logic imports
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types

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
    """KEEPING YOUR EXACT FUNCTION: Using the object-based call."""
    try:
        ytt_api = YouTubeTranscriptApi()

        transcript_list = ytt_api.list(video_id)

        # Attempt to find Hindi or English
        try:
            transcript = transcript_list.find_transcript(['en', 'hi'])
        except:
            transcript = next(iter(transcript_list))

        data = transcript.fetch()

        return " ".join([snippet.text for snippet in data])

    except Exception as e:
        st.error(f"Transcript Error: {e}")
        return None


# 3. Streamlit UI (Wide Layout)
st.set_page_config(
    page_title="Youtube Personal Project Manager",
    page_icon="🌍",
    layout="wide"
)

# Sidebar for controls
with st.sidebar:
    st.title("⚙️ Project Settings")

    # FEATURE 1: Language Selector
    output_lang = st.selectbox(
        "Select Output Language:",
        ["English", "Hindi", "Spanish", "French", "German", "Bengali", "Telugu"]
    )

    user_goal = st.text_area(
        "Custom Persona/Goal:",
        placeholder="e.g. Focus on the code, or summarize for a beginner..."
    )

    # Universal Translation Feature
    universal_mode = st.toggle(
        "Universal Translation",
        value=True,
        help="Detects non-English transcripts and translates them instantly."
    )

    st.divider()
    st.info("Stack: Python 3.13 + Gemini 3 + Streamlit")


# Main Content
st.title("🌍 Youtube Personal Project Manager")
st.markdown(
    f"Enter a link to get a structured Action Plan in **{output_lang}**."
)

video_url = st.text_input(
    "YouTube URL:",
    placeholder="https://www.youtube.com/watch?v=..."
)


if st.button("Generate My Action Plan"):
    if video_url:
        v_id = get_video_id(video_url)

        if v_id:
            with st.spinner("Step 1: Fetching Transcript..."):
                raw_text = get_transcript(v_id)

            if raw_text:
                with st.spinner(f"Step 2: AI Processing in {output_lang}..."):

                    # FEATURE 2: Updated System Instruction for Translation
                    sys_instr = (
                        f"You are a professional project manager. "
                        f"IMPORTANT: Write the entire response in {output_lang}. "
                        "Use Markdown with bold headers and checklists."
                    )

                    if universal_mode:
                        sys_instr += (
                            f" The transcript might be in Hindi/Hinglish; "
                            f"accurately translate it into {output_lang}."
                        )

                    try:
                        # Using Gemini 3 Flash Preview as requested
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            contents=(
                                f"User Goal: {user_goal if user_goal else 'Detailed Action Plan'}\n\n"
                                f"Transcript: {raw_text}"
                            ),
                            config=types.GenerateContentConfig(
                                system_instruction=sys_instr
                            )
                        )

                        plan = response.text

                        # Display Results
                        st.success(f"Plan Generated Successfully in {output_lang}!")
                        st.markdown("---")
                        st.markdown(plan)

                        # FEATURE 3: FAIL-SAFE MARKDOWN DOWNLOAD
                        # No more PDF crashes or encoding errors.
                        st.download_button(
                            label=f"📥 Download Plan as .md (Markdown)",
                            data=plan, # Streamlit handles string-to-bytes for .md files automatically
                            file_name=f"Action_Plan_{output_lang}.md",
                            mime="text/markdown"
                        )
                    
                    except Exception as e:
                        st.error("🤖 The AI engine is currently busy. Please wait 10s and retry.")
                        st.info(f"Technical Detail: {e}")

        else:
            st.error("Invalid link format. Please paste a full YouTube URL.")