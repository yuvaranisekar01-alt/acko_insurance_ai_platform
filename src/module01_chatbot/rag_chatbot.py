import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# ------------------------------------------------------------------
# Postgres connection (same pattern as db.py in module02_premium)
# ------------------------------------------------------------------

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)


def log_chat(question: str, answer: str):
    """Logs a single Q&A pair to the chat_logs table."""
    insert_query = text("""
        INSERT INTO chat_logs (question, answer)
        VALUES (:question, :answer)
    """)
    with engine.connect() as conn:
        conn.execute(insert_query, {"question": question, "answer": answer})
        conn.commit()


# ------------------------------------------------------------------
# RAG chain setup
# ------------------------------------------------------------------

SYSTEM_PROMPT = """
You are Acko's insurance assistant, helping customers understand their motor and health insurance policies.

Guidelines:
- Answer ONLY using the context provided below. Do not use outside knowledge.
- If the answer isn't in the provided context, say clearly: "I don't have that information in the available policy documents. Please contact Acko support for details."
- Never invent specific numbers, coverage limits, or policy terms that aren't explicitly stated in the context.
- Be concise and clear — prefer short, direct answers over long explanations.
- Be polite and professional. Greet the customer warmly if this is the start of a conversation.
- If relevant, mention which policy type (Motor/Health) or section the answer comes from.
- This chatbot does not provide legal or financial advice — for complex claims or disputes, direct the customer to Acko's official support channels.

Context:
{context}

Question:
{question}

Answer:
"""


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def build_rag_chain(persist_directory: str):
    """
    Loads the persisted ChromaDB vectorstore and builds the LCEL RAG chain.
    Call this once (cached) when the Streamlit app starts.
    """
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )

    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


def ask(rag_chain, question: str) -> str:
    """Runs a question through the RAG chain and logs it to Postgres."""
    answer = rag_chain.invoke(question)
    try:
        log_chat(question, answer)
    except Exception as e:
        print(f"Warning: failed to log chat to database: {e}")
    return answer

    