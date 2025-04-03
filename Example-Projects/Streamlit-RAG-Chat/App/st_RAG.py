import os
import tempfile
from pathlib import Path
from typing import TypedDict

import chromadb
import pandas as pd
import streamlit as st
import toml
from dotenv import load_dotenv
from llama_index.core.base.response.schema import Response
import sys

# Añadir el directorio padre al path para poder importar models
sys.path.append(str(Path(__file__).parents[1]))
from models.RAG import RAG

load_dotenv()

config = toml.load(Path(__file__).parents[1] / "config.toml")

SYSTEM_PROMPT = (
    "Eres un asistente experto en textos pedagógicos."
    "Tu tarea es ayudar a los usuarios a encontrar información específica"
    "en documentos PDF. Responde a las preguntas de manera concisa y clara."
    "Si no puedes encontrar la respuesta en los documentos, informa al usuario."
    "Debes proporcionar la información de manera clara y estructurada y haciendo referencia"
    "textual a los documentos de origen, en el caso de ser necesario para aclarar un concepto"
)


class SidebarOutput(TypedDict):
    """Class to store the sidebar output."""

    top_k: int
    query_engine_response_mode: str
    chat_engine_response_mode: str


class SourceData(TypedDict):
    """Class to store the source data from a LlamaIndex query response."""

    position: str
    score: str
    filename: str
    page_num: str
    text_fragment: str


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


def _clean_file_uploader():
    """
    Limpia el file uploader cambiando su key en session_state para forzar
    su recreación vacío.
    """
    # Generates new key for the file uploader
    if "pdf_uploader_key" not in st.session_state:
        st.session_state["pdf_uploader_key"] = "pdf_uploader_0"
    else:
        # Extract the number of the current key and increment it
        current_key = st.session_state["pdf_uploader_key"]
        key_parts = current_key.split("_")
        if len(key_parts) > 2 and key_parts[-1].isdigit():
            counter = int(key_parts[-1]) + 1
        else:
            counter = 0
        st.session_state["pdf_uploader_key"] = f"pdf_uploader_{counter}"

    # Cleans the current state of the uploader
    if "pdf_uploader" in st.session_state:
        del st.session_state["pdf_uploader"]


