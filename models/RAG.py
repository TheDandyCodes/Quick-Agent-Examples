import os
from pathlib import Path

import chromadb
import toml
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.llms.gemini import Gemini
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
from prompts import EXTRACTION_PROMPT


class RAG:
    def __init__(
        self,
        system_prompt: str,
        model: str = "gpt-4o-mini",
    ):
        self.system_prompt = system_prompt

        if model not in ["gemini-2.0-flash", "gpt-4o-mini"]:
            raise ValueError(
                "Invalid model. Choose 'gemini-2.0-flash' or 'gpt-4o-mini'."
            )

        if model == "gemini-2.0-flash":
            self.model = Gemini(
                model=f"models/{model}", api_key=os.environ["GEMINI_API_KEY"]
            )
        elif model == "gpt-4o-mini":
            self.model = OpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"])

        self.index = None
        self.chat_engine = None
        self.query_engine = None

    def _get_existing_filenames(self, chroma_collection):
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

    def create_or_update_rag_index(
        self, vector_store_path: str, chroma_collection: str, data_dir: str
    ) -> None:
        # TODO: Docstring y return type hint
        if not os.path.exists(vector_store_path):
            os.makedirs(vector_store_path)

        # Initialize the ChromaDB client
        db = chromadb.PersistentClient(path=vector_store_path)

        # Create a new collection
        chroma_collection = db.get_or_create_collection(chroma_collection)

        # Assign chroma as the vector_store to the context
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        if (
            not os.path.exists(vector_store_path)
            or len(os.listdir(vector_store_path)) == 0
        ):
            # Load documents
            documents = SimpleDirectoryReader(data_dir).load_data()
            # Verify that there are no empty documents
            for doc in documents:
                if not doc:
                    print("Documento vacío encontrado")

            # Create index
            index = VectorStoreIndex.from_documents(
                documents, storage_context=storage_context
            )
            self.index = index

            return
        else:
            # Load index from storage
            index = VectorStoreIndex.from_vector_store(
                vector_store, storage_context=storage_context
            )

            # Get existing filenames previously indexed
            # Note: This assume that we can get metadata from the documents
            try:
                existing_filenames = self._get_existing_filenames(chroma_collection)
            except Exception as e:
                print(f"WARNING: (Error: {e})")
                # If the collection is empty, set the existing filenames to an empty set
                existing_filenames = set()

            all_files = os.listdir(data_dir)
            new_files = set(all_files) - existing_filenames

            if new_files:
                new_file_paths = [os.path.join(data_dir, file) for file in new_files]
                # Verify that the files exist
                new_files_paths = [
                    path for path in new_file_paths if os.path.exists(path)
                ]
                # only index new files
                new_documents = SimpleDirectoryReader(
                    input_files=new_files_paths
                ).load_data()

                # TODO: Filtrar documentos vaciós?
                if new_documents:
                    for new_doc in new_documents:
                        index.insert(new_doc)

            self.index = index
            return

    def build_chat_engine(self, chat_mode: str, top_k: int):
        chat_engine = self.index.as_chat_engine(
            chat_mode=chat_mode,
            verbose=True,
            system_prompt=self.system_prompt,
            similarity_top_k=top_k,
            llm=self.model,
        )
        self.chat_engine = chat_engine

    def build_query_engine(self, response_mode: str, top_k: int):
        query_engine = self.index.as_query_engine(
            response_mode=response_mode,
            verbose=True,
            similarity_top_k=top_k,
            llm=self.model,
        )
        self.query_engine = query_engine


def main():
    # Load the environment variables (API key)
    load_dotenv()

    # Load the configuration file
    config = toml.load(Path(__file__).parents[1] / "config.toml")

    rag = RAG(
        system_prompt=EXTRACTION_PROMPT,
        model=config["openai"]["MODEL_NAME"],
    )

    rag.create_or_update_rag_index(
        vector_store_path="Quick-Examples/chroma_db",
        chroma_collection="chroma_collection_test",
        data_dir="Quick-Examples/data",
    )

    # Chat engine
    rag.build_chat_engine(chat_mode="context", top_k=5)

    # Query engine
    rag.build_query_engine(response_mode="tree_summarize", top_k=5)

    # Example usage
    query = "De que trata el documento?"

    # Chat
    print(f"Chat Engine Response: {rag.chat_engine.chat(query)}\n")

    # Query
    print(f"Query Engine Response: {rag.query_engine.query(query)}\n")


if __name__ == "__main__":
    main()
