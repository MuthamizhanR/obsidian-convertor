
# 📄 Obsidian to PDF Converter

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Selenium](https://img.shields.io/badge/Selenium-Headless_Chrome-43B02A)

A robust, web-based tool to convert **Obsidian Markdown** notes into professional **PDFs**. 

Unlike standard converters, this tool preserves complex Obsidian features like **Callouts (Admonitions)**, **Mermaid Diagrams**, and **MathJax (LaTeX)** equations by rendering them in a headless Chromium browser before printing.

---

## ✨ Features

*   **🎨 Obsidian Callouts:** Renders colored blockquotes (Note, Tip, Warning, Danger, etc.) with proper styling.
*   **📊 Mermaid.js Support:** Automatically renders Flowcharts, Sequence diagrams, Gantt charts, etc.
*   **➗ MathJax Support:** Renders LaTeX equations (`$E=mc^2$`) perfectly.
*   **🔗 WikiLink Support:** Converts Obsidian-style `[[Links]]` into bold text.
*   **📄 A4 Layout:** Optimized CSS for A4 printing with smart page breaks (prevents cutting diagrams in half).
*   **🚀 Instant Preview:** Drag & drop interface with auto-generation.

---

## 🖼️ Screenshots

| Input (Markdown) | Output (PDF) |
| :--- | :--- |
| `> [!NOTE]` <br> `> This is a note.` | Renders as a blue box with a bold title. |
| ```mermaid graph TD; A-->B;``` | Renders as a sharp SVG diagram. |

*(Add your own screenshots here by uploading images to your repo and linking them)*

---

## 🚀 Quick Start (Web)

The easiest way to use this is via the web interface. 

1.  **[Click here to open the App](https://your-app-url.streamlit.app)** (Replace with your actual Streamlit URL).
2.  Upload your `.md` file.
3.  Wait for the processing bar.
4.  Click **Download PDF**.

---

## 🛠️ Local Installation

If you prefer to run this on your own machine:

### Prerequisites
*   Python 3.8+
*   Google Chrome or Chromium installed on your system.

### Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/md-to-pdf-converter.git
    cd md-to-pdf-converter
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the app:**
    ```bash
    streamlit run app.py
    ```

4.  Open your browser to `http://localhost:8501`.

---

## ☁️ Deploying to Streamlit Cloud

Want to host this yourself for free?

1.  Fork this repository.
2.  Go to **[Streamlit Community Cloud](https://streamlit.io/cloud)** and sign in with GitHub.
3.  Click **New App** and select your repository.
4.  **Crucial Step:** Ensure your repository has the `packages.txt` file containing `chromium` and `chromium-driver`. This allows Streamlit to install the browser engine.
5.  Click **Deploy**.

---

## 📝 Syntax Support Guide

### 1. Callouts
Standard Obsidian syntax is fully supported:
```markdown
> [!NOTE] Title
> This is a blue note block.

> [!WARNING]
> This is a yellow warning block.
2. Diagrams (Mermaid)

Use the standard code block syntax:

code
Markdown
download
content_copy
expand_less
```mermaid
graph TD;
    A[Start] --> B{Is it working?};
    B -- Yes --> C[Great!];
    B -- No --> D[Debug];
code
Code
download
content_copy
expand_less
### 3. Math (LaTeX)
```markdown
The quadratic formula is $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$.
📂 Project Structure
code
Text
download
content_copy
expand_less
.
├── app.py              # Main application logic
├── requirements.txt    # Python dependencies (Streamlit, Selenium, etc.)
├── packages.txt        # System dependencies (Chromium for Streamlit Cloud)
└── README.md           # This file
🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

📄 License

This project is open-source and available under the MIT License.

