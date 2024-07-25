import streamlit as st
import requests
import json
from datetime import datetime

# Get the API base URL and API key from secrets
API_BASE_URL = st.secrets["API_BASE_URL"]
API_KEY = st.secrets["API_KEY"]


def format_sources(sources):
    if not sources:
        return "No sources available."

    formatted_sources = []
    for source in sources:
        # Remove any leading/trailing whitespace and existing bullet points
        source = source.strip().lstrip("*- ")

        # Split the source into parts (assuming the last part is the URL)
        parts = source.split(" - ")
        if len(parts) > 1:
            text = " - ".join(parts[:-1])
            url = parts[-1]
            # Create an HTML anchor tag for the link
            formatted_source = f'{text} - <a href="{url}" target="_blank">{url}</a>'
        else:
            formatted_source = source

        # Add a standardized bullet point with HTML
        formatted_sources.append(f"<li>{formatted_source}</li>")

    return "<ul>" + "".join(formatted_sources) + "</ul>"


def main():
    st.set_page_config(page_title="LEWAS Lab Chatbot", page_icon="💧")

    # Check authentication
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("Please log in to access the chatbot.")
        st.markdown("[Go to Login Page](/)")
        st.stop()
    else:
        st.success("You are successfully logged in!")
        st.title("LEWAS Lab Chatbot 💧")

        st.markdown(
            """
        Welcome to the LEWAS Lab Chatbot! Ask questions about our water quality monitoring 
        and research activities, and I'll do my best to answer.
        """
        )

        # Initialize chat history and details
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "details" not in st.session_state:
            st.session_state.details = {}

        # Display chat messages from history on app rerun
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant":
                    details = st.session_state.details.get(i, "No details available.")
                    with st.expander("View Details", expanded=False):
                        st.markdown(details, unsafe_allow_html=True)

        # React to user input
        if prompt := st.chat_input("Ask a question about LEWAS Lab"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)

            # Show loading spinner while waiting for response
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/query_documents",
                        json={"query_text": prompt},
                        headers={
                            "accept": "application/json",
                            "Content-Type": "application/json",
                            "API-Key": API_KEY,
                        },
                        timeout=30,
                    )

                    if response.status_code == 200:
                        try:
                            response_json = response.json()
                        except json.JSONDecodeError:
                            assistant_response = (
                                "Error: Unable to parse the server response."
                            )
                            additional_info = "No details available."
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
                            <p><strong>Query ID:</strong> {query_id}</p>
                            <p><strong>Time:</strong> {create_time}</p>
                            <p><strong>Sources:</strong></p>
                            {format_sources(sources)}
                            """

                    elif response.status_code == 403:
                        assistant_response = (
                            "Error: Invalid API key or unauthorized access."
                        )
                        additional_info = "No details available."
                    else:
                        assistant_response = (
                            f"Error: Received status code {response.status_code}"
                        )
                        additional_info = "No details available."

                except requests.RequestException as e:
                    assistant_response = (
                        f"Error: Unable to connect to the server. {str(e)}"
                    )
                    additional_info = "No details available."

            # Add assistant response to chat history
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_response}
            )

            # Store details
            st.session_state.details[len(st.session_state.messages) - 1] = (
                additional_info
            )

            # Display assistant response
            with st.chat_message("assistant"):
                st.markdown(assistant_response)
                with st.expander("View Details", expanded=False):
                    st.markdown(additional_info, unsafe_allow_html=True)

            # Rerun to update the chat history
            st.rerun()

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
        st.session_state.details = {}
        st.rerun()

    # Add a logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.query_params.clear()
        st.rerun()

    # Footer
    st.markdown(
        """
    ---
    Created by the LEWAS Lab team | Virginia Tech
    """
    )


if __name__ == "__main__":
    main()
