from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings

_retriever_instance = None

def reset_retriever():
    """Forces the retriever to reload the updated ChromaDB collection."""
    global _retriever_instance
    _retriever_instance = None

def get_retriever(persist_dir: str = "data/chromadb_store"):
    global _retriever_instance
    
    if _retriever_instance is None:
        embeddings = OllamaEmbeddings(model="bge-m3")
        vector_store = Chroma(
            persist_directory=persist_dir, 
            embedding_function=embeddings
        )
        # k=8 ensures both safety context and production tables are retrieved simultaneously
        _retriever_instance = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 8}
        )
        
    return _retriever_instance

def retrieve_context(query: str) -> str:
    retriever = get_retriever()
    results = retriever.invoke(query)
    
    context_blocks = []
    for i, doc in enumerate(results):
        block = f"--- Source Chunk {i+1} ---\nSource: {doc.metadata.get('source', 'Unknown')}\nData:\n{doc.page_content}\n"
        context_blocks.append(block)
        
    return "\n".join(context_blocks)