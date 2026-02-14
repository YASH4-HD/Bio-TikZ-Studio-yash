import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
import streamlit as st
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageOps

# Disable the safety limit globally
Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="Bio-TikZ Studio", page_icon="🧬", layout="wide")

OUTPUT_PROFILES = {
    "Custom": {"dpi_scale": 4, "auto_crop": True, "line_thickness": "thick"},
    "Nature Journal": {"dpi_scale": 6, "auto_crop": True, "line_thickness": "thin"},
    "Conference Poster": {"dpi_scale": 4, "auto_crop": True, "line_thickness": "ultra thick"},
    "Grant/Investor Deck": {"dpi_scale": 3, "auto_crop": True, "line_thickness": "thick"},
}

TIKZ_TEMPLATES = {
    "Mitochondria (Bezier)": r"""\begin{tikzpicture}
% Outer membrane
\draw[thick] (0,0) ellipse (4 and 2);
% Inner membrane (cristae style)
\draw[thick] (-3,0) 
.. controls (-2.5,1) and (-1.5,1) .. (-1,0)
.. controls (-0.5,-1) and (0.5,-1) .. (1,0)
.. controls (1.5,1) and (2.5,1) .. (3,0);
% Labels
\node at (0,2.4) {\textbf{Outer Membrane}};
\node at (0,-2.4) {\textbf{Inner Membrane}};
\node at (0,0.8) {\textit{Matrix}};
\end{tikzpicture}""",
    "Cell Signaling": r"""\begin{tikzpicture}
\node[circle, draw, fill=blue!15, minimum size=2.2cm] (cell) at (0,0) {Cell};
\node[rectangle, draw, fill=green!20, minimum width=1.5cm, minimum height=0.6cm] (rec) at (0,1.8) {Receptor};
\draw[->, thick] (rec) -- (cell);
\end{tikzpicture}""",
    "Immune Synapse": r"""\begin{tikzpicture}
\node[circle, draw, fill=red!15, minimum size=2cm] (tcell) at (-1.8,0) {T Cell};
\node[circle, draw, fill=orange!15, minimum size=2cm] (apc) at (1.8,0) {APC};
\draw[ultra thick, <->] (-0.8,0) -- (0.8,0) node[midway, above] {Synapse};
\end{tikzpicture}""",
    "CRISPR Workflow": r"""\begin{tikzpicture}
\node[rectangle, draw, fill=purple!15, minimum width=2cm, minimum height=0.8cm] (gRNA) at (0,1.5) {gRNA};
\node[rectangle, draw, fill=purple!25, minimum width=2cm, minimum height=0.8cm] (cas9) at (0,0) {Cas9};
\node[rectangle, draw, fill=gray!20, minimum width=2.5cm, minimum height=0.8cm] (dna) at (0,-1.5) {Target DNA};
\draw[->, thick] (gRNA) -- (cas9);
\draw[->, thick] (cas9) -- (dna);
\end{tikzpicture}""",
}

