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
    initial_sidebar_state="expanded"
)

# --- 2. CUSTOM CSS (Visuals) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
    h1 { font-family: 'Inter', sans-serif; background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .css-card { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e0e0e0; }
    div.stButton > button { background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%); color: white; border: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; }
    .footer { position: fixed; bottom: 0; left: 0; width: 100%; background-color: white; text-align: center; padding: 10px; font-size: 12px; color: #888; border-top: 1px solid #eaeaea; }
</style>
""", unsafe_allow_html=True)

# --- 3. PDF STYLING (The Print Layout) ---
# FIX: Removed 'text-transform: uppercase' from admonition-title
# FIX: Added 'ul, ol' styles to ensure lists work inside callouts
PDF_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond&family=Lato:wght@400;700&display=swap');
    @page { size: A4; margin: 20mm; }
    body { font-family: "EB Garamond", serif; font-size: 12pt; line-height: 1.6; color: #222; }
    
    h1, h2, h3, h4 { font-family: "Lato", sans-serif; page-break-after: avoid; color: #000; margin-top: 1.5em; }
    h1 { border-bottom: 2px solid #000; text-align: center; margin-top: 0; }
    
    /* Tables */
    table { width: 100%; border-collapse: collapse; margin: 1em 0; page-break-inside: avoid; }
    th, td { border: 1px solid #ccc; padding: 6px; vertical-align: top; }
    
    /* Code Blocks */
    pre { background: #f4f4f4; padding: 10px; border-radius: 5px; white-space: pre-wrap; page-break-inside: avoid; font-family: monospace; font-size: 0.9em; }
    
    /* Callouts (Admonitions) - FIXED */
    .admonition { 
        border-left: 5px solid #448aff; 
        background: #f8f9fa; 
        padding: 15px; 
        margin: 1.5em 0; 
        page-break-inside: avoid; 
        border-radius: 0 4px 4px 0; 
    }
    .admonition-title { 
        font-weight: bold; 
        display: block; 
        font-family: "Lato", sans-serif; 
        margin-bottom: 8px;
        color: #333;
        /* Removed text-transform: uppercase to fix all-caps bug */
    }
    
    /* Callout Colors */
    .admonition.note { border-color: #448aff; background: #eff6ff; }
    .admonition.tip { border-color: #22c55e; background: #f0fdf4; }
    .admonition.warning { border-color: #eab308; background: #fefce8; }
    .admonition.danger { border-color: #ef4444; background: #fef2f2; }
    .admonition.example { border-color: #a855f7; background: #f3e8ff; }

    /* Lists inside callouts need margin reset */
    .admonition ul, .admonition ol { margin-top: 0; padding-left: 20px; }
    
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

# --- 4. LOGIC FIXES ---
def process_obsidian_syntax(text):
    # 1. Strip Frontmatter
    if text.startswith("---"):
        try: _, _, text = text.split("---", 2)
        except: pass

    # 2. Fix WikiLinks [[Link|Text]] -> **Text**
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'**\2**', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'**\1**', text)

    # 3. Process Callouts with Recursive Markdown Parsing
    lines = text.split('\n')
    output = []
    
    # State tracking
    in_callout = False
    callout_type = None
    callout_title = None
    callout_buffer = [] # Stores content lines to be parsed as markdown later

    def flush_callout():
        # This function compiles the buffered lines, runs markdown on them, 
        # and wraps them in the div.
        nonlocal in_callout, callout_buffer
        if not in_callout: return
        
        # Parse the inner markdown (Fixes bold/lists inside callouts)
        inner_text = "\n".join(callout_buffer)
        inner_html = markdown.markdown(inner_text, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
        
        display_title = callout_title if callout_title else callout_type.title()
        
        html_block = f"""
        <div class="admonition {callout_type.lower()}">
            <span class="admonition-title">{display_title}</span>
            {inner_html}
        </div>
        """
        output.append(html_block)
        callout_buffer = []
        in_callout = False

    for line in lines:
        # Check for start of callout: > [!NOTE] or > [!NOTE] Title
        match = re.match(r'>\s*\[!(\w+)\]\s*(.*)', line)
        
        if match:
            # If we were already in a callout, close it first
            if in_callout: flush_callout()
            
            in_callout = True
            callout_type = match.group(1)
            raw_title = match.group(2).strip()
            
            # LOGIC FIX: If title is very long, it's likely content, not a title.
            if len(raw_title) > 50:
                callout_title = callout_type.title() # Default title
                callout_buffer.append(raw_title)     # Treat text as body
            else:
                callout_title = raw_title
                
        elif in_callout:
            if line.strip() == "":
                callout_buffer.append("")
            elif line.startswith(">"):
                # Append content line (strip the leading '>')
                callout_buffer.append(line[1:].lstrip() if len(line) > 1 else "")
            else:
                # Line doesn't start with '>', callout ended
                flush_callout()
                output.append(line)
        else:
            output.append(line)

    if in_callout: flush_callout()

    return "\n".join(output)

def render_pdf(html_content):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Streamlit Cloud specific binary path
    service = Service("/usr/bin/chromedriver") 
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        with open("temp.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        driver.get("file://" + os.path.abspath("temp.html"))
        
        # Wait slightly longer for complex Mermaid diagrams
        time.sleep(4)
        
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            'printBackground': True,
            'paperWidth': 8.27, 'paperHeight': 11.69,
            'marginTop': 0, 'marginBottom': 0, 'marginLeft': 0, 'marginRight': 0
        })
        return base64.b64decode(pdf_data['data'])
    finally:
        driver.quit()

# --- 5. UI LAYOUT ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Obsidian_RGB_logo_2020.svg/1024px-Obsidian_RGB_logo_2020.svg.png", width=50)
    st.markdown("### Instructions")
    st.markdown("""
    1. Upload your `.md` file.
    2. Click **Generate PDF**.
    3. Diagrams & Math are preserved.
    """)
    st.caption("v2.0 - Fixed Callouts")

col1, col2 = st.columns([1, 1])
with col1:
    st.title("Markdown to PDF")
    st.markdown("### Professional Converter")
    st.markdown("Supports **Mermaid**, **MathJax**, and **Obsidian Callouts** properly.")

with col2:
    with st.container():
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload .md file", type=["md"])
        st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file:
    st.success(f"📄 Loaded: {uploaded_file.name}")
    
    if st.button("✨ Generate PDF"):
        with st.status("🚀 Processing...", expanded=True) as status:
            st.write("⚙️ Parsing Markdown & Callouts...")
            content = uploaded_file.read().decode("utf-8")
            
            # 1. Process Callouts (Markdown -> HTML for blocks)
            # This logic now handles the **bold** and - list items inside the blue boxes
            processed_md_parts = process_obsidian_syntax(content)
            
            # 2. Convert the Rest of the Document
            # We use the 'markdown' lib again for the main body, but since callouts
            # are already HTML <div>s, we need to be careful not to break them.
            # However, standard markdown usually leaves block HTML alone, which is exactly what we want.
            html_body = markdown.markdown(processed_md_parts, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
            
            # 3. Mermaid Fix
            html_body = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>', r'<div class="mermaid">\1</div>', html_body, flags=re.DOTALL)
            
            filename = uploaded_file.name.replace(".md", "")
            final_html = f"<html><head>{PDF_STYLE}</head><body><h1>{filename}</h1>{html_body}{SCRIPTS}</body></html>"
            
            st.write("📸 Rendering PDF...")
            try:
                pdf_bytes = render_pdf(final_html)
                status.update(label="✅ Success!", state="complete", expanded=False)
                st.balloons()
                
                # Center download button
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2:
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name=f"{filename}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")

st.markdown('<div class="footer">Fixed Formatting Update</div>', unsafe_allow_html=True)
