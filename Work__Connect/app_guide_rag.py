"""
WorkConnect App Navigation & Operations RAG Guide (app_guide_rag.py)
- Loads app_faq.txt
- Chunks and stores in ChromaDB using HuggingFace embeddings (with graceful fallback if packages are missing)
- Defines LangChain tool 'App_Guide_Tool'
"""

import os

try:
    from langchain_core.tools import tool
    from langchain_text_splitters import CharacterTextSplitter
    from langchain_community.document_loaders import TextLoader
    from langchain_community.vectorstores import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    def tool(func):
        return func

FAQ_FILE = "app_faq.txt"
DB_DIR = "./chroma_app_guide_db"

def setup_app_guide_rag():
    if not LANGCHAIN_AVAILABLE:
        return None
    try:
        if not os.path.exists(FAQ_FILE):
            with open(FAQ_FILE, "w", encoding="utf-8") as f:
                f.write(
                    "HOW TO APPLY FOR A JOB:\n"
                    "1. Log in to your Worker account.\n"
                    "2. Go to the 'Recommended Jobs' dashboard.\n"
                    "3. Use the search bar or distance filter to find a job that matches your skills.\n"
                    "4. Click on the job card to view details (wage, location, date).\n"
                    "5. Click the 'Apply' button.\n"
                    "6. The employer will review your profile. You will get a notification if you are shortlisted.\n\n"
                    "HOW TO POST A REQUIREMENT (FOR EMPLOYERS):\n"
                    "1. Log in to your Employer account.\n"
                    "2. Click the '+' button on the bottom navigation bar.\n"
                    "3. Fill in the job details: Title, Skill Required, Number of Workers, Date, and Wage.\n"
                    "4. Set the location using the map or by typing the village/city name.\n"
                    "5. Click 'Post Requirement'. The matching engine will instantly show you a list of suitable workers.\n\n"
                    "HOW TO UPDATE YOUR PROFILE:\n"
                    "1. Go to the 'Profile' tab.\n"
                    "2. Click 'Edit Profile'.\n"
                    "3. You can add new skills, update your expected wage, or change your availability dates.\n"
                    "4. Click 'Save' to ensure the matching engine uses your latest information."
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
    except Exception:
        return None


retriever = setup_app_guide_rag()


if LANGCHAIN_AVAILABLE:
    @tool
    def App_Guide_Tool(query: str) -> str:
        """Use this tool ONLY when the user asks HOW to do something inside the app, such as how to apply for a job, how to register, how to post a requirement, or how to update their profile."""
        try:
            if not retriever:
                return "1. Log in to your account.\n2. Go to 'Browse Jobs' to apply or 'Post a Job' to hire.\n3. Visit 'Edit Profile' to update your preferences."
            docs = retriever.invoke(query)
            if not docs:
                return "I couldn't find specific instructions for that action in the WorkConnect guide."
            return "\n\n".join([doc.page_content for doc in docs])
        except Exception as e:
            return f"Error retrieving app guide: {str(e)}"
else:
    def App_Guide_Tool(query: str) -> str:
        """Use this tool ONLY when the user asks HOW to do something inside the app, such as how to apply for a job, how to register, how to post a requirement, or how to update their profile."""
        return "1. Log in to your account.\n2. Go to 'Browse Jobs' to apply or 'Post a Job' to hire.\n3. Visit 'Edit Profile' to update your preferences."
