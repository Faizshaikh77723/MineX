import os
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings

def build_vector_store(markdown_file_path: str, persist_dir: str):
    """
    Reads a Markdown document, chunks it logically by headers, 
    and stores the embeddings in ChromaDB using Ollama.
    """
    print(f"1. Reading Markdown file: {markdown_file_path}")
    if not os.path.exists(markdown_file_path):
        raise FileNotFoundError(f"Could not find {markdown_file_path}")
        
    with open(markdown_file_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
        
    print("2. Chunking document by Markdown headers...")
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(md_text)
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    final_splits = text_splitter.split_documents(md_header_splits)
    
    print(f"   -> Generated {len(final_splits)} logical chunks.")
    
    print("3. Connecting to Ollama for Embeddings (bge-m3)...")
    # Using Ollama handles the heavy C++ operations securely outside of Python
    embeddings = OllamaEmbeddings(model="bge-m3")
    
    print("4. Storing vectors into ChromaDB...")
    vector_store = Chroma.from_documents(
        documents=final_splits, 
        embedding=embeddings, 
        persist_directory=persist_dir
    )
    
    print(f"✅ Success! Vector database created at: {persist_dir}")
    return vector_store

if __name__ == "__main__":
    input_md = "data/extracted/Safety_in_Coal_Mines.md"
    db_folder = "data/chromadb_store"
    build_vector_store(input_md, db_folder)