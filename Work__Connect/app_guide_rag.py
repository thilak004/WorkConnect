"""
WorkConnect App Navigation & Operations RAG Guide (app_guide_rag.py)
- Loads app_faq.txt
- Chunks and stores in ChromaDB using HuggingFace embeddings
- Defines LangChain tool 'App_Guide_Tool' with precise description
"""

import os
from langchain_core.tools import tool
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()

FAQ_FILE = "app_faq.txt"
DB_DIR = "./chroma_app_guide_db"

def setup_app_guide_rag():
    """Load app_faq.txt, chunk text, and store in ChromaDB with HuggingFace embeddings."""
    if not os.path.exists(FAQ_FILE):
        with open(FAQ_FILE, "w", encoding="utf-8") as f:
            f.write(
                "How to apply for a job:\n"
                "1. Go to 'Browse Jobs' from the navigation bar.\n"
                "2. Filter jobs by your trade or location.\n"
                "3. Click 'Apply Now' on any open job listing.\n\n"
                "How to post a requirement:\n"
                "1. Sign in as an Employer.\n"
                "2. Click 'Post a Job' in the top navigation.\n"
                "3. Fill in job title, required skill, daily wage, and location, then click submit.\n\n"
                "How to update a worker profile:\n"
                "1. Go to your Worker Dashboard.\n"
                "2. Click 'Edit Profile & Preferences'.\n"
                "3. Update your skill, experience, wage expectations, or phone number and save changes."
            )

    loader = TextLoader(FAQ_FILE, encoding="utf-8")
    documents = loader.load()

    text_splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    docs = text_splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    return vector_store.as_retriever(search_kwargs={"k": 2})


# Initialize retriever
retriever = setup_app_guide_rag()


# Create LangChain Tool with exact description requested
@tool
def App_Guide_Tool(query: str) -> str:
    """Use this tool ONLY when the user asks HOW to do something inside the app, such as how to apply for a job, how to register, how to post a requirement, or how to update their profile."""
    try:
        docs = retriever.invoke(query)
        if not docs:
            return "I couldn't find specific instructions for that action in the WorkConnect guide."
        return "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        return f"Error retrieving app guide: {str(e)}"
