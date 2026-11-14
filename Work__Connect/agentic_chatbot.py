"""
WorkConnect Agentic AI Chatbot Backend
- Uses LangChain's create_react_agent with AgentExecutor
- Provides 3 core tools: Search_Knowledge_Base, Job_Search_Tool, Registration_Help
- Robust error handling (handle_parsing_errors=True) for malformed outputs or gibberish input
"""

import os
import json
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    openai_api_key=os.environ.get("OPENAI_API_KEY")
)

# 1. Search_Knowledge_Base Tool (RAG / General Platform Info)
@tool
def search_knowledge_base(query: str) -> str:
    """Use this tool for general questions about WorkConnect, daily wage ranges, matching system weights, or privacy regulations (DPDP Act 2023)."""
    q_lower = query.lower()
    if "match" in q_lower or "weight" in q_lower:
        return "WorkConnect matching weights: Skills 35%, Location 20%, Experience 15%, Wage 15%, Availability 10%, Rating 5%."
    elif "privacy" in q_lower or "data" in q_lower:
        return "WorkConnect complies strictly with the Digital Personal Data Protection Act, 2023 (DPDP Act, 2023)."
    elif "wage" in q_lower or "salary" in q_lower:
        return "Daily wages on WorkConnect typically range from ₹500 to ₹1,200 per day depending on skill and experience."
    return "WorkConnect is a platform connecting local workers (farmers, masons, drivers) with employers across India."


# 2. Job_Search_Tool (Search jobs by skill and location)
@tool
def job_search_tool(query: str) -> str:
    """Use this tool when users ask to search for jobs specifying a skill/trade (e.g., mason, driver, electrician) and/or location (e.g., Guntur, Rajahmundry)."""
    q_lower = query.lower()
    mock_jobs = [
        {"title": "Mason", "location": "Guntur", "wage": "₹800/day", "employer": "Sri Builders"},
        {"title": "Electrician", "location": "Vijayawada", "wage": "₹900/day", "employer": "Apex Electricals"},
        {"title": "Driver", "location": "Kakinada", "wage": "₹750/day", "employer": "FastLogistics"}
    ]

    results = [j for j in mock_jobs if j["title"].lower() in q_lower or j["location"].lower() in q_lower]
    if not results:
        results = mock_jobs[:2]

    return json.dumps(results, ensure_ascii=False)


# 3. Registration_Help Tool (Sign up guide)
@tool
def registration_help(query: str) -> str:
    """Use this tool when users ask how to sign up, register an account, or join as a worker or employer."""
    return (
        "Step-by-step registration guide for WorkConnect:\n"
        "1. Click 'Register' or 'Register by Voice' on the homepage.\n"
        "2. Choose your role: Worker / Job Seeker or Employer / Contractor.\n"
        "3. Enter your name, mobile phone number, and email address.\n"
        "4. Set a secure password (at least 8 characters).\n"
        "5. Select your primary trade (e.g., Mason, Driver, Electrician) and location.\n"
        "6. Click complete to instantly access your private dashboard."
    )


tools = [search_knowledge_base, job_search_tool, registration_help]

# Standard ReAct Prompt Template
react_prompt = PromptTemplate.from_template("""
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}
""")


def get_agent_executor():
    """Create and return the agent executor with robust error handling."""
    agent = create_react_agent(llm, tools, react_prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True, # Graceful handling of malformed LLM outputs or gibberish
        max_iterations=3
    )
    return agent_executor


def run_agent_chat(user_message: str) -> str:
    """Run agent chat securely with error handling."""
    try:
        executor = get_agent_executor()
        result = executor.invoke({"input": user_message})
        return result.get("output", "I am here to help you find jobs or manage your account. How can I assist?")
    except Exception as e:
        return "I encountered a minor processing error. Please ask your question clearly about jobs, wages, or registration."
