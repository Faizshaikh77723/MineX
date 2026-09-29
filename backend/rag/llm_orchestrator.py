import re
import ollama
from backend.rag.retriever import retrieve_context
from backend.reporting.report_engine import create_pdf_report
from backend.tools.calculator import execute_math_tool

SESSION_MEMORY = []

STANDARD_PROMPT = """You are MineX RAG Assistant, an expert AI for the Ministry of Coal (SIH26023).

RULES:
1. ONLY use the provided context to answer.
2. Domain Notation:
   - "Dec 25", "DEC 25", "Apr 25-Dec 25", and "2024-25" refer to performance data for the years 2024 and 2025.
   - "Mill Te" and "Qty. in MT" represent Coal Production / Offtake volume in Million Tonnes.
   - Opencast and Underground tables represent raw coal extraction metrics.
3. If the user asks for production or growth data and figures are present in the tables, extract and report the exact numerical values.
4. If the context genuinely does not contain the answer, say: "I cannot determine this from my database."
5. Keep answers concise, structured, and cite the document sources.
"""

REPORT_PROMPT = """You are an elite autonomous reporting agent for the Ministry of Coal.
Your task is to generate a formal statutory report based on the provided context and the user's query.

CRITICAL GUARDRAIL:
1. Document Conventions:
   - Shorthand notations such as "DEC 25", "Dec'25", "Apr 25-Dec 25", and "2024-25" ARE valid data for 2024 and 2025.
   - Tables with headers "Mill Te", "MT", "Opencast", "Underground", or "Offtake" contain coal production figures.
2. If the context DOES NOT contain data matching the requested topic or timeframe, reply ONLY with:
   "I cannot determine this from my database. The requested data is not present in the uploaded statutory documents."
3. Do not substitute requested production figures with unrelated safety or reclamation statistics.

If the context supports the query, output using this Markdown structure:
# Executive Summary
[Synthesize key findings and total figures]
# Key Performance & Operational Metrics
[Tabulate or itemize production, growth %, and subsidiary breakdowns]
# Risk & Safety Assessment
[Note operational observations, declines, or relevant safety metrics if available; otherwise state not applicable]
# Actionable Recommendations
[Policy or operational takeaways based on the data]
# Data Sources
[Cite document names, tables, and annexures]
"""

def expand_query(query: str) -> str:
    """Enriches the retrieval query with domain terms to match tabular data."""
    q_lower = query.lower()
    expanded = query
    if any(k in q_lower for k in ["production", "rate", "output", "quantity", "growth"]):
        expanded += " coal production offtake actual growth Mill Te MT raw coal opencast underground"
    if "2025" in q_lower:
        expanded += " DEC 25 Apr 25-Dec 25 2024-25 CIL subsidiary"
    if "10 year" in q_lower or "ten year" in q_lower or "trend" in q_lower:
        expanded += " 2014-15 2024-25 all india raw coal"
    return expanded

def route_query(user_question: str) -> str:
    q_clean = re.sub(r'[^\w\s]', '', user_question.lower()).strip()
    
    greetings = {"hi", "hello", "hey", "who are you", "what do you do", "who created you", "tell me about yourself"}
    if q_clean in greetings:
        return "Hey! I am the MineX RAG Assistant, your specialized document intelligence system for the Ministry of Coal. How can I help you today?"
        
    status_queries = {"how are you", "how are you doing", "what are you doing", "what is up", "hows it going", "whats up"}
    if q_clean in status_queries:
        return "I am processing Ministry of Coal documents and ready to assist! How can I help you analyze coal reports or production statistics today?"

    gratitude = {"thanks", "thank you", "thank you so much", "great thanks"}
    if q_clean in gratitude:
        return "You're welcome! Let me know if you need any further analysis, figures, or reports."

    # Mathematical Intent Router
    if any(k in q_clean for k in ["calculate growth", "percentage increase", "percentage share", "percentage of"]):
        numbers = [float(n) for n in re.findall(r'\d+\.?\d*', user_question)]
        if len(numbers) >= 2:
            if "share" in q_clean or "percentage of" in q_clean:
                math_result = execute_math_tool("share", numbers[0], numbers[1])
            else:
                math_result = execute_math_tool("growth", numbers[0], numbers[1])
            return f"📊 **Statistical Analysis:** For the figures {numbers[0]} and {numbers[1]}, the calculation shows: {math_result}"

    words = q_clean.split()
    if len(words) <= 2 and "coal" in words:
        return "I need a bit more context. Are you looking for coal production data, safety statistics, or a specific mine report?"
        
    return None

def generate_answer(user_question: str) -> dict:
    global SESSION_MEMORY
    
    # 1. Quick Conversational / Math Routing
    fast_reply = route_query(user_question)
    if fast_reply:
        return {"answer": fast_reply, "is_report": False, "pdf_filename": None}
        
    # 2. Context Retrieval with Query Expansion
    search_query = expand_query(user_question)
    context = retrieve_context(search_query)
    
    if not context.strip():
        return {
            "answer": "I cannot determine this from my database. Please ensure the relevant document has been uploaded.",
            "is_report": False,
            "pdf_filename": None
        }

    # 3. Detect Report Intent
    report_keywords = ["report", "detailed report", "statutory report", "summary report", "comprehensive analysis", "dossier"]
    is_report = any(k in user_question.lower() for k in report_keywords)
    system_instructions = REPORT_PROMPT if is_report else STANDARD_PROMPT
    
    final_prompt = f"CONTEXT DOCUMENTS:\n{context}\n\nUSER QUESTION: {user_question}"
    messages = [{'role': 'system', 'content': system_instructions}]
    
    # Keep up to 2 recent turns to retain immediate context without overflowing tokens
    messages.extend(SESSION_MEMORY[-2:])
    messages.append({'role': 'user', 'content': final_prompt})
    
    try:
        response = ollama.chat(
            model='coal_ai_model',
            messages=messages,
            keep_alive=-1,
            options={
                "num_ctx": 8192,     # Expanded to prevent truncating large tabular chunks
                "temperature": 0.1,  # Low temperature for strict factual/numerical adherence
                "num_predict": 1200 if is_report else 450
            }
        )
        
        ai_answer = response['message']['content']
        pdf_file = None

        # 4. Trigger PDF Report Generation (only if report was requested and not aborted)
        if is_report and "I cannot determine this from my database" not in ai_answer:
            print("📑 Triggering Statutory Report Engine (PDF Builder)...")
            pdf_file = create_pdf_report(
                title=user_question[:50],
                query=user_question,
                content_markdown=ai_answer
            )

        # Update Session Memory
        SESSION_MEMORY.append({'role': 'user', 'content': user_question})
        SESSION_MEMORY.append({'role': 'assistant', 'content': ai_answer})
        
        return {
            "answer": ai_answer,
            "is_report": is_report,
            "pdf_filename": pdf_file
        }
        
    except Exception as e:
        return {
            "answer": f"Error connecting to MineX Engine: {str(e)}",
            "is_report": False,
            "pdf_filename": None
        }

def warmup_model():
    print("Pre-warming MineX model in GPU...")
    try:
        ollama.chat(
            model='coal_ai_model', 
            messages=[{'role': 'user', 'content': 'warmup'}], 
            keep_alive=-1,
            options={"num_predict": 1}
        )
    except Exception:
        print("Warmup failed, ensure Ollama is running.")