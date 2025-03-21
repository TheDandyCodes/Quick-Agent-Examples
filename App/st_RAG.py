import numpy as np
import streamlit as st
import tempfile
from PIL import Image
import os

def _hide_header():
    """Hide header of streamlit."""
    st.markdown(
        """
    <style>
    [data-testid="stHeader"]{
        display: none;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

def create_rag_index(temp_dir: str) -> None:
    """Create RAG index from PDFs."""
    # TODO: Finish function
    pass

# Sidebar
def build_sidebar():
    # TODO: Add return typehint
    # TODO: Create Type Class for Sidebar Output
    sidebar_output = {}
    # Load Image
    st.sidebar.subheader("Load your PDFs")
    uploaded_pdfs = st.sidebar.file_uploader("Carga tus PDFs", type="pdf", accept_multiple_files=True)

    if uploaded_pdfs:
        temp_dir = tempfile.mkdtemp()

        for pdf in uploaded_pdfs:
            file_path = os.path.join(temp_dir, pdf.name)
            with open(file_path, "wb") as f:
                f.write(pdf.read())
    
    # TODO: Finish
    index = create_rag_index(temp_dir)
    st.sidebar.divider()

    # Image Histogram
    if st.session_state["img"] is not None:
        st.sidebar.subheader("Image Histogram")
        show_histogram = st.sidebar.toggle("Show Histogram")

    # Sidebar Inputs
    sidebar_inputs = {
        "show_histogram": show_histogram,
    }

    return sidebar_output

# Main Page
def build_main_page(sidebar_inputs: dict[str, bool]) -> None:
    # Show Image
    cont1 = st.container()
    cont2 = st.container()

    col1_title, col2_title = cont1.columns(2)

    col1, col2 = cont2.columns(2)
    if st.session_state["img"] is not None:
        col1_title.subheader("Raw Image")
        col1.image(
            st.session_state["img"], 
            caption="Uploaded Image", 
            use_container_width=False,
            width=400
        )
    if sidebar_inputs["show_histogram"]:
        col2_title.subheader("Histogram")
        if st.session_state["img"] is not None:
            histogram = get_img_histogram(st.session_state["img"])
            col2.plotly_chart(histogram)
        else:
            col2.error("Please upload an image to show the histogram.")  

    st.divider()

#########################################################################

st.set_page_config(
    page_title="Komorebi AI - Consulta de Interacciones",
    layout="wide",
    page_icon="./src/streamlit_dashboard_interactions/assets/apple-touch-icon.png",
)

_hide_header()

if "img" not in st.session_state:
    st.session_state["img"] = None

# Show Sidebar
sidebar_inputs = build_sidebar()

# Show Main Page
build_main_page(sidebar_inputs)

# streamlit run test.py --server.address localhost --server.port 8502 --browser.gatherUsageStats false  # noqa: E501