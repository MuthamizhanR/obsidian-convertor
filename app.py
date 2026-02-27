import streamlit as st
import markdown
import os
import time
import base64
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="Obsidian -> PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed" # Collapsed by default for cleaner look
)

# --- 2. CSS STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    /* App Background */
    .stApp { background-color: #f4f6f9; font-family: 'Inter', sans-serif; }
    
    /* Header */
    h1 { 
        font-family: 'Inter', sans-serif; 
        font-weight: 800; 
        color: #1f2937;
    }
    
    /* Card Style */
    .css-card { 
        background-color: white; 
        padding: 25px; 
        border-radius: 12px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); 
        border: 1px solid #e5e7eb;
        text-align: center;
    }
    
    /* Download Button - Make it Big and Green */
    div.stButton > button { 
        background-color: #10b981; 
        color: white; 
        border: none; 
        padding: 15px 32px; 
        font-size: 18px;
        border-radius: 8px; 
        font-weight: 700; 
        width: 100%;
        transition: all 0.2s;
    }
    div.stButton > button:hover { 
        background-color: #059669; 
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        color: white;
    }
    
    /* Hide the default streamlit menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. PDF CSS (The Look of the Document) ---
PDF_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond&family=Lato:wght@400;700&display=swap');
    @page { size: A4; margin: 20mm; }
    
    body { 
        font-family: "EB Garamond", serif; 
        font-size: 12.5pt; 
        line-height: 1.65; 
        color: #111; 
        text-align: justify;
    }
    
    h1, h2, h3, h4 { 
        font-family: "Lato", sans-serif; 
        page-break-after: avoid; 
        color: #000; 
        margin-top: 1.5em; 
        margin-bottom: 0.5em;
    }
    h1 { border-bottom: 2px solid #000; text-align: center; margin-top: 0; font-size: 24pt; }
    h2 { border-bottom: 1px solid #ccc; font-size: 18pt; }
    
    /* Tables */
    table { width: 100%; border-collapse: collapse; margin: 1em 0; page-break-inside: avoid; font-family: "Lato", sans-serif; font-size: 10pt; }
    th, td { border: 1px solid #ccc; padding: 8px; vertical-align: top; text-align: left; }
    th { background-color: #f3f4f6; font-weight: bold; }
    
    /* Code Blocks */
    pre { 
        background: #f1f5f9; 
        padding: 12px; 
        border-radius: 6px; 
        white-space: pre-wrap; 
        page-break-inside: avoid; 
        font-family: "Courier New", monospace; 
        font-size: 0.9em; 
        border: 1px solid #e2e8f0;
    }
    
    /* Callouts (Admonitions) - CRITICAL FIX */
    .admonition { 
        border-left: 5px solid #3b82f6; 
        background: #eff6ff; 
        padding: 15px; 
        margin: 1.5em 0; 
        page-break-inside: avoid; 
        border-radius: 4px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .admonition-title { 
        font-weight: bold; 
        display: block; 
        font-family: "Lato", sans-serif; 
        margin-bottom: 8px;
        color: #1e3a8a;
        font-size: 1em;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Callout Colors */
    .admonition.note { border-left-color: #3b82f6; background: #eff6ff; } /* Blue */
    .admonition.tip { border-left-color: #10b981; background: #ecfdf5; } /* Green */
    .admonition.warning { border-left-color: #f59e0b; background: #fffbeb; } /* Yellow */
    .admonition.danger { border-left-color: #ef4444; background: #fef2f2; } /* Red */
    .admonition.example { border-left-color: #8b5cf6; background: #f5f3ff; } /* Purple */
    .admonition.quote { border-left-color: #64748b; background: #f8fafc; } /* Grey */

    /* Lists inside callouts */
    .admonition ul, .admonition ol { margin-bottom: 0; padding-left: 20px; }
    
    /* Diagrams */
    .mermaid { display: flex; justify-content: center; margin: 2em auto; page-break-inside: avoid; }
    img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
</style>
"""

SCRIPTS = """
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true, theme:'neutral', securityLevel:'loose'});</script>
<script>MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']]},svg:{fontCache:'global'}};</script>
<script type="text/javascript" id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
"""

# --- 4. ROBUST PARSING ENGINE (The Fix) ---
def parse_markdown_chunks(text):
    """
    Parses Markdown by splitting it into 'Normal' chunks and 'Callout' chunks.
    This prevents the HTML <div> tags from being escaped by the markdown parser.
    """
    # 1. Frontmatter Removal
    if text.startswith("---"):
        try: _, _, text = text.split("---", 2)
        except: pass

    # 2. Fix Obsidian WikiLinks
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'**\2**', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'**\1**', text)

    lines = text.split('\n')
    final_html_parts = []
    
    # Buffers
    normal_lines = []
    callout_lines = []
    
    # State
    in_callout = False
    callout_type = "note"
    callout_title = ""

    def render_normal():
        if normal_lines:
            # Render standard markdown
            md_text = "\n".join(normal_lines)
            html = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
            
            # Fix Mermaid blocks in normal text
            html = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>', r'<div class="mermaid">\1</div>', html, flags=re.DOTALL)
            
            final_html_parts.append(html)
            normal_lines.clear()

    def render_callout():
        if callout_lines:
            # Render inner markdown
            inner_text = "\n".join(callout_lines)
            inner_html = markdown.markdown(inner_text, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
            
            # Fix Mermaid inside callouts
            inner_html = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>', r'<div class="mermaid">\1</div>', inner_html, flags=re.DOTALL)
            
            # Create the DIV manually (The parser never sees this, so it can't break it)
            display_title = callout_title if callout_title else callout_type.title()
            
            block = f"""
            <div class="admonition {callout_type.lower()}">
                <span class="admonition-title">{display_title}</span>
                {inner_html}
            </div>
            """
            final_html_parts.append(block)
            callout_lines.clear()

    # --- Line by Line Parser ---
    for line in lines:
        # Check for start of callout: > [!TYPE] Title
        match = re.match(r'>\s*\[!(\w+)\]\s*(.*)', line)
        
        if match:
            # Switch State: Normal -> Callout
            render_normal()
            if in_callout: render_callout() # Close previous if nested (rare)
            
            in_callout = True
            callout_type = match.group(1)
            raw_title = match.group(2).strip()
            
            # Handle empty titles or long text on first line
            if len(raw_title) > 0:
                callout_title = raw_title
            else:
                callout_title = ""
                
        elif in_callout:
            if line.strip() == "":
                callout_lines.append("")
            elif line.startswith(">"):
                # It's part of the callout, strip the '>'
                content = line.lstrip('>').lstrip()
                # If it's empty, keep it empty (paragraph break)
                callout_lines.append(content if len(content) > 0 else "")
            else:
                # Line does NOT start with '>', callout ended.
                render_callout()
                in_callout = False
                normal_lines.append(line)
        else:
            normal_lines.append(line)

    # Flush remaining buffers
    if in_callout: render_callout()
    render_normal()

    return "\n".join(final_html_parts)

def generate_pdf(html_content):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        with open("temp.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        driver.get("file://" + os.path.abspath("temp.html"))
        time.sleep(4) # Wait for Mermaid/MathJax
        
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            'printBackground': True,
            'paperWidth': 8.27, 'paperHeight': 11.69,
            'marginTop': 0, 'marginBottom': 0, 'marginLeft': 0, 'marginRight': 0
        })
        return base64.b64decode(pdf_data['data'])
    finally:
        driver.quit()

# --- 5. UI LAYOUT ---

st.title("Obsidian to PDF Converter")
st.markdown("Upload your note, and the PDF will generate **automatically**.")

# Custom File Uploader Area
with st.container():
    uploaded_file = st.file_uploader(" ", type=["md"], label_visibility="collapsed")

if uploaded_file:
    # AUTO START LOGIC
    # As soon as file is present, we start working.
    
    st.info(f"Processing: **{uploaded_file.name}**")
    
    # Progress Bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Read
        content = uploaded_file.read().decode("utf-8")
        progress_bar.progress(20)
        
        # Step 2: Parse (The robust way)
        status_text.text("Parsing Markdown & Callouts...")
        html_body = parse_markdown_chunks(content)
        progress_bar.progress(50)
        
        # Step 3: Combine
        filename = uploaded_file.name.replace(".md", "")
        final_html = f"<html><head>{PDF_STYLE}</head><body><h1>{filename}</h1>{html_body}{SCRIPTS}</body></html>"
        
        # Step 4: Render
        status_text.text("Rendering PDF in Chromium...")
        pdf_bytes = generate_pdf(final_html)
        progress_bar.progress(100)
        
        status_text.empty() # Clear status
        progress_bar.empty() # Clear bar
        
        # Success Area
        st.success("✅ Conversion Complete!")
        
        # BIG DOWNLOAD BUTTON
        st.download_button(
            label="⬇️ DOWNLOAD PDF NOW",
            data=pdf_bytes,
            file_name=f"{filename}.pdf",
            mime="application/pdf"
        )
        
    except Exception as e:
        st.error(f"Error: {e}")
