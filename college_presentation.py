import streamlit as st
import os
import re
import io
import time
from dotenv import load_dotenv

# Core logic imports
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types

# PDF Generation imports
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY

# --- 1. CONFIGURATION ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 2. LOGIC FUNCTIONS ---

def get_video_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_transcript(video_id):
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
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
    )
    styles = getSampleStyleSheet()
    style_n = styles["Normal"]
    style_n.alignment = TA_JUSTIFY
    style_n.fontName = 'Helvetica'
    style_n.fontSize = 10 
    style_n.leading = 12 

    text = markdown_text.replace("**", "<b>")
    parts = text.split("<b>")
    clean_parts = [parts[0]]
    for part in parts[1:]:
        if "<b>" not in part and "</b>" not in part:
            clean_parts.append(part + "</b>")
        else:
            clean_parts.append(part)
    text = "".join(clean_parts).replace("\n", "<br/>")
    text = text.replace("&", "&amp;").replace(" < ", " &lt; ").replace(" > ", " &gt; ")

    story = [Paragraph("<b>AI GENERATED ANALYSIS REPORT</b>", styles["Title"]), Spacer(1, 15)]
    try:
        story.append(Paragraph(f"<para>{text}</para>", style_n))
    except:
        plain_text = markdown_text.replace("**", "").replace("#", "")
        story.append(Paragraph(plain_text, style_n))
    
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

    st.divider()
    st.subheader("⚡ Quick Actions")
    
    task_type = None
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📝 Quiz", use_container_width=True): task_type = "Quiz"
        if st.button("📚 Notes", use_container_width=True): task_type = "Notes"
    with col_b:
        if st.button("🎴 Flashcards", use_container_width=True): task_type = "Flashcards"
        if st.button("📋 Summary", use_container_width=True): task_type = "Summary"
    
    if st.button("📂 Question Bank", use_container_width=True):
        task_type = "Question Bank"

st.title("🚀 Universal AI Video Action Planner")

video_url = st.text_input(
    "Enter YouTube Video URL:", 
    placeholder="https://www.youtube.com/watch?v=...",
    key="main_url_input"
)

main_gen_btn = st.button("Generate Full Action Plan", use_container_width=True)

# --- 4. EXECUTION LOGIC (WITH CHUNKING) ---
final_instruction = None
active_mode = ""

if main_gen_btn:
    final_instruction = "Create a professional, chronological action plan with bold headers and checklists."
    active_mode = "Action Plan"
elif task_type:
    instructions = {
        "Quiz": "Generate a 5-question Multiple Choice Quiz with an answer key.",
        "Notes": "Generate comprehensive, structured study notes with key definitions.",
        "Flashcards": "Generate 5-10 Flashcard-style Q&A pairs.",
        "Summary": "Generate a concise 5-bullet point executive summary.",
        "Question Bank": "Generate a categorized Question Bank (Short, Medium, and Long answers)."
    }
    final_instruction = instructions[task_type]
    active_mode = task_type

if final_instruction:
    if not video_url:
        st.warning("⚠️ Please enter a YouTube URL first!")
    else:
        v_id = get_video_id(video_url)
        if v_id:
            with st.spinner("Step 1: Fetching Transcript..."):
                raw_text = get_transcript(v_id)
            
            if raw_text:
                # --- NEW: CHUNKING & COMBINING LOGIC ---
                # We split the text into chunks of 30,000 characters (~40 mins of video)
                chunk_size = 30000 
                chunks = [raw_text[i:i + chunk_size] for i in range(0, len(raw_text), chunk_size)]
                
                combined_output = []
                
                # We only process up to 3 chunks to stay within Free Tier daily limits 
                # but cover up to 2 hours of video.
                for idx, chunk in enumerate(chunks[:3]):
                    with st.spinner(f"Step 2: Processing Part {idx+1} of {len(chunks[:3])}..."):
                        sys_instr = (
                            f"Professional project manager. Write ONLY in {output_lang}. "
                            f"Task: {final_instruction}. Use bold headers."
                        )
                        if universal_mode:
                            sys_instr += " Translate from Hindi/Hinglish if needed."

                        try:
                            # Using 1.5-flash for the highest TPM limit
                            response = client.models.generate_content(
                                model="gemini-3-flash-preview",
                                contents=f"Goal: {user_goal}\n\nTranscript Part {idx+1}: {chunk}",
                                config=types.GenerateContentConfig(system_instruction=sys_instr)
                            )
                            combined_output.append(response.text)
                            
                            # Small delay to avoid 'Requests Per Minute' (RPM) limit
                            if len(chunks) > 1:
                                time.sleep(2) 
                                
                        except Exception as e:
                            st.error(f"AI Error on Part {idx+1}: {e}")
                            break # Stop if we hit a hard limit

                if combined_output:
                    plan = "\n\n---\n\n".join(combined_output)
                    st.success(f"🎯 {active_mode} Ready!")
                    st.markdown("---")
                    st.markdown(plan)

                    # Export Buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📥 Download PDF",
                            data=generate_pdf(plan),
                            file_name=f"{active_mode}.pdf",
                            mime="application/pdf"
                        )
                    with col2:
                        st.download_button(
                            label="📝 Download Markdown",
                            data=plan,
                            file_name=f"{active_mode}.md",
                            mime="text/markdown"
                        )
        else:
            st.error("Invalid YouTube URL format.")