# Multi-Agent AI Travel Planner 🧭

A production-grade, containerized multi-agent system that plans complete trips by coordinating specialized AI agents (Flights, Hotels, Weather, Budget, and Itinerary). 

## Architecture & Features
- **LangGraph Orchestration:** A Supervisor agent routes user requests to specialized worker agents.
- **Model Context Protocol (MCP):** Integrates external MCP servers for real-time weather and flight data.
- **Human-in-the-Loop:** The graph pauses for human approval before generating the final polished itinerary.
- **Persistent Memory:** Uses a PostgreSQL checkpointer to save state, allowing users to resume conversations.
- **Custom UI:** A heavily customized Streamlit interface featuring a live agent-tracking canvas, interactive budget charts, and structured result cards.
- **Dockerized:** Fully containerized with `docker-compose` for seamless local development and cloud deployment.

## Tech Stack
- **Framework:** LangGraph, LangChain
- **LLM:** Google Gemini (via `langchain-google-genai`)
- **Database:** PostgreSQL (via `psycopg`)
- **Tools:** Tavily Search, OpenWeatherMap, AviationStack (MCP)
- **Frontend:** Streamlit, Plotly, Custom CSS/SVG
- **Infrastructure:** Docker, Docker Compose

## How to Run Locally

1. Clone the repository:
   ```bash
   git clone https://github.com/sarfraz-ali-ai/AI-Travel-Planning-App-using-LangGraph-and-MCP.git
   cd AI-Travel-Planning-App-using-LangGraph-and-MCP
