import os
import tempfile
import pandas as pd
import chromadb
import streamlit as st
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore

load_dotenv()

VECTOR_STORE_DIR = "chroma_db"

CHROMA_COLLECTION = "chroma_collection"


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
    if not os.path.exists(VECTOR_STORE_DIR):
        os.makedirs(VECTOR_STORE_DIR)

    # Initialize the ChromaDB client
    db = chromadb.PersistentClient(path=VECTOR_STORE_DIR)

    # Create a new collection
    chroma_collection = db.get_or_create_collection(CHROMA_COLLECTION)

    # Assign chroma as the vector_store to the context
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if not os.path.exists(VECTOR_STORE_DIR) or len(os.listdir(VECTOR_STORE_DIR)) == 0:
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


# Sidebar
def build_sidebar():
    # TODO: Add return typehint
    # TODO: Create Type Class for Sidebar Output
    # TODO: Añadir botón de limpiado de base de datos
    sidebar_output = {}
    # Load Image
    uploaded_pdfs = st.sidebar.file_uploader(
        "Carga tus PDFs", type="pdf", accept_multiple_files=True
    )

    st.sidebar.divider()

    # TODO: No permitir subir documentos repetidos
    if uploaded_pdfs:
        temp_dir = tempfile.mkdtemp()

        for pdf in uploaded_pdfs:
            file_path = os.path.join(temp_dir, pdf.name)
            with open(file_path, "wb") as f:
                f.write(pdf.read())

        # TODO: Finish
        index = create_or_update_rag_index(temp_dir)

    else:
        index = None


    db = chromadb.PersistentClient(path=VECTOR_STORE_DIR)
    chroma_collection = db.get_or_create_collection(CHROMA_COLLECTION)

    # Show indexed documents in the sidebar (knowledge base from the RAG)
    expander = st.sidebar.expander("Ver documentos indexados (Base de Conocimiento)")

    st.sidebar.divider()

    # If collection is not empty, show the documents and allow to delete them
    # Deleting Knwoledge Base functionality
    if st.sidebar.button("Limpiar Base de Conocimiento"):
        try:
            db.delete_collection(CHROMA_COLLECTION)
            # db.get_or_create_collection(CHROMA_COLLECTION)
            st.success("Base de Conocimiento limpiada exitosamente.")
            index = None
            expander.info("No hay documentos indexados.")

        except Exception as e:
            st.sidebar.error(f"Error al limpiar la Base de Conocimiento: {e}")
        
    # In case there is no collections
    if len(db.list_collections()) == 0:
        existing_filenames = []
    else:
        existing_filenames = list(_get_existing_filenames(
            chroma_collection
        ))
        expander.write(pd.DataFrame(existing_filenames, columns=["Documentos indexados"]))

    # Sidebar Inputs
    sidebar_output = {
        "index": index,
    }

    return sidebar_output


# Main Page
def build_main_page(sidebar_output: dict[str, bool]) -> None:
    if sidebar_output["index"] is not None:
        st.success("Index updated successfully.")

        top_k = st.slider("Número de resultados", min_value=1, max_value=100, value=10)
        response_mode = st.selectbox(
            "Modo de respuesta", options=["tree_summarize", "compact", "refine"]
        )
        user_query = st.text_input("Consulta")

        if st.button("Consultar"):

            with st.spinner("Consultando..."):

                query_engine = sidebar_output["index"].as_query_engine(
                    similarity_top_k=top_k,
                    response_mode=response_mode,
                    # Important: This configuration makes metadata available in the response
                    node_postprocessors=[],
                )
                response = query_engine.query(user_query)
                st.write(response.response)

                source_data = []

                for i, node in enumerate(response.source_nodes):
                    # Extraer información del nodo
                    node_id = getattr(node, 'node_id', f"Node-{i+1}")
                    score = round(node.score * 100, 2) if hasattr(node, 'score') else 'N/A'
                    
                    # Extraer metadatos relevantes
                    filename = node.metadata.get('file_name', 'Desconocido')
                    page_num = node.metadata.get('page_label', 'N/A')
                    
                    # Max 200 characters to show in the table
                    text_fragment = node.text[:200] + "..." if len(node.text) > 200 else node.text
                    
                    # Agregar a los datos de la tabla
                    source_data.append({
                        "Posición": f"{i+1}",
                        "Score": f"{score}%",
                        "Archivo": filename,
                        "Página": page_num,
                        "Fragmento": text_fragment
                    })
                
                # Mostrar la tabla de fuentes
                if source_data:
                    st.dataframe(source_data, use_container_width=True)
                    
                else:
                    st.info("No se encontraron nodos fuente para esta consulta.")

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
sidebar_output = build_sidebar()

# Show Main Page
build_main_page(sidebar_output)

# streamlit run test.py --server.address localhost --server.port 8502 --browser.gatherUsageStats false  # noqa: E501
