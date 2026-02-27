import streamlit as st
import markdown
import os
import time
import base64
import re
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# --- PAGE CONFIG ---
st.set_page_config(page_title="Obsidian to PDF", page_icon="📄", layout="centered")

# --- CSS & JS INJECTION ---
# This CSS ensures A4 printing, prevents cutting diagrams in half, and styles callouts
STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond&family=Lato:wght@400;700&display=swap');
    @page { size: A4; margin: 20mm; }
    body { font-family: "EB Garamond", serif; font-size: 12pt; line-height: 1.6; color: #222; }
    
    h1, h2, h3 { font-family: "Lato", sans-serif; page-break-after: avoid; color: #000; }
    h1 { border-bottom: 2px solid #000; text-align: center; margin-top: 0; }
    
    /* Tables & Code */
    table { width: 100%; border-collapse: collapse; margin: 1em 0; page-break-inside: avoid; }
    th, td { border: 1px solid #ccc; padding: 6px; }
    pre { background: #f4f4f4; padding: 10px; border-radius: 5px; white-space: pre-wrap; page-break-inside: avoid; }
    
    /* Obsidian Callouts */
    .admonition { border-left: 4px solid #448aff; background: #f8f9fa; padding: 10px 15px; margin: 1em 0; page-break-inside: avoid; border-radius: 0 4px 4px 0; }
    .admonition-title { font-weight: bold; text-transform: uppercase; font-size: 0.85em; display: block; font-family: sans-serif; margin-bottom: 5px; }
    .admonition.note { border-color: #448aff; background: #eff6ff; }
    .admonition.tip { border-color: #22c55e; background: #f0fdf4; }
    .admonition.warning { border-color: #eab308; background: #fefce8; }
    .admonition.danger { border-color: #ef4444; background: #fef2f2; }

    /* Diagrams & Images */
    .mermaid { display: flex; justify-content: center; margin: 1.5em auto; page-break-inside: avoid; }
    img { max-width: 100%; page-break-inside: avoid; }
</style>
"""

# Scripts for Mermaid (Diagrams) and MathJax (Equations)
SCRIPTS = """
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true, theme:'neutral', securityLevel:'loose'});</script>
<script>
MathJax = {
  tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] },
  svg: { fontCache: 'global' }
};
</script>
<script type="text/javascript" id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
"""

def process_obsidian_syntax(text):
    # 1. Remove Frontmatter (YAML)
    if text.startswith("---"):
        try: _, _, text = text.split("---", 2)
        except: pass

    # 2. Convert WikiLinks [[Link]] -> **Link**
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'**\2**', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'**\1**', text)

    # 3. Process Callouts ( > [!INFO] Title )
    lines = text.split('\n')
    output = []
    in_callout = False
    
    for line in lines:
        match = re.match(r'>\s*\[!(\w+)\]\s*(.*)', line)
        if match:
            if in_callout: output.append("</div>") # Close previous
            c_type, c_title = match.groups()
            c_title = c_title if c_title else c_type.title()
            output.append(f'<div class="admonition {c_type.lower()}"><span class="admonition-title">{c_title}</span>')
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

def convert_to_html(md_text, filename):
    # Convert MD to HTML
    html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'nl2br'])
    
    # Fix Mermaid Code Blocks for JS rendering
    html_body = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>', r'<div class="mermaid">\1</div>', html_body, flags=re.DOTALL)

    return f"""<!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8">{STYLE}</head>
    <body>
        <h1>{filename}</h1>
        {html_body}
        {SCRIPTS}
    </body>
    </html>"""

def print_to_pdf(html_content):
    # --- SELENIUM CLOUD CONFIGURATION ---
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Streamlit Cloud installs chromium here:
    service = Service("/usr/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Save HTML locally
        with open("temp.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        # Open in Headless Browser
        driver.get("file://" + os.path.abspath("temp.html"))
        
        # Wait for Mermaid/MathJax to render
        time.sleep(3) 
        
        # Print to PDF via CDP
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            'printBackground': True,
            'paperWidth': 8.27, 'paperHeight': 11.69, # A4
            'marginTop': 0, 'marginBottom': 0, 'marginLeft': 0, 'marginRight': 0
        })
        
        return base64.b64decode(pdf_data['data'])
        
    finally:
        driver.quit()

# --- MAIN UI ---
st.title("📄 Obsidian to PDF Converter")
st.markdown("Upload your `.md` file. We support **Mermaid Diagrams**, **MathJax**, and **Callouts**.")

uploaded_file = st.file_uploader("Choose a Markdown file", type=["md"])

if uploaded_file:
    # Read file
    content = uploaded_file.read().decode("utf-8")
    filename = uploaded_file.name.replace(".md", "")
    
    if st.button("🚀 Convert to PDF"):
        with st.spinner("Processing Markdown & Rendering Chromium..."):
            try:
                # 1. Process Text
                clean_md = process_obsidian_syntax(content)
                # 2. Make HTML
                final_html = convert_to_html(clean_md, filename)
                # 3. Print PDF
                pdf_bytes = print_to_pdf(final_html)
                
                st.success("Conversion Successful!")
                
                # 4. Download Button
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=f"{filename}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")
