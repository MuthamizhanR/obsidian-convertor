import streamlit as st
import markdown
import os
import time
import base64
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# 1. PAGE CONFIGURATION (Must be first)
st.set_page_config(
    page_title="Markdown -> PDF",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CUSTOM STYLING (The "Character" Injection)
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

    /* General App Styling */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Inter', sans-serif;
    }

    /* Header Styling */
    h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 10px;
    }

    /* Custom Card Containers */
    .css-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
    }

    /* Button Styling */
    div.stButton > button {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        color: white;
        border: none;
        padding: 12px 28px;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(37, 117, 252, 0.2);
        color: white;
    }

    /* File Uploader styling tweak */
    div[data-testid="stFileUploader"] {
        border: 2px dashed #a0a0a0;
        border-radius: 10px;
        padding: 20px;
        background-color: #ffffff;
    }

    /* Footer */
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: white;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        color: #888;
        border-top: 1px solid #eaeaea;
    }
</style>
""", unsafe_allow_html=True)

# --- BACKEND LOGIC (Same engine, hidden from UI) ---
PDF_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond&family=Lato:wght@400;700&display=swap');
    @page { size: A4; margin: 20mm; }
    body { font-family: "EB Garamond", serif; font-size: 12pt; line-height: 1.6; color: #222; }
    h1, h2, h3 { font-family: "Lato", sans-serif; page-break-after: avoid; color: #000; }
    h1 { border-bottom: 2px solid #000; text-align: center; margin-top: 0; }
    table { width: 100%; border-collapse: collapse; margin: 1em 0; page-break-inside: avoid; }
    th, td { border: 1px solid #ccc; padding: 6px; }
    pre { background: #f4f4f4; padding: 10px; border-radius: 5px; white-space: pre-wrap; page-break-inside: avoid; }
    .admonition { border-left: 4px solid #448aff; background: #f8f9fa; padding: 10px 15px; margin: 1em 0; page-break-inside: avoid; border-radius: 0 4px 4px 0; }
    .admonition-title { font-weight: bold; text-transform: uppercase; font-size: 0.85em; display: block; font-family: sans-serif; margin-bottom: 5px; }
    .admonition.note { border-color: #448aff; background: #eff6ff; }
    .admonition.tip { border-color: #22c55e; background: #f0fdf4; }
    .admonition.warning { border-color: #eab308; background: #fefce8; }
    .mermaid { display: flex; justify-content: center; margin: 1.5em auto; page-break-inside: avoid; }
    img { max-width: 100%; page-break-inside: avoid; }
</style>
"""

SCRIPTS = """
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true, theme:'neutral'});</script>
<script>MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']]},svg:{fontCache:'global'}};</script>
<script type="text/javascript" id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
"""

def process_text(text):
    if text.startswith("---"):
        try: _, _, text = text.split("---", 2)
        except: pass
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'**\2**', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'**\1**', text)
    lines = text.split('\n')
    output = []
    in_callout = False
    for line in lines:
        match = re.match(r'>\s*\[!(\w+)\]\s*(.*)', line)
        if match:
            if in_callout: output.append("</div>")
            c_type, c_title = match.groups()
            output.append(f'<div class="admonition {c_type.lower()}"><span class="admonition-title">{c_title or c_type.title()}</span>')
            in_callout = True
        elif in_callout and not line.startswith(">"):
            output.append("</div>")
            in_callout = False
            output.append(line)
        elif in_callout and line.startswith(">"):
            output.append(line[1:].strip())
        else:
            output.append(line)
    if in_callout: output.append("</div>")
    return "\n".join(output)

def render_pdf(html_content):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    service = Service("/usr/bin/chromedriver") # Streamlit Cloud Path
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        with open("temp.html", "w", encoding="utf-8") as f: f.write(html_content)
        driver.get("file://" + os.path.abspath("temp.html"))
        time.sleep(3)
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {'printBackground': True, 'paperWidth': 8.27, 'paperHeight': 11.69, 'marginTop': 0, 'marginBottom': 0, 'marginLeft': 0, 'marginRight': 0})
        return base64.b64decode(pdf_data['data'])
    finally:
        driver.quit()

# --- SIDEBAR (Instructions) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Obsidian_RGB_logo_2020.svg/1024px-Obsidian_RGB_logo_2020.svg.png", width=50)
    st.header("How to use")
    st.markdown("""
    1. **Export** your Obsidian note.
    2. **Upload** the `.md` file here.
    3. **Wait** for the magic to happen.
    
    ### Supports:
    - ✅ **Mermaid** Diagrams
    - ✅ **MathJax** Equations ($E=mc^2$)
    - ✅ **Callouts** (Note, Tip, etc.)
    """)
    st.divider()
    st.caption("Built with Python & Selenium")

# --- MAIN LAYOUT ---
col1, col2 = st.columns([1, 1])

with col1:
    st.title("Markdown to PDF")
    st.markdown("### The professional converter for your notes.")
    st.markdown("Transform your raw Obsidian notes into beautiful, printable PDFs without losing your diagrams or math.")

with col2:
    # Use a container to create a "Card" effect
    with st.container():
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Drop your markdown file here", type=["md"])
        st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file:
    # Show file stats in a nice way
    st.success(f"📄 File loaded: **{uploaded_file.name}** ({round(uploaded_file.size/1024, 2)} KB)")
    
    # Preview Section
    with st.expander("👀 Preview Content"):
        content = uploaded_file.read().decode("utf-8")
        st.code(content[:500] + "...", language="markdown")

    # The Big Button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✨ Generate PDF Now"):
        
        # New Status Spinner
        with st.status("🚀 Starting Engine...", expanded=True) as status:
            st.write("⚙️ Parsing Markdown syntax...")
            clean_md = process_text(content)
            
            st.write("🎨 Constructing HTML layout...")
            filename = uploaded_file.name.replace(".md", "")
            html_body = markdown.markdown(clean_md, extensions=['tables', 'fenced_code', 'nl2br'])
            html_body = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>', r'<div class="mermaid">\1</div>', html_body, flags=re.DOTALL)
            
            final_html = f"<html><head>{PDF_STYLE}</head><body><h1>{filename}</h1>{html_body}{SCRIPTS}</body></html>"
            
            st.write("📸 Snapshotting with Chromium (this takes 3s)...")
            try:
                pdf_bytes = render_pdf(final_html)
                status.update(label="✅ PDF Ready!", state="complete", expanded=False)
                
                # Success Logic
                st.balloons()
                
                # Columns for download button to center it
                d_col1, d_col2, d_col3 = st.columns([1,2,1])
                with d_col2:
                    st.download_button(
                        label="📥 Download Your PDF",
                        data=pdf_bytes,
                        file_name=f"{filename}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Something went wrong: {e}")

# Footer
st.markdown('<div class="footer">Made with ❤️ for the Obsidian Community</div>', unsafe_allow_html=True)
