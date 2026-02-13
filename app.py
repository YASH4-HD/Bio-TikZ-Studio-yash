import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io

# Page Configuration
st.set_page_config(page_title="BioRender-to-LaTeX Tool", page_icon="🧬", layout="wide")

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
                
                if auto_crop:
                    # Calculate the actual content area (the bounding box)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    # Use PIL's bbox to crop white space
                    bg = Image.new(img.mode, img.size, img.getpixel((0,0)))
                    diff = Image.chops.difference(img, bg)
                    bbox = diff.getbbox()
                    if bbox:
                        img = img.crop(bbox)
                else:
                    pix = page.get_pixmap(matrix=mat)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                
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
                    mime="image/png"
                )

# --- TAB 2: OVERLEAF TIKZ GENERATOR ---
with tab2:
    st.header("Quick TikZ Code Generator")
    st.write("Generate clean code for biological nodes to paste into Overleaf.")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        cell_label = st.text_input("Cell Label", "Macrophage")
        cell_color = st.color_picker("Cell Color", "#e74c3c")
    with c2:
        shape = st.selectbox("Shape", ["circle", "ellipse", "octagon"])
        line_thickness = st.select_slider("Line Thickness", ["thin", "thick", "ultra thick"])
    with c3:
        show_shadow = st.checkbox("Add Shadow", value=True)

    # Generate the Snippet
    shadow_code = ", drop shadow" if show_shadow else ""
    
    tikz_code = f"""
% Add this to your preamble: \\usetikzlibrary{{shapes.geometric, shadows}}

\\begin{{tikzpicture}}
    \\node[{shape}, draw, fill={cell_color}!20, 
          line width={line_thickness}, 
          minimum size=2.5cm, 
          align=center{shadow_code}] (mycell) at (0,0) {{{cell_label}}};
\\end{{tikzpicture}}
    """
    
    st.subheader("Copy this code to Overleaf:")
    st.code(tikz_code, language="latex")
    st.info("💡 Tip: Use this for quick flowchart nodes or cell diagrams.")

st.markdown("---")
st.caption("Developed by Yashwant Nama | PhD Research Portfolio Project")
