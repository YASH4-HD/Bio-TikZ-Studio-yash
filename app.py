import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageChops
import io

# Page Configuration
st.set_page_config(page_title="Bio-TikZ Studio", page_icon="🧬", layout="wide")

st.title("🔬 Researcher's Visualization Suite")
st.markdown("---")

# Create Tabs for the two features
tab1, tab2 = st.tabs(["🖼️ High-Res PNG Converter (with Auto-Crop)", "📝 Overleaf TikZ Generator"])

# --- TAB 1: PDF TO PNG CONVERTER ---
with tab1:
    st.header("Convert PDF Figures to Journal-Quality PNG")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Settings")
        dpi_scale = st.slider("Resolution (Scaling)", 1, 8, 4, help="4 = 300 DPI, 6 = 600 DPI")
        auto_crop = st.checkbox("Auto-Crop White Margins", value=True)
        
    with col2:
        uploaded_file = st.file_uploader("Upload your Figure PDF from Overleaf", type=["pdf"])
        
        if uploaded_file is not None:
            pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Apply high-res scaling
                mat = fitz.Matrix(dpi_scale, dpi_scale)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))

                if auto_crop:
                    # Calculate the actual content area
                    bg = Image.new(img.mode, img.size, img.getpixel((0,0)))
                    diff = ImageChops.difference(img, bg)
                    bbox = diff.getbbox()
                    if bbox:
                        img = img.crop(bbox)
                
                # Display and Download
                st.image(img, caption=f"Page {page_num + 1} - Processed", use_container_width=True)
                
                # Prepare buffer for download
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.download_button(
                    label=f"💾 Download High-Res Page {page_num + 1}",
                    data=byte_im,
                    file_name=f"Figure_Output_DPI{dpi_scale*72}.png",
                    mime="image/png",
                    key=f"btn_{page_num}"
                )

# --- TAB 2: OVERLEAF TIKZ GENERATOR ---
with tab2:
    st.header("Quick TikZ Code Generator")
    st.write("Generate clean code for biological nodes to paste into Overleaf.")

    # New Feature: Toggle for Beginners
    full_doc_mode = st.toggle("🚀 Full Document Mode (For Beginners)", value=False, help="Enable this to get the complete code including preamble. Just paste into a blank Overleaf file!")

    c1, c2, c3 = st.columns(3)
    
    with c1:
        cell_label = st.text_input("Cell Label", "Macrophage")
        cell_color = st.color_picker("Cell Color", "#e74c3c")
    
    with c2:
        shape_option = st.selectbox("Shape", ["circle", "ellipse", "octagon", "rectangle"])
        line_thickness = st.select_slider("Line Thickness", ["thin", "thick", "ultra thick"], value="thick")

    with c3:
        show_shadow = st.checkbox("Add Shadow", value=True)
        preset = st.selectbox("Style Preset", ["Standard Cell", "Receptor", "Nucleus"])

    # --- LOGIC TO HANDLE PRESETS ---
    if preset == "Receptor":
        min_size = "minimum width=1.0cm, minimum height=0.4cm"
        final_shape = "rectangle" 
    elif preset == "Nucleus":
        min_size = "minimum size=1.5cm"
        final_shape = "circle"
    else:
        min_size = "minimum size=2.5cm"
        final_shape = shape_option

    # Clean the color hex for LaTeX
    hex_color = cell_color.replace('#', '')
    
    # Correct Shadow Logic (No trailing commas)
    shadow_part = ", drop shadow" if show_shadow else ""

    # --- TIKZ SNIPPET GENERATION ---
    tikz_snippet = f"""\\begin{{tikzpicture}}
    \\node [
        {final_shape}, 
        draw, 
        fill={hex_color}!20, 
        {line_thickness},          
        {min_size},
        align=center{shadow_part}
    ] (mycell) at (0,0) {{{cell_label}}};
\\end{{tikzpicture}}"""

    # --- FULL DOCUMENT GENERATION ---
    if full_doc_mode:
        final_output = f"""\\documentclass[tikz,border=10pt]{{standalone}}
\\usetikzlibrary{{shapes.geometric, shadows}}
\\usepackage{{xcolor}}

\\definecolor{{{hex_color}}}{{HTML}}{{{hex_color}}}

\\begin{{document}}

{tikz_snippet}

\\end{{document}}"""
    else:
        final_output = f"% Add this to your preamble once:\n% \\definecolor{{{hex_color}}}{{HTML}}{{{hex_color}}}\n\n" + tikz_snippet

    st.subheader("Copy this code to Overleaf:")
    st.code(final_output, language="latex")
    
    st.info("💡 Pro-tip: If you are new to LaTeX, turn on 'Full Document Mode' and paste everything into a new Overleaf file.")
    st.info("💡 Pro-tip: After recompiling in Overleaf, download the PDF and use Tab 1 to get your high-res image!")

st.markdown("---")
st.caption("Developed by Yashwant Nama | PhD Research Portfolio Project")