# Sidebar
def build_sidebar() -> SidebarOutput:
    """Build the sidebar of the app.

    This function creates the sidebar of the app, allowing the user to upload
    PDFs, select the number of results to display, and choose the response modes
    for the query and chat engines. It also provides an option to clear the knowledge
    base.

    Returns
    -------
    SidebarOutput
        A dictionary containing the selected paramters from the sidebar.
    """
    # Load Image
    uploaded_pdfs = st.sidebar.file_uploader(
        "Carga tus PDFs",
        type="pdf",
        accept_multiple_files=True,
        key=st.session_state.get("pdf_uploader_key", "pdf_uploader"),
    )

    st.sidebar.divider()

    if uploaded_pdfs:
        disable = False
        
        current_pdf_identifiers = [(pdf.name, pdf.size) for pdf in uploaded_pdfs]
        previous_pdf_identifiers = [
            (pdf.name, pdf.size) for pdf in st.session_state["previous_uploaded_pdfs"]
        ]
        # En el caso de que el usuario suba un nuevo PDF o cambie uno de los PDFs
        if current_pdf_identifiers != previous_pdf_identifiers:
            with st.spinner("Cargando PDFs..."):
                temp_dir = tempfile.mkdtemp()

                for pdf in uploaded_pdfs:
                    file_path = os.path.join(temp_dir, pdf.name)
                    with open(file_path, "wb") as f:
                        f.write(pdf.read())

                st.session_state["rag"].create_or_update_rag_index(
                    vector_store_path=config["chroma"]["VECTOR_STORE"],
                    chroma_collection_name=config["chroma"]["CHROMA_COLLECTION"],
                    data_dir=temp_dir,
                )

                # In case `uploaded_pdfs` changes from previous state,
                # st.session_state[“docs_updated”] = True
                # This is to check if the documents have been updated,
                # so that the chat context is preserved
                st.session_state["docs_updated"] = True
                st.session_state["previous_uploaded_pdfs"] = uploaded_pdfs

    else:
        disable = True

    top_k = st.sidebar.slider(
        "Número de resultados",
        min_value=1,
        max_value=100,
        value=st.session_state["widgets_default_values_by_keys"]["top_k"],
        disabled=disable,
    )

    tab1, tab2 = st.sidebar.tabs(["Query engine", "Chat engine"])

    query_engine_response_mode = tab1.selectbox(
        "Modo de respuesta",
        options=["tree_summarize", "compact", "refine"],
        key="query_engine_response_mode",
        disabled=disable,
    )
    chat_engine_response_mode = tab2.selectbox(
        "Modo de respuesta",
        options=["context", "condense_plus_context"],
        key="chat_engine_response_mode",
        disabled=disable,
    )

    st.sidebar.divider()

    db = chromadb.PersistentClient(path=config["chroma"]["VECTOR_STORE"])
    chroma_collection = db.get_or_create_collection(
        config["chroma"]["CHROMA_COLLECTION"]
    )

    # Show indexed documents in the sidebar (knowledge base from the RAG)
    expander = st.sidebar.expander("Ver documentos indexados (Base de Conocimiento)")

    st.sidebar.divider()

    # If collection is not empty, show the documents and allow to delete them
    # Deleting Knwoledge Base functionality
    if st.sidebar.button("Limpiar Base de Conocimiento", disabled=disable):
        try:
            db.delete_collection(config["chroma"]["CHROMA_COLLECTION"])
            # db.get_or_create_collection(config["chroma"]["CHROMA_COLLECTION"])

            # Clean the file uploader
            _clean_file_uploader()

            # Now there are no documents in the collection
            st.session_state["docs_updated"] = True

            st.success("Base de Conocimiento limpiada exitosamente.")

            expander.info("No hay documentos indexados.")

            # Force a rerun of the app to clean the file uploader, that assures that the file uploader
            # is reloaded with the new key and without files.
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"Error al limpiar la Base de Conocimiento: {e}")

    # In case there is no collections
    if len(db.list_collections()) == 0:
        existing_filenames = []
    else:
        existing_filenames = list(
            st.session_state["rag"].get_existing_filenames(chroma_collection)
        )
        expander.dataframe(
            pd.DataFrame(existing_filenames, columns=["Documentos indexados"]),
            hide_index=True,
        )

    # Sidebar Inputs
    sidebar_output = {
        "top_k": top_k,
        "query_engine_response_mode": query_engine_response_mode,
        "chat_engine_response_mode": chat_engine_response_mode,
    }

    return sidebar_output


def build_chat() -> None:
    """Build the chat interface of the app that allows the user
    to interact with the RAG assistant."""
    cont1, cont2 = st.container(), st.container(height=500)
    if cont1.button("Limpiar chat", key="clear_button"):
        st.session_state.messages = []
        st.session_state["chat_engine"].reset()

    # Display chat messages from history on app rerun
    # Note: App rerun occurs when a user interacts with the app
    for message in st.session_state.messages:
        with cont2.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with cont2.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with cont2.chat_message("assistant"):
            stream_response = st.session_state["chat_engine"].stream_chat(prompt)
            response = st.write_stream(stream_response.response_gen)

        st.session_state.messages.append({"role": "assistant", "content": response})


# Main Page
def build_main_page(sidebar_output: SidebarOutput) -> None:
    """Build the main page of the app.

    This function creates the main page of the app, allowing the user to
    interact with the RAG assistant. It includes a query engine and a chat
    engine. The query engine allows the user to ask questions and receive
    answers based on the indexed documents. The chat engine allows the user
    to have a conversation with the assistant, which can provide information
    and answer questions based on the indexed documents.

    Parameters
    ----------
    sidebar_output : SidebarOutput
        A dictionary containing the selected parameters from the sidebar.
    """
    if st.session_state["rag"].index is not None:
        st.toast("Index updated successfully.")

        tab_query, tab_chat = st.tabs(["Consulta", "Chat"])

        # Query Engine
        with tab_query:
            _build_query_section(sidebar_output)

        # Chat Engine
        with tab_chat:
            # In case the documents have been updated
            if st.session_state["docs_updated"]:
                chat_engine = st.session_state["rag"].build_chat_engine(
                    chat_mode=sidebar_output["chat_engine_response_mode"],
                    top_k=sidebar_output["top_k"],
                )

                st.session_state["chat_engine"] = chat_engine

                st.session_state["docs_updated"] = False

            # Chat
            build_chat()


