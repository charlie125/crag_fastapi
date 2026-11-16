import os

# LangChain
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

# Ollama Embedding model
from langchain_ollama import OllamaEmbeddings

from models import VectorDB
from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker
from config import setting

embeddings = OllamaEmbeddings(model="nomic-embed-text")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Corpus and vector store live inside the project, so that they are carried
# by the repository.
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
PERSIST_DIR = os.path.join(DATA_ROOT, "vector_db")

FILE_LOCATION = os.path.join(
    DATA_ROOT, "Corporate Data Protection and GDPR Compliance Policy.pdf")

engine = create_engine(setting.database_url)
SessionLocal = sessionmaker(engine, class_=Session, expire_on_commit=False)

def set_up_vector_db():
    file_location = FILE_LOCATION
    loader = PyPDFLoader(file_location)
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\n\n", "\n", " "]
        )

    chunks = splitter.split_documents(pages)

    chunks_list = [chunk.page_content for chunk in chunks]
    emb_text = embeddings.embed_documents(chunks_list)

    with SessionLocal() as session:
        p = Path(str(FILE_LOCATION))
        session.execute(delete(VectorDB).where(VectorDB.source == p.stem))

        for emb, chk in zip(emb_text, chunks):
            new_vector = VectorDB(content=chk.page_content, source=p.stem, page=int(chk.metadata["page"]) + 1, embedding=emb)

            session.add(new_vector)
        session.commit()

    return chunks

def format_data(obj):
    formatted_chunks = []

    for doc in obj:
        clean_text = doc.content.replace("-\n", "").replace("\n", " ")
        formatted_chunks.append(
            f"[Source: '{doc.source}', Page: {doc.page}]: {clean_text}")

    text_prompt_string = "\n\n".join(formatted_chunks)

    return text_prompt_string

def vector_db_search(user_query):
    query_embedding = embeddings.embed_query(user_query)
    with SessionLocal() as session:
        stmt = select(VectorDB).order_by(VectorDB.embedding.cosine_distance(query_embedding)).limit(3)
        retrieved_context = format_data(session.scalars(stmt).all())

    return retrieved_context

if __name__ == "__main__":
    chunks = set_up_vector_db()
    print(f"Ingested {len(chunks)} chunks")