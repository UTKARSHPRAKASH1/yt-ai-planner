import streamlit as st
import os
import re
import io
from dotenv import load_dotenv

# Core logic imports
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types

# PDF Generation imports (ReportLab - Professional & Unicode Safe)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY

# --- 1. CONFIGURATION ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Initialize Gemini Client
client = genai.Client(api_key=api_key)

# --- 2. LOGIC FUNCTIONS ---

def get_video_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_transcript(video_id):
    """Reverted to your exact working method."""
    try:
        ytt_api = YouTubeTranscriptApi()
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

def generate_pdf(markdown_text):
    """
    ULTIMATE FIX: Cleans AI-generated text to prevent ReportLab Parse Errors.
    Ensures all <b> tags are closed and illegal XML characters are removed.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    style_n = styles["Normal"]
    style_n.alignment = TA_JUSTIFY
    style_n.fontName = 'Helvetica'
    style_n.fontSize = 10 # Slightly smaller to fit the Spotify Clone report
    style_n.leading = 12 

    # --- 1. PRE-PROCESSING FOR REPORTLAB (XML Safety) ---
    # Convert Markdown Bold (**) to ReportLab Bold (<b>)
    text = markdown_text.replace("**", "<b>")
    
    # Logic to ensure every <b> has a closing </b>
    parts = text.split("<b>")
    clean_parts = [parts[0]]
    for part in parts[1:]:
        if "<b>" not in part and "</b>" not in part:
            # If the AI forgot the closing tag, we add it at the end of the line
            clean_parts.append(part + "</b>")
        else:
            clean_parts.append(part)
    text = "".join(clean_parts)

    # Replace newlines with PDF line breaks
    text = text.replace("\n", "<br/>")

    # Final escape for illegal XML characters like &, <, > that aren't tags
    text = text.replace("&", "&amp;").replace(" < ", " &lt; ").replace(" > ", " &gt; ")

    # --- 2. BUILD PDF ---
    story = []
    story.append(Paragraph("<b>PROJECT MANAGEMENT REPORT</b>", styles["Title"]))
    story.append(Spacer(1, 15))
    
    try:
        # We wrap the text in a <para> tag to ensure it's treated as a single block
        p = Paragraph(f"<para>{text}</para>", style_n)
        story.append(p)
    except Exception as e:
        # FAILSAFE: If the tags are still broken, strip all tags and print plain text
        st.warning("Formatting issues detected; generating plain-text PDF.")
        plain_text = markdown_text.replace("**", "").replace("#", "")
        p = Paragraph(plain_text, style_n)
        story.append(p)
    
    doc.build(story)
    pdf_value = buffer.getvalue()
    buffer.close()
    return pdf_value

# --- 3. STREAMLIT UI ---
st.set_page_config(page_title="AI Video Planner", layout="wide")

with st.sidebar:
    st.title("⚙️ Project Settings")
    output_lang = st.selectbox("Output Language:", ["English", "Hindi", "Spanish", "German", "Bengali"])
    user_goal = st.text_area("Custom Goal:", placeholder="e.g. Summarize code...")
    universal_mode = st.toggle("Universal Translation", value=True)

st.title("🚀 Universal AI Video Action Planner")
video_url = st.text_input("YouTube URL:")

if st.button("Generate My Action Plan"):
    if video_url:
        v_id = get_video_id(video_url)
        if v_id:
            with st.spinner("Fetching Transcript..."):
                raw_text = get_transcript(v_id)
            
            if raw_text:
                with st.spinner(f"AI Synthesis in {output_lang}..."):
                    sys_instr = (
                        f"Professional project manager. Write ONLY in {output_lang}. "
                        "Use Markdown bold headers and checklists."
                    )
                    if universal_mode:
                        sys_instr += " Translate from Hindi/Hinglish if needed."

                    try:
                        # USING 1.5-FLASH FOR STABILITY DURING PRESENTATION
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            contents=f"Goal: {user_goal}\n\nTranscript: {raw_text}",
                            config=types.GenerateContentConfig(system_instruction=sys_instr)
                        )
                        
                        plan = response.text
                        st.success(f"Plan Generated Successfully in {output_lang}!")
                        st.markdown("---")
                        st.markdown(plan)

                        # Generate and Show Download Button immediately
                        pdf_data = generate_pdf(plan)
                        st.download_button(
                            label="📥 Download Action Plan (PDF)",
                            data=pdf_data,
                            file_name=f"Action_Plan_{output_lang}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error("🤖 The AI engine is currently busy. Please wait 10 seconds and click 'Generate' again.")
                        st.info(f"Technical Detail: {e}")
        else:
            st.error("Invalid YouTube URL.")