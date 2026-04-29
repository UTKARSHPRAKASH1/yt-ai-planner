import streamlit as st
import os
import re
import requests
import io
import time
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from fpdf import FPDF

# --- 1. CONFIGURATION & CLIENT SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 2. LOGIC FUNCTIONS ---

def get_video_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_transcript(video_id):
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
            st.error(f"Supadata Error {response.status_code}")
            return None
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

def get_books_by_category(category_label):
    domains = {
        "Python Programming": ["*Fluent Python* (Luciano Ramalho)", "*Automate the Boring Stuff* (Al Sweigart)"],
        "Data Structures": ["*Data Structures & Algorithms Made Easy* (Narasimha Karumanchi)", "*Fundamentals of Data Structure* (Sahni)"],
        "Algorithms": ["*Introduction to Algorithms* (CLRS)", "*Algorithm Design* (Kleinberg & Tardos)"],
        "Web Development": ["*Django for Beginners* (William Vincent)", "*Two Scoops of Django* (Feldroy)"],
        "Operating Systems": ["*Operating System Concepts* (Galvin)", "*Modern Operating Systems* (Tanenbaum)"],
        "GATE Prep": ["*Discrete Mathematics* (Kenneth Rosen)", "*Computer Organization* (Hamacher)"],
        "Cybersecurity": ["*The Web Application Hacker's Handbook*", "*Cryptography and Network Security* (Stallings)"],
    }
    label = category_label.strip()
    return domains.get(label, ["Not in the keywords"]), label

# --- 3. STREAMLIT UI DESIGN ---
st.set_page_config(page_title="AI Video Planner", page_icon="🎯", layout="wide")

with st.sidebar:
    st.title("⚙️ Project Control")
    target_lang = st.selectbox("Output Language:", ["English", "Hindi", "Spanish", "French", "Bengali"])
    user_goal = st.text_area("Specific Focus/Goal:", placeholder="e.g., Only extract the Python code snippets...")
    
    st.divider()
    st.subheader("⚡ Quick Actions")
    task_type = None
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📝 Quiz"): task_type = "Quiz"
        if st.button("📚 Notes"): task_type = "Notes"
    with col_b:
        if st.button("🎴 Flashcards"): task_type = "Flashcards"
        if st.button("📋 Summary"): task_type = "Summary"
    
    if st.button("📂 Question Bank", use_container_width=True):
        task_type = "Question Bank"

st.title("YouTube Personal Project Manager using AI")
video_url = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

# Set the active instruction
if task_type:
    instructions = {
        "Quiz": "Generate a 5-question Multiple Choice Quiz with an answer key.",
        "Notes": "Generate comprehensive study notes.",
        "Flashcards": "Generate 5-10 Flashcard-style Q&A pairs.",
        "Summary": "Generate a concise 5-bullet point summary.",
        "Question Bank": "Generate a categorized Question Bank."
    }
    final_instr = instructions[task_type]
    active_mode = task_type
else:
    final_instr = "Create a professional, chronological action plan."
    active_mode = "Action Plan"

if st.button("Generate Plan") or task_type:
    if not video_url:
        st.warning("Please enter a valid URL.")
    else:
        v_id = get_video_id(video_url)
        if v_id:
            with st.spinner("🔍 Extracting intelligence..."):
                raw_transcript = get_transcript(v_id)
            
            if raw_transcript:
                # Chunking to handle long videos safely
                chunk_size = 30000
                chunks = [raw_transcript[i:i + chunk_size] for i in range(0, len(raw_transcript), chunk_size)]
                combined_output = []
                detected_cat = "Not in the keywords"

                for idx, chunk in enumerate(chunks[:3]):
                    with st.spinner(f"🧠 Synthesizing Part {idx+1}..."):
                        cat_tag = ""
                        if idx == 0:
                            cat_tag = "\n\nAt the end of your response, write CATEGORY: followed by one of: [Python Programming, Data Structures, Algorithms, Web Development, Operating Systems, GATE Prep, Cybersecurity]"
                        
                        sys_prompt = f"Professional Senior Project Manager. Write in {target_lang}. Task: {final_instr}. {cat_tag}"
                        
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            contents=f"Goal: {user_goal}\n\nTranscript: {chunk}",
                            config=types.GenerateContentConfig(system_instruction=sys_prompt)
                        )
                        
                        text = response.text
                        if "CATEGORY:" in text:
                            parts = text.split("CATEGORY:")
                            combined_output.append(parts[0])
                            detected_cat = parts[1].strip().split('\n')[0]
                        else:
                            combined_output.append(text)
                        
                        if len(chunks) > 1: time.sleep(2)

                if combined_output:
                    plan_text = "\n\n---\n\n".join(combined_output)
                    books, news_label = get_books_by_category(detected_cat)

                    st.success("🎯 Your Plan is Ready!")
                    
                    # --- Dual Pane Layout ---
                    col_main, col_side = st.columns([0.7, 0.3])
                    
                    with col_main:
                        st.markdown(plan_text)
                        st.divider()
                        # Export Buttons
                        e_col1, e_col2 = st.columns(2)
                        with e_col1:
                            st.download_button("📄 PDF", generate_pdf(plan_text), "Plan.pdf", "application/pdf")
                        with e_col2:
                            st.download_button("📝 Markdown", plan_text, "Plan.md", "text/markdown")

                    with col_side:
                        st.subheader("📚 Book Recommendations")
                        if books[0] == "Not in the keywords":
                            st.warning("⚠️ No specific domain matched.")
                        else:
                            st.info(f"Category: {news_label}")
                            for b in books:
                                st.write(b)
                        
                        st.divider()
                        st.subheader("📰 Recent News")
                        if news_label != "Not in the keywords":
                            search_url = f"https://www.google.com/search?q={news_label.replace(' ', '+')}+latest+trends+2026"
                            st.link_button(f"🚀 View {news_label} News", search_url)
                        else:
                            st.write("Enter a CS link for news.")