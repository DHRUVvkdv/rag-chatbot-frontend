import streamlit as st
import requests
import json
from datetime import datetime

# Get the API base URL and API key from secrets
API_BASE_URL = st.secrets["API_BASE_URL"]
API_KEY = st.secrets["API_KEY"]

st.set_page_config(page_title="LEWAS Lab Chatbot", page_icon="💧")

st.title("LEWAS Lab Chatbot 💧")

st.markdown(
    """
Welcome to the LEWAS Lab Chatbot! Ask questions about our water quality monitoring 
and research activities, and I'll do my best to answer.
"""
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask a question about LEWAS Lab"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Create a placeholder for the assistant's response
    assistant_response_placeholder = st.empty()

    # Show loading spinner while waiting for response
    with st.spinner("Thinking..."):
        try:
            response = requests.post(
                f"{API_BASE_URL}/query_documents",
                json={"query_text": prompt},
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "API-Key": API_KEY,  # Add the API key to the headers
                },
                timeout=30,  # 30 seconds timeout
            )

            if response.status_code == 200:
                try:
                    response_json = response.json()
                except json.JSONDecodeError:
                    assistant_response = "Error: Unable to parse the server response."
                    additional_info = ""
                    sources = []
                else:
                    assistant_response = response_json.get(
                        "answer_text", "Sorry, I couldn't process that request."
                    )

                    # Format additional information
                    query_id = response_json.get("query_id", "N/A")
                    create_time = datetime.fromtimestamp(
                        response_json.get("create_time", 0)
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    sources = response_json.get("sources", [])

                    additional_info = f"""
                    **Query ID:**  
                    {query_id}

                    **Time:**  
                    {create_time}

                    **Sources:**
                    """
            elif response.status_code == 403:
                assistant_response = "Error: Invalid API key or unauthorized access."
                additional_info = ""
                sources = []
            else:
                assistant_response = (
                    f"Error: Received status code {response.status_code}"
                )
                additional_info = ""
                sources = []

        except requests.RequestException as e:
            assistant_response = f"Error: Unable to connect to the server. {str(e)}"
            additional_info = ""
            sources = []

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        assistant_response_placeholder.markdown(assistant_response)
        if additional_info:
            with st.expander("View answer details"):
                st.markdown(additional_info)
                for i, source in enumerate(sources):
                    if i == 0:
                        st.markdown(f"- {source}")
                    else:
                        st.markdown(f"* {source}")
                st.markdown("---")  # Add a horizontal line at the end

    # Add assistant response to chat history
    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_response}
    )

# Add some information about LEWAS Lab
st.sidebar.title("About LEWAS Lab")
st.sidebar.info(
    """
The LEWAS (Learning Enhanced Watershed Assessment System) Lab is dedicated to 
real-time water quality monitoring and research. We use advanced technology to 
collect, analyze, and share data about water resources.
"""
)

# Add a link to more information
st.sidebar.markdown("[Learn more about LEWAS Lab](https://lewas.ictas.vt.edu/)")

# Add a clear button for chat history
if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = []
    st.experimental_rerun()

# Footer
st.markdown(
    """
---
Created by the LEWAS Lab team | Virginia Tech
"""
)
