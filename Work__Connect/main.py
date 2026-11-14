"""
WorkConnect FastAPI Backend (main.py)
- Integrates LangChain ChatGroq (model: llama3-8b-8192) with graceful fallback
- ReAct Agent with 3 tools: Search_Document, App_Guide_Tool, Job_Search_Tool
"""

import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="WorkConnect Agentic AI API")

try:
    from langchain_core.tools import tool
    from langchain_groq import ChatGroq
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain_core.prompts import PromptTemplate
    from app_guide_rag import App_Guide_Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    def tool(func):
        return func
    def App_Guide_Tool(query: str):
        return "Please refer to the app guide on the WorkConnect homepage."

if LANGCHAIN_AVAILABLE:
    llm = ChatGroq(
        model="llama3-8b-8192",
        temperature=0.2,
        groq_api_key=os.environ.get("GROQ_API_KEY")
    )

    @tool
    def Search_Document(query: str) -> str:
        """Use this tool for general questions about labor laws, daily wage ranges, platform matching weights, or WorkConnect general features."""
        q_lower = query.lower()
        if "match" in q_lower or "weight" in q_lower:
            return "WorkConnect matching weights: Skills 35%, Location 20%, Experience 15%, Wage 15%, Availability 10%, Rating 5%."
        elif "privacy" in q_lower or "data" in q_lower:
            return "WorkConnect complies strictly with the Digital Personal Data Protection Act, 2023 (DPDP Act, 2023)."
        elif "wage" in q_lower or "salary" in q_lower:
            return "Daily wages on WorkConnect typically range from ₹500 to ₹1,200 per day."
        return "WorkConnect connects local workers (farmers, masons, drivers) with employers across India securely and efficiently."

    @tool
    def Job_Search_Tool(query: str) -> str:
        """Use this tool when users ask to search for jobs specifying a skill/trade and/or location."""
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

    tools = [Search_Document, App_Guide_Tool, Job_Search_Tool]

    react_prompt = PromptTemplate.from_template("""
You are a helpful, respectful, and concise AI assistant for the WorkConnect platform.
CRITICAL INSTRUCTIONS:
- If the user asks "How do I...", "Where do I click...", or "What are the steps...", you MUST use the App_Guide_Tool.
- When answering "how-to" questions, structure the response as a clear, numbered list of steps. Do not use long paragraphs.
- Keep the tone helpful and encouraging.
- Do not promise jobs; remind users that final hiring is up to the employer.

You have access to the following tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
...
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!
Question: {input}
Thought:{agent_scratchpad}
""")

    def get_agent_executor():
        agent = create_react_agent(llm, tools, react_prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    try:
        if not LANGCHAIN_AVAILABLE:
            return {"success": True, "reply": "WorkConnect AI Assistant is online. Please use the main app interface at /browse_jobs or /employer/dashboard."}
        executor = get_agent_executor()
        result = executor.invoke({"input": req.message})
        return {
            "success": True,
            "reply": result.get("output", "I am here to help you navigate WorkConnect or find jobs. How can I assist?")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
