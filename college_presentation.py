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

# --- 4. AI-DRIVEN KNOWLEDGE BASE ---
def get_recommendations(category_label):
    """Maps AI-detected categories to specific books and search queries."""
    domains = {
        "Data Structures": {
            "books": ["*Data Structures & Algorithms Made Easy* (Narasimha Karumanchi)", "*Fundamentals of Data Structure* (Sahni)"],
            "query": "Latest breakthroughs in Data Structures 2026"
        },
        "Algorithms": {
            "books": ["*Introduction to Algorithms* (CLRS)", "*Algorithm Design* (Kleinberg & Tardos)"],
            "query": "Advanced algorithmic research news 2026"
        },
        "Operating Systems": {
            "books": ["*Operating System Concepts* (Galvin)", "*Modern Operating Systems* (Tanenbaum)"],
            "query": "OS kernel developments and virtualization 2026"
        },
        "Computer Networks": {
            "books": ["*Computer Networking: A Top-Down Approach* (Kurose)", "*Data Communications* (Forouzan)"],
            "query": "Networking protocols and 6G news 2026"
        },
        "Databases": {
            "books": ["*Database System Concepts* (Korth)", "*Fundamentals of Database Systems* (Navathe)"],
            "query": "Distributed databases and NoSQL trends 2026"
        },
        "Python Programming": {
            "books": ["*Fluent Python* (Luciano Ramalho)", "*Automate the Boring Stuff* (Al Sweigart)"],
            "query": "Python language updates and PEP news 2026"
        },
        "Web Development": {
            "books": ["*Django for Beginners* (William Vincent)", "*Two Scoops of Django* (Feldroy)"],
            "query": "Web development frameworks and Django news 2026"
        },
        "Machine Learning & AI": {
            "books": ["*Hands-On Machine Learning* (Geron)", "*Artificial Intelligence: A Modern Approach* (Russell)"],
            "query": "Generative AI and Large Language Models news 2026"
        },
        "Cybersecurity": {
            "books": ["*The Web Application Hacker's Handbook*", "*Cryptography and Network Security* (Stallings)"],
            "query": "Cybersecurity threats and encryption news 2026"
        }
    }
    
    label = category_label.strip()
    if label in domains:
        return domains[label]["books"], domains[label]["query"]
    return ["Not in the keywords"], None

# --- 5. EXECUTION LOGIC (WITH AI CATEGORIZATION) ---
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
                chunk_size = 30000 
                chunks = [raw_text[i:i + chunk_size] for i in range(0, len(raw_text), chunk_size)]
                combined_output = []
                detected_category = "None"
                
                for idx, chunk in enumerate(chunks[:3]):
                    with st.spinner(f"Step 2: Processing Part {idx+1}..."):
                        # Added categorization instruction to the first chunk
                        cat_instr = ""
                        if idx == 0:
                            cat_instr = (
                                "\n\nCRITICAL: At the end of your response, identify the subject category "
                                "from this list: [Data Structures, Algorithms, Operating Systems, Computer Networks, "
                                "Databases, Python Programming, Web Development, Machine Learning & AI, Cybersecurity]. "
                                "Format exactly as: CATEGORY: <Label>"
                            )

                        sys_instr = (
                            f"Professional project manager. Write ONLY in {output_lang}. "
                            f"Task: {final_instruction}. Use bold headers.{cat_instr}"
                        )
                        
                        try:
                            response = client.models.generate_content(
                                model="gemini-3-flash-preview",
                                contents=f"Goal: {user_goal}\n\nTranscript Part {idx+1}: {chunk}",
                                config=types.GenerateContentConfig(system_instruction=sys_instr)
                            )
                            
                            chunk_text = response.text
                            # Extract Category Label if present
                            if "CATEGORY:" in chunk_text:
                                parts = chunk_text.split("CATEGORY:")
                                combined_output.append(parts[0])
                                detected_category = parts[1].strip().split('\n')[0]
                            else:
                                combined_output.append(chunk_text)

                            if len(chunks) > 1:
                                time.sleep(2) 
                        except Exception as e:
                            st.error(f"AI Error: {e}")
                            break 

                if combined_output:
                    plan = "\n\n---\n\n".join(combined_output)
                    
                    # FETCH DYNAMIC INFO USING AI DETECTED CATEGORY
                    books, news_query = get_recommendations(detected_category)
                    
                    st.success(f"🎯 {active_mode} Ready!")
                    st.markdown("---")
                    
                    col_left, col_right = st.columns([0.7, 0.3])
                    
                    with col_left:
                        st.markdown(plan)
                        ecol1, ecol2 = st.columns(2)
                        with ecol1:
                            st.download_button("📥 Download PDF", generate_pdf(plan), f"{active_mode}.pdf")
                        with ecol2:
                            st.download_button("📝 Download Markdown", plan, f"{active_mode}.md")

                    with col_right:
                        st.subheader("📚 Recommended Books")
                        if books[0] == "Not in the keywords":
                            st.warning("⚠️ Not in the keywords")
                        else:
                            st.success(f"Detected: {detected_category}")
                            for b in books:
                                st.info(b)
                        
                        st.divider()
                        st.subheader("📰 Recent News")
                        if news_query:
                            search_url = f"https://www.google.com/search?q={news_query.replace(' ', '+')}"
                            st.link_button(f"🚀 {detected_category} News 2026", search_url)
                        else:
                            st.write("No specific news category detected.")