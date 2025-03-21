import streamlit as st
import sqlite3, json, tempfile, os
import numpy as np
# from gtts import gTTS
# from gtts.tts import gTTSError

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_community.embeddings import HuggingFaceEmbeddings

# ----- Document Processing & SQL Storage -----
def process_documents(uploaded_files):
    texts = []
    for file in uploaded_files:
        file_extension = os.path.splitext(file.name)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        loader = None
        if file_extension == ".pdf":
            loader = PyPDFLoader(temp_file_path)
        elif file_extension in [".docx", ".doc"]:
            loader = Docx2txtLoader(temp_file_path)
        elif file_extension == ".txt":
            loader = TextLoader(temp_file_path)

        if loader:
            loaded_docs = loader.load()  # returns a list of Document objects
            texts.extend(loaded_docs)
            os.remove(temp_file_path)

    # Split documents into chunks
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=100, length_function=len)
    text_chunks = text_splitter.split_documents(texts)

    # Create embeddings and store them in SQL
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2",
                                         model_kwargs={'device': 'cpu'})
    store_embeddings_sql(text_chunks, embeddings)
    return "Documents processed and embeddings stored in SQL."

def store_embeddings_sql(text_chunks, embeddings):
    # Connect to (or create) the SQLite database
    conn = sqlite3.connect("embeddings.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            embedding TEXT
        )
    """)
    # Insert each text chunk and its embedding (serialized as JSON)
    for chunk in text_chunks:
        # Use .page_content if available (from Document object), else convert to string
        content = chunk.page_content if hasattr(chunk, "page_content") else str(chunk)
        embedding_vector = embeddings.embed_query(content)
        embedding_json = json.dumps(embedding_vector)
        cursor.execute("INSERT INTO embeddings (content, embedding) VALUES (?, ?)", (content, embedding_json))
    conn.commit()
    conn.close()

# ----- Retrieval from SQL -----
def retrieve_similar_documents(query, k=2):
    # Compute the embedding for the query
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2",
                                         model_kwargs={'device': 'cpu'})
    query_embedding = embeddings.embed_query(query)
   
    # Connect to the SQLite database and fetch stored embeddings
    conn = sqlite3.connect("embeddings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT content, embedding FROM embeddings")
    rows = cursor.fetchall()
    conn.close()

    def cosine_similarity(a, b):
        a = np.array(a)
        b = np.array(b)
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    # Calculate similarity for each stored document
    similarities = []
    for row in rows:
        content, embedding_json = row
        embedding_vector = json.loads(embedding_json)
        sim = cosine_similarity(query_embedding, embedding_vector)
        similarities.append((content, sim))
    similarities.sort(key=lambda x: x[1], reverse=True)
    top_matches = similarities[:k]
    return top_matches

# ----- Generate LLM Response -----
def get_response(user_query, chat_history):
    llm = ChatOllama(model="llama3")
    # Retrieve similar documents stored in SQL
    similar_docs = retrieve_similar_documents(user_query, k=2)
    context = "\n\n".join([doc for doc, score in similar_docs])
   
    # Build a prompt that includes context and chat history
    prompt = f"Context:\n{context}\n\nChat History:\n"
    for msg in chat_history:
        role = "User" if isinstance(msg, HumanMessage) else "AI"
        prompt += f"{role}: {msg.content}\n"
    prompt += f"User: {user_query}\nAI:"
   
    response = llm([HumanMessage(content=prompt)])
    return response.content

# ----- Speech-to-Text and Text-to-Speech Utilities -----


# ----- Streamlit UI -----
st.set_page_config(page_title="FAUGPT with SQL Embeddings", page_icon="🤖", layout="wide")

# Sidebar: File upload and document processing
with st.sidebar:
    st.title("FAUGPT with SQL Embeddings")
    uploaded_files = st.file_uploader("Upload documents", accept_multiple_files=True)
    if st.button("Process Documents"):
        if uploaded_files:
            result_msg = process_documents(uploaded_files)
            st.success(result_msg)
        else:
            st.warning("Please upload documents first.")
   
    if st.button("New Chat"):
        st.session_state.chat_history = [AIMessage(content="Hi, I'm a bot. How can I help you?")]
        st.experimental_rerun()
   
    st.markdown("---")

# Main chat area
main_container = st.container()

with main_container:
    # Initialize chat history if not already done
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [AIMessage(content="Hi, I'm a bot. How can I help you?")]

    # Display conversation history
    for message in st.session_state.chat_history:
        with st.chat_message("AI" if isinstance(message, AIMessage) else "Human"):
            st.markdown(message.content)
   
    # User input area
    with st.container():
        col1, col2, col3 = st.columns([0.88, 0.04, 0.04])
        with col1:
            user_query = st.text_input("Type your message here...", key="user_input", label_visibility="collapsed")
        with col2:
            speak_button = st.button("🎤")
        with col3:
            send_button = st.button("➤")
   
    # Handle speech input
    
    # When a query is submitted, get a response from the LLM using SQL-based retrieval
    if send_button or user_query:
        if user_query:
            st.session_state.chat_history.append(HumanMessage(content=user_query))
            with st.chat_message("Human"):
                st.markdown(user_query)
            with st.chat_message("AI"):
                response_container = st.empty()
                response = get_response(user_query, st.session_state.chat_history)
                response_container.markdown(response)
                # Convert response to speech and play audio
                # audio_file = text_to_speech(response)
            
            st.session_state.chat_history.append(AIMessage(content=response))

# Some CSS styling to improve the UI
st.markdown("""
<style>
.stTextInput > div > div > input {
    border-radius: 20px;
}
.stButton > button {
    border-radius: 20px;
    height: 2.4em;
    line-height: 1;
    padding: 0.3em -11px;
    margin-top: 1px;
}
.stSidebar {
    background-color: #f0f2f6;
}
div.row-widget.stButton {
    margin-top: 1px;
}
</style>
""", unsafe_allow_html=True)