def _build_query_section(sidebar_output: SidebarOutput) -> None:
    """Build the query section of the app.

    This function creates the query section of the app, allowing the user to
    make inquiries and receive answers based on the indexed documents.

    Parameters
    ----------
    sidebar_output : SidebarOutput
        A dictionary containing the selected parameters from the sidebar.
    """
    user_query = st.text_input("Consulta")
    if st.button("Consultar"):
        with st.spinner("Consultando..."):
            query_engine = st.session_state["rag"].build_query_engine(
                response_mode=sidebar_output["query_engine_response_mode"],
                top_k=sidebar_output["top_k"],
                # Important: This configuration makes metadata available in the response
                node_postprocessors=[],
            )

            response = query_engine.query(user_query)
            st.write(response.response)

            source_data = get_source_data_from_response(response)

            # Show source data in a table
            if source_data:
                st.dataframe(source_data, use_container_width=True)

            else:
                st.info("No se encontraron nodos fuente para esta consulta.")


def get_source_data_from_response(response: Response) -> list[SourceData]:
    """Get source metadata from LlamaIndex query response.

    This function extracts the source metadata from the LlamaIndex query response
    and returns it in a structured format. The metadata includes the position,
    score, filename, page number, and text fragment of the source nodes.

    Parameters
    ----------
    response : Response
        The LlamaIndex query response object.
        It contains the source nodes and their metadata.

    Returns
    -------
    list[SourceData]
        A list of dictionaries containing the source metadata.
        Each dictionary contains the position, score, filename, page number,
    """
    source_data = []
    for i, node in enumerate(response.source_nodes):
        # Extract score from node
        score = round(node.score * 100, 2) if hasattr(node, "score") else "N/A"

        # Extract metadata from node
        filename = node.metadata.get("file_name", "Desconocido")
        page_num = node.metadata.get("page_label", "N/A")

        # Max 200 characters
        text_fragment = node.text[:200] + "..." if len(node.text) > 200 else node.text

        # Append data to source_data
        source_data.append(
            {
                "Posición": f"{i+1}",
                "Score": f"{score}%",
                "Archivo": filename,
                "Página": page_num,
                "Fragmento": text_fragment,
            }
        )

    return source_data


#########################################################################

st.set_page_config(
    page_title="RAG",
    layout="wide",
    page_icon="App/assets/page_logo.jpg",
)

_hide_header()

# Session States
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "chat_engine" not in st.session_state:
    st.session_state["chat_engine"] = None

if "rag" not in st.session_state:
    rag = RAG(
        system_prompt=SYSTEM_PROMPT,
        model=config["google-genai"]["MODEL_NAME"],
    )
    st.session_state["rag"] = rag

# This is to "clean" the file uploader when "Limpiar Base de Conocimiento" is clicked
if "pdf_uploader_key" not in st.session_state:
    st.session_state["pdf_uploader_key"] = "pdf_uploader"

if "docs_updated" not in st.session_state:
    st.session_state["docs_updated"] = False

if "previous_uploaded_pdfs" not in st.session_state:
    st.session_state["previous_uploaded_pdfs"] = []

if "widgets_default_values_by_keys" not in st.session_state:
    st.session_state["widgets_default_values_by_keys"] = {
        "top_k": 5,
    }

# Show Sidebar
sidebar_output = build_sidebar()

# Show Main Page
build_main_page(sidebar_output)

# streamlit run test.py --server.address localhost --server.port 8502 --browser.gatherUsageStats false  # noqa: E501
