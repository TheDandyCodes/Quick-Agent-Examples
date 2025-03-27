import os
import tempfile
import pandas as pd
import chromadb
import streamlit as st
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
import toml
from pathlib import Path

load_dotenv()

config = toml.load(Path(__file__).parents[1] / "config.toml")

SYSTEM_PROMPT = "Eres un maestro estoico capaz de aconsejar y hablar de esta filosofía tomando de referencia las meditaciones de Marco Aurelio"

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

def _get_existing_filenames(chroma_collection):
    # TODO: Docstring and type hints
    # TODO: Cache?
    metadatas = chroma_collection.get().get("metadatas", [])
    if metadatas:
        existing_filenames = {
            metadata["file_name"]
            for metadata in metadatas
            if "file_name" in metadata
        }
    else:
        existing_filenames = set()
    return existing_filenames

def create_or_update_rag_index(temp_dir: str) -> None:
    # TODO: Docstring y return type hint
    if not os.path.exists(config["vector-stores"]["RESPONDER_VS"]):
        os.makedirs(config["vector-stores"]["RESPONDER_VS"])

    # Initialize the ChromaDB client
    db = chromadb.PersistentClient(path=config["vector-stores"]["RESPONDER_VS"])

    # Create a new collection
    chroma_collection = db.get_or_create_collection(config["chroma"]["CHROMA_COLLECTION"])

    # Assign chroma as the vector_store to the context
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if not os.path.exists(config["vector-stores"]["RESPONDER_VS"]) or len(os.listdir(config["vector-stores"]["RESPONDER_VS"])) == 0:
        st.toast("No stored index found. Creating a new one.")
        # Load documents
        documents = SimpleDirectoryReader(temp_dir).load_data()
        # Verify that there are no empty documents
        for doc in documents:
            if not doc:
                print("Documento vacío encontrado")

        # Create index
        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context
        )
        return index
    else:
        st.toast("Stored index found. Updating it.")
        # Load index from storage
        index = VectorStoreIndex.from_vector_store(
            vector_store, storage_context=storage_context
        )

        # Get existing filenames previously indexed
        # Note: This assume that we can get metadata from the documents
        try:
            existing_filenames = _get_existing_filenames(chroma_collection)
        except Exception as e:
            print(f"WARNING: (Error: {e})")
            # If the collection is empty, set the existing filenames to an empty set
            existing_filenames = set()

        all_files = os.listdir(temp_dir)
        new_files = set(all_files) - existing_filenames

        if new_files:
            new_file_paths = [os.path.join(temp_dir, file) for file in new_files]
            # Verify that the files exist
            new_files_paths = [path for path in new_file_paths if os.path.exists(path)]
            # only index new files
            new_documents = SimpleDirectoryReader(
                input_files=new_files_paths
            ).load_data()

            # TODO: Filtrar documentos vaciós?
            if new_documents:
                for new_doc in new_documents:
                    index.insert(new_doc)

        return index

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
def build_sidebar():
    # TODO: Add return typehint
    # TODO: Create Type Class for Sidebar Output
    # TODO: Añadir botón de limpiado de base de datos
    # TODO: Add default values in the same way as st_interactions.py of bestinver
    index = None
    top_k = 5
    query_engine_response_mode = "tree_summarize"
    chat_engine_response_mode = "context"

    # Load Image
    uploaded_pdfs = st.sidebar.file_uploader(
        "Carga tus PDFs", 
        type="pdf", 
        accept_multiple_files=True, 
        key=st.session_state.get("pdf_uploader_key", "pdf_uploader")
    )

    st.sidebar.divider()

    # TODO: No permitir subir documentos repetidos
    if uploaded_pdfs:

        disable = False

        with st.spinner("Cargando PDFs..."):
            temp_dir = tempfile.mkdtemp()

            for pdf in uploaded_pdfs:
                file_path = os.path.join(temp_dir, pdf.name)
                with open(file_path, "wb") as f:
                    f.write(pdf.read())

            # TODO: Finish
            index = create_or_update_rag_index(temp_dir)

    else:
        disable = True

    top_k = st.sidebar.slider("Número de resultados", min_value=1, max_value=100, value=10, disabled=disable)

    tab1, tab2 = st.sidebar.tabs(["Query engine", "Chat engine"])

    query_engine_response_mode = tab1.selectbox(
        "Modo de respuesta", 
        options=["tree_summarize", "compact", "refine"],
        key="query_engine_response_mode",
        disabled=disable
    )
    chat_engine_response_mode = tab2.selectbox(
        "Modo de respuesta", 
        options=["context", "condense_plus_context"],
        key="chat_engine_response_mode",
        disabled=disable
    )

    st.sidebar.divider()

    db = chromadb.PersistentClient(path=config["vector-stores"]["RESPONDER_VS"])
    chroma_collection = db.get_or_create_collection(config["chroma"]["CHROMA_COLLECTION"])

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

            st.success("Base de Conocimiento limpiada exitosamente.")

            index = None
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
        existing_filenames = list(_get_existing_filenames(
            chroma_collection
        ))
        expander.dataframe(pd.DataFrame(existing_filenames, columns=["Documentos indexados"]), hide_index=True)

    # Sidebar Inputs
    sidebar_output = {
        "index": index,
        "top_k": top_k,
        "query_engine_response_mode": query_engine_response_mode,
        "chat_engine_response_mode": chat_engine_response_mode,
    }

    return sidebar_output

