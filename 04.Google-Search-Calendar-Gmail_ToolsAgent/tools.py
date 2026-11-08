
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from langchain_google_community import CalendarToolkit, GmailToolkit

from langchain_google_community.calendar.utils import (
    build_calendar_service,
    get_google_credentials,
)

from langchain_google_community.gmail.utils import (
    build_gmail_service
)

credentials = get_google_credentials(
    token_file="token.json",
    scopes=["https://www.googleapis.com/auth/calendar",
            "https://mail.google.com/",
           ],
    client_secrets_file="credentials.json",
)

calendar_resource = build_calendar_service(credentials=credentials)
gmail_resource = build_gmail_service(credentials=credentials)

calendar_toolkit = CalendarToolkit(api_resource=calendar_resource)
gmail_toolkit = GmailToolkit(api_resource=gmail_resource)

calendar_tools = calendar_toolkit.get_tools()
gmail_tools = gmail_toolkit.get_tools()

tavily = TavilySearch(max_results = 2)

embeddings = OllamaEmbeddings(
    model="mxbai-embed-large:latest"   
)

vectorstore = FAISS.load_local(
    "faiss_db",
    embeddings,
    allow_dangerous_deserialization=True
)


#rag
@tool
def rag_retrieval(query: str):
    """Search the company knowledge base and return relevant information."""
    print("\n*************RAG*************")

    results = vectorstore.similarity_search_with_score(query, k=3)

    filtered = [
        doc.page_content
        for doc, score in results
        # if score < 0.4
    ]
    return "\n\n---\n\n".join(filtered) if filtered else "No relevant context found."

#google search
@tool
def google_search(query: str):
    """This tool is used to do the google search"""
    print("\n*************Google Search*************")

    result = tavily.invoke(query)
    return result
tools = [rag_retrieval, google_search, *calendar_tools, *gmail_tools]