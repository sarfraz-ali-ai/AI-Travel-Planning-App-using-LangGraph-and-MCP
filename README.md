# Multi-Agent AI Travel Planner 🧭

**🔴 [Live Demo on AWS](http://52.64.241.75:8501/)**

A stateful, multi-agent AI application that plans complete trips by coordinating specialized agents. Built with LangGraph, it uses a Supervisor router to delegate tasks (Flights, Hotels, Weather, Budget) and pauses for Human-in-the-Loop approval before finalizing the itinerary.

## 🧠 Architecture & Features

- **LangGraph Orchestration:** Implements a deterministic state machine with a Supervisor agent that routes user requests to specialized worker agents based on the context.
- **Model Context Protocol (MCP):** Integrates external MCP servers (`stdio` transport) for real-time external tool calling (weather and flight data), bypassing the need for hardcoded API wrappers.
- **Human-in-the-Loop:** The graph execution intentionally pauses (`interrupt()`) after drafting an itinerary, allowing the user to review, request changes, or approve the plan before the final agent generates the response.
- **Persistent Memory:** Uses a PostgreSQL database via `PostgresSaver` to check-point and save the state of every conversation, enabling users to resume past trips.
- **Custom UI:** A heavily customized Streamlit interface featuring a live agent-tracking canvas, interactive budget charts, and structured result cards.
- **Fully Containerized:** Uses Docker and Docker Compose to run both the Streamlit app and the PostgreSQL database in isolated containers.

## 🛠️ Tech Stack

- **Framework:** LangGraph, LangChain
- **LLM:** Google Gemini (via `langchain-google-genai`)
- **Database:** PostgreSQL (via `psycopg` and `langgraph-checkpoint-postgres`)
- **Tools:** Tavily Search, OpenWeatherMap, AviationStack (via MCP)
- **Frontend:** Streamlit, Plotly, Custom CSS/SVG
- **Infrastructure:** Docker, Docker Compose, AWS EC2

## 🚀 How to Run Locally

Because this project uses a PostgreSQL database and local MCP subprocesses, **Docker is the required way to run it**. 

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sarfraz-ali-ai/AI-Travel-Planning-App-using-LangGraph-and-MCP.git
   cd AI-Travel-Planning-App-using-LangGraph-and-MCP