def build_chat():
    # TODO: Docstring

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
def build_main_page(sidebar_output: dict[str, bool]) -> None:
    if sidebar_output["index"] is not None:
        st.toast("Index updated successfully.")

        tab_query, tab_chat = st.tabs(["Consulta", "Chat"])

        # Query Engine
        with tab_query:
            _build_query_section(sidebar_output)
        
        # Chat Engine
        with tab_chat:
            chat_engine = sidebar_output["index"].as_chat_engine(
                chat_mode=sidebar_output["chat_engine_response_mode"], 
                verbose=False, 
                system_prompt=SYSTEM_PROMPT,
                similarity_top_k=sidebar_output["top_k"], 
                llm=st.session_state["llm"]
            )

            st.session_state["chat_engine"] = chat_engine
            
            # Chat
            build_chat()

def _build_query_section(sidebar_output):
    # TODO: Docstring and type hints
    user_query = st.text_input("Consulta")
    if st.button("Consultar"):
        with st.spinner("Consultando..."):
            query_engine = sidebar_output["index"].as_query_engine(
                        similarity_top_k=sidebar_output["top_k"],
                        response_mode=sidebar_output["query_engine_response_mode"],
                        # Important: This configuration makes metadata available in the response
                        node_postprocessors=[],
                        llm=st.session_state["llm"],
                    )
            response = query_engine.query(user_query)
            st.write(response.response)

            source_data = get_source_data_from_response(response)
                    
            # Show source data in a table
            if source_data:
                st.dataframe(source_data, use_container_width=True)
                        
            else:
                st.info("No se encontraron nodos fuente para esta consulta.")

def get_source_data_from_response(response):
    # TODO: docstring and type hints
    source_data = []

    for i, node in enumerate(response.source_nodes):
        # Extract score from node
        score = round(node.score * 100, 2) if hasattr(node, 'score') else 'N/A'
                    
        # Extract metadata from node
        filename = node.metadata.get('file_name', 'Desconocido')
        page_num = node.metadata.get('page_label', 'N/A')
                    
        # Max 200 characters
        text_fragment = node.text[:200] + "..." if len(node.text) > 200 else node.text
                    
        # Append data to source_data
        source_data.append({
            "Posición": f"{i+1}",
            "Score": f"{score}%",
            "Archivo": filename,
            "Página": page_num,
            "Fragmento": text_fragment
        })

    return source_data


#########################################################################

st.set_page_config(
    page_title="RAG",
    layout="wide",
    page_icon="App/assets/page_logo.jpg",
)

_hide_header()

# Session States
if 'messages' not in st.session_state:
    st.session_state["messages"] = []

if 'chat_engine' not in st.session_state:
    st.session_state["chat_engine"] = None

if 'llm' not in st.session_state:
    st.session_state["llm"] = OpenAI(model=config["openai"]["MODEL_NAME"])

# This is to "clean" the file uploader when "Limpiar Base de Conocimiento" is clicked
if 'pdf_uploader_key' not in st.session_state:
    st.session_state["pdf_uploader_key"] = "pdf_uploader"

# Show Sidebar
sidebar_output = build_sidebar()

# Show Main Page
build_main_page(sidebar_output)

# streamlit run test.py --server.address localhost --server.port 8502 --browser.gatherUsageStats false  # noqa: E501