def convert_pdf_page_to_image(page: fitz.Page, dpi_scale: int, auto_crop: bool) -> Image.Image:
    mat = fitz.Matrix(dpi_scale, dpi_scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

    if auto_crop:
        bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
    return img

def convert_pdf_bytes_to_images(pdf_bytes: bytes, dpi_scale: int, auto_crop: bool) -> list[Image.Image]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images.append(convert_pdf_page_to_image(page=page, dpi_scale=dpi_scale, auto_crop=auto_crop))
    return images

def image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def build_zip(files: list[tuple[str, bytes]]) -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, payload in files:
            zf.writestr(filename, payload)
    zip_buffer.seek(0)
    return zip_buffer.read()

def generate_cell_tikz(cell_label: str, cell_shape: str, cell_color: str, line_thickness: str, min_size: str, show_shadow: bool) -> str:
    label_to_print = cell_label.replace('\\n', '\\\\ ').replace('\n', '\\\\ ')
    shadow_part = ", drop shadow" if show_shadow else ""
    shape_map = {"circle": "circle", "ellipse": "ellipse", "rectangle": "rectangle", "double circle": "circle, double, double distance=2pt"}
    final_shape = shape_map.get(cell_shape, "circle")
    return f"""\\begin{{tikzpicture}}
\\node [
    {final_shape},
    draw,
    fill=mycolor!20,
    {line_thickness},
    {min_size},
    inner sep=5pt,
    align=center{shadow_part}
] (mycell) at (0,0) {{{label_to_print}}};
\\end{{tikzpicture}}"""

def generate_tikz_code(cell_label: str, cell_color: str, shape_option: str, line_thickness: str, show_shadow: bool, preset: str) -> str:
    if preset == "Receptor":
        min_size = "minimum width=1.0cm, minimum height=0.4cm"
        final_shape = "rectangle"
    elif preset == "Nucleus":
        min_size = "minimum size=1.5cm"
        final_shape = "circle"
    else:
        min_size = "minimum size=2.5cm"
        final_shape = shape_option
    hex_color = cell_color.replace("#", "")
    tikz_body = generate_cell_tikz(cell_label, final_shape, cell_color, line_thickness, min_size, show_shadow)
    return f"% Add this to your preamble:\n\\definecolor{{mycolor}}{{HTML}}{{{hex_color}}}\n\n{tikz_body}"

def generate_legend_tikz(legend_items: list[dict[str, str]]) -> str:
    lines = [r"\begin{tikzpicture}", r"\node at (0.3, 0.8) {\textbf{Legend Index}};"]
    y = 0.0
    for item in legend_items:
        color = item["color"].replace("#", "")
        label = item["label"]
        shape = item["shape"]
        style = item.get("style", "solid")
        lines.append(f"\\node[{shape}, draw, {style}, fill={{[HTML]{{{color}}}!25}}, minimum size=0.45cm] at (0,{round(y, 2)}) {{}};")
        lines.append(f"\\node[anchor=west] at (0.6,{round(y, 2)}) {{{label}}};")
        y -= 0.8
    lines.append(r"\end{tikzpicture}")
    return "\n".join(lines)

def build_full_tikz_document(tikz_body: str) -> str:
    return rf"""\documentclass[tikz,border=10pt]{{standalone}}
\usepackage[svgnames]{{xcolor}}
\usetikzlibrary{{shadows,arrows.meta,positioning,shapes.geometric,calc}}
\begin{{document}}
{tikz_body}
\end{{document}}"""

def grayscale_score(img: Image.Image) -> float:
    gray = ImageOps.grayscale(img)
    hist = gray.histogram()
    total = sum(hist)
    if total == 0: return 0.0
    low, high, mid = sum(hist[:32]) / total, sum(hist[224:]) / total, sum(hist[96:160]) / total
    score = (high + low) * 100 - mid * 15
    return max(0.0, min(100.0, round(score, 2)))

def color_blind_preview(img: Image.Image) -> Image.Image:
    r, g, b = img.split()
    g_reduced = ImageEnhance.Brightness(g).enhance(0.35)
    return Image.merge("RGB", (r, g_reduced, b))

def compose_panel(images, columns, spacing, bg_color, add_labels, label_color):
    widths, heights = [im.width for im in images], [im.height for im in images]
    cell_w, cell_h = max(widths), max(heights)
    rows = (len(images) + columns - 1) // columns
    canvas_w, canvas_h = columns * cell_w + (columns + 1) * spacing, rows * cell_h + (rows + 1) * spacing
    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(canvas)
    for idx, img in enumerate(images):
        row, col = idx // columns, idx % columns
        x, y = spacing + col * (cell_w + spacing), spacing + row * (cell_h + spacing)
        canvas.paste(img, (x, y))
        if add_labels: draw.text((x + 10, y + 10), chr(65 + idx), fill=label_color)
    return canvas

def build_project_payload(state: dict) -> str: return json.dumps(state, indent=2)
def load_project_payload(uploaded_project) -> dict: return json.loads(uploaded_project.read().decode("utf-8"))

st.title("🔬 Bio-TikZ Studio | End-to-End Figure Production")
st.caption("Phase 1 + 2 + 3 features: conversion, design, accessibility, composition, packaging, and workflow automation")
st.markdown("---")

main_tabs = st.tabs(["🖼️ Converter Lab", "🧬 TikZ + Template Studio", "🧪 Accessibility + Reviewer Mode", "🧩 Panel Composer", "📦 Workspace + Export Pack", "🏆 Design Strategy"])

with main_tabs[0]:
    st.header("Batch PDF Converter")
    preset = st.selectbox("Output Profile", list(OUTPUT_PROFILES.keys()))
    default_profile = OUTPUT_PROFILES[preset]
    c1, c2, c3 = st.columns(3)
    with c1:
        dpi_scale = st.slider("Resolution Scale", 1.0, 8.0, float(default_profile["dpi_scale"]), step=0.5)
        calculated_dpi = int(dpi_scale * 72)
        if calculated_dpi >= 300: st.success(f"✅ {calculated_dpi} DPI: Journal Quality")
    with c2: auto_crop = st.checkbox("Auto-Crop", value=default_profile["auto_crop"])
    with c3: batch_mode = st.checkbox("Enable Batch ZIP", value=True)
    uploaded_pdfs = st.file_uploader("Upload PDF figures", type=["pdf"], accept_multiple_files=True)
    if uploaded_pdfs:
        zip_entries = []
        for pdf in uploaded_pdfs:
            pdf_images = convert_pdf_bytes_to_images(pdf.read(), dpi_scale=dpi_scale, auto_crop=auto_crop)
            pdf_stem = Path(pdf.name).stem
            for page_idx, page_img in enumerate(pdf_images, start=1):
                st.image(page_img, caption=f"{pdf_stem} P{page_idx}", use_container_width=True)
                png_bytes = image_to_png_bytes(page_img)
                zip_entries.append((f"{pdf_stem}_P{page_idx}.png", png_bytes))
        if batch_mode and zip_entries:
            st.download_button("⬇️ Download ZIP", data=build_zip(zip_entries), file_name="batch_figures.zip")

with main_tabs[1]:
    st.header("TikZ + Legend Studio")
    # ... (Keep your TikZ and Legend Generator logic here, it was working well) ...
    # (Simplified for space, ensure your existing button logic for presets is kept)

with main_tabs[2]:
    st.header("Accessibility Validator")
    uploaded_image = st.file_uploader("Upload PNG/JPG", type=["png", "jpg", "jpeg"])
    if uploaded_image is not None:
        # MEMORY FIX: Use thumbnail to load only what we need
        base_img = Image.open(uploaded_image).convert("RGB")
        base_img.thumbnail((1200, 1200)) # Resizes in-place safely
        
        gray_img = ImageOps.grayscale(base_img)
        cb_img = color_blind_preview(base_img)
        score = grayscale_score(base_img)
        st.metric("Grayscale Resilience Score", f"{score}/100")
        c1, c2, c3 = st.columns(3)
        c1.image(base_img, caption="Original")
        c2.image(gray_img, caption="Grayscale")
        c3.image(cb_img, caption="Color-Blind")

with main_tabs[3]:
    st.header("Panel Composer")
    panel_files = st.file_uploader("Upload panels", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if panel_files:
        columns = st.slider("Columns", 1, 4, 2)
        spacing = st.slider("Spacing", 0, 80, 20)
        bg_color = st.color_picker("Background", "#ffffff")
        label_color = st.color_picker("Label Color", "#000000")
        add_labels = st.checkbox("Add labels (A, B, C...)", value=True)
        
        # MEMORY FIX: Resize each panel to 800px max before composing
        images = []
        for f in panel_files:
            img = Image.open(f).convert("RGB")
            img.thumbnail((800, 800))
            images.append(img)
            
        composed = compose_panel(images, columns, spacing, bg_color, add_labels, label_color)
        st.image(composed, caption="Preview", use_container_width=True)
        st.download_button("⬇️ Download Panel", data=image_to_png_bytes(composed), file_name="composed.png")

# ... (Keep Workspace and Strategy tabs as they were) ...
st.markdown("---")
st.caption("Developed by Yashwant Nama | PhD Research Portfolio Project")
