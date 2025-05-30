import streamlit as st
import requests
import json
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key

# Get API URLs and keys from secrets
API_BASE_URL = st.secrets["API_BASE_URL"]
API_BASE_URL_RAG = st.secrets["API_BASE_URL_RAG"]  # Separate RAG endpoint
API_KEY = st.secrets["API_KEY"]
API_KEY_RAG = st.secrets["API_KEY_RAG"]  # New RAG-specific API key
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_REGION_NAME = st.secrets["AWS_REGION_NAME"]

LOGIN_ENABLED = False  # Set this to False to disable login

dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION_NAME,
)
table = dynamodb.Table("lewas-chatbot-queries")


def update_feedback_in_dynamodb(query_id, user_liked):
    try:
        # Try to update the existing item
        response = table.update_item(
            Key={"query_id": query_id},
            UpdateExpression="set user_liked = :ul",
            ExpressionAttributeValues={":ul": user_liked},
            ReturnValues="UPDATED_NEW",
        )
        return True
    except Exception as e:
        # For now, just catch the error and continue
        # You may want to log this for troubleshooting
        print(f"Feedback update error: {str(e)}")
        # Continue without feedback rather than breaking the app
        return False


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
    if LOGIN_ENABLED:
        if (
            "authenticated" not in st.session_state
            or not st.session_state.authenticated
        ):
            st.warning("Please log in to access the chatbot.")
            st.markdown("[Go to Login Page](/)")
            st.stop()
        else:
            st.success("You are successfully logged in!")
    else:
        # If login is disabled, set authenticated to True
        st.session_state.authenticated = True

    st.title("LEWAS Lab Chatbot 💧")
    st.markdown(
        """
    Welcome to the LEWAS Lab Chatbot! Ask questions about our water quality monitoring 
    and research activities, and I'll do my best to answer. You can also ask for visualizations 
    of weather data like temperature, humidity, or pressure.
    """
    )

    # Initialize chat history, details, and feedback
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "details" not in st.session_state:
        st.session_state.details = {}
    if "feedback" not in st.session_state:
        st.session_state.feedback = {}

    # Display chat messages from history on app rerun
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

            if message["role"] == "assistant":
                details = st.session_state.details.get(i, {}).get(
                    "additional_info", "No details available."
                )
                with st.expander("View Details", expanded=False):
                    st.markdown(details, unsafe_allow_html=True)

                # Add feedback buttons
                if i not in st.session_state.feedback:
                    st.write("Did you like this response?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("👍", key=f"thumbs_up_{i}"):
                            query_id = st.session_state.details.get(i, {}).get(
                                "query_id", "N/A"
                            )
                            if update_feedback_in_dynamodb(query_id, True):
                                st.session_state.feedback[i] = "positive"
                                st.success("Thank you for your positive feedback!")
                            else:
                                # Quietly continue without error message
                                st.session_state.feedback[i] = "positive"
                                st.success("Thank you for your positive feedback!")
                    with col2:
                        if st.button("👎", key=f"thumbs_down_{i}"):
                            query_id = st.session_state.details.get(i, {}).get(
                                "query_id", "N/A"
                            )
                            if update_feedback_in_dynamodb(query_id, False):
                                st.session_state.feedback[i] = "negative"
                                st.error(
                                    "We're sorry to hear that. We'll work on improving."
                                )
                            else:
                                # Quietly continue without error message
                                st.session_state.feedback[i] = "negative"
                                st.error(
                                    "We're sorry to hear that. We'll work on improving."
                                )
                else:
                    if st.session_state.feedback[i] == "positive":
                        st.success("You gave positive feedback for this response.")
                    else:
                        st.error("You gave negative feedback for this response.")

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
                # First, classify the query using the smart_query endpoint
                classification_response = requests.post(
                    f"{API_BASE_URL}/classify_query",
                    json={"query_text": prompt},
                    headers={
                        "accept": "application/json",
                        "Content-Type": "application/json",
                        "API-Key": API_KEY,
                    },
                    timeout=10,
                )

                if classification_response.status_code == 200:
                    # Get the classification result
                    classification_data = classification_response.json()
                    classification = classification_data.get("classification", "RAG")

                    # Select appropriate API base URL, endpoint, and API key
                    if classification == "RAG":
                        # Use RAG endpoint on the RAG server with RAG-specific API key
                        base_url = API_BASE_URL_RAG
                        endpoint = "/query_documents"
                        api_key = API_KEY_RAG  # Use RAG-specific API key
                    else:
                        # Use the normal API for visualizations and live data
                        base_url = API_BASE_URL
                        endpoint = "/smart_query"
                        api_key = API_KEY  # Use standard API key

                    # Now make the actual query with the appropriate endpoint and API key
                    response = requests.post(
                        f"{base_url}{endpoint}",
                        json={"query_text": prompt},
                        headers={
                            "accept": "application/json",
                            "Content-Type": "application/json",
                            "API-Key": api_key,  # Use the selected API key
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
                            query_id = "N/A"
                        else:
                            assistant_response = response_json.get(
                                "answer_text", "Sorry, I couldn't process that request."
                            )
                            query_id = response_json.get("query_id", "N/A")
                            create_time = datetime.fromtimestamp(
                                response_json.get("create_time", 0)
                            ).strftime("%Y-%m-%d %H:%M:%S")
                            sources = response_json.get("sources", [])

                            additional_info = f"""
                            <p><strong>Query ID:</strong> {query_id}</p>
                            <p><strong>Time:</strong> {create_time}</p>
                            <p><strong>Query Type:</strong> {classification}</p>
                            <p><strong>Sources:</strong></p>
                            {format_sources(sources)}
                            """
                    else:
                        assistant_response = (
                            f"Error: Received status code {response.status_code}"
                        )
                        additional_info = "No details available."
                        query_id = "N/A"
                else:
                    # If classification fails, default to using the smart_query endpoint with standard API key
                    response = requests.post(
                        f"{API_BASE_URL}/smart_query",
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
                            query_id = "N/A"
                        else:
                            assistant_response = response_json.get(
                                "answer_text", "Sorry, I couldn't process that request."
                            )
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
                    else:
                        assistant_response = (
                            f"Error: Received status code {response.status_code}"
                        )
                        additional_info = "No details available."
                        query_id = "N/A"

            except requests.RequestException as e:
                assistant_response = f"Error: Unable to connect to the server. {str(e)}"
                additional_info = "No details available."
                query_id = "N/A"

        # Add assistant response to chat history
        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_response}
        )

        # Store details
        st.session_state.details[len(st.session_state.messages) - 1] = {
            "additional_info": additional_info,
            "query_id": query_id,
        }

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

    # Add chatbot capabilities overview
    st.sidebar.title("🤖 Chatbot Capabilities")
    st.sidebar.markdown(
        """
    **🔴 Live Environmental Data**
    - Current sensor readings (16 parameters)
    - Recent trends and measurements
    
    **📊 Data Visualizations** 
    - 24-hour trend graphs for any parameter
    - Professional charts with proper units
    
    **📚 Knowledge Base**
    - LEWAS Lab research and operations
    - Technical questions about monitoring
    - Educational content about water quality
    """
    )

    # Add visualization info
    st.sidebar.title("💡 Try These Questions")
    st.sidebar.markdown(
        """
    **For Live Data:**
    - "What's the current pH?"
    - "How much oxygen is in the water?"
    - "Is it raining?"
    
    **For Visualizations:**
    - "Graph dissolved oxygen trends"
    - "Show me humidity over time"
    - "Plot water temperature data"
    
    **For Information:**
    - "What research does LEWAS do?"
    - "How does water monitoring work?"
    - "Why is turbidity important?"
    """
    )

    # Add complete user guide section
    st.sidebar.title("📖 Complete User Guide")
    st.sidebar.info(
        """
    For detailed information about all 16 monitoring parameters, advanced features, 
    and comprehensive examples, check out our complete user guide.
    """
    )
    st.sidebar.markdown(
        "[📋 View Complete User Guide](https://docs.google.com/document/d/1GuQ2WcPjabqR3VkJuyAe7hrCV_3evtd9fc0i9w6zz60/edit?usp=sharing)"
    )

    # Add monitoring parameters quick reference
    with st.sidebar.expander("📊 Quick Parameter Reference"):
        st.markdown(
            """
        **Water Quality (7 params):**
        pH, Dissolved Oxygen, Temperature, Turbidity, Conductance, Salinity, ORP
        
        **Water Flow (4 params):**
        Stage, Flow Rate, Velocity (Smoothed & Raw)
        
        **Weather (5 params):**
        Air Temp, Humidity, Pressure, Rain Intensity, Rain Accumulation
        """
        )

    # Add a link to more information
    st.sidebar.markdown(
        "[Learn more about LEWAS Lab](https://lewasenge.s4.es.cloud.vt.edu/)"
    )

    # Add contact information for issues
    st.sidebar.title("Contact Us")
    st.sidebar.info(
        """
    Is something wrong? Email [dhruvvarshney@vt.edu](mailto:dhruvvarshney@vt.edu) or message on 
    [LinkedIn](https://www.linkedin.com/in/dhruvvarshneyvk/).
    """
    )

    # Add a clear button for chat history
    if st.sidebar.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.details = {}
        st.session_state.feedback = {}
        st.rerun()

    # Add a logout button
    if LOGIN_ENABLED:
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.query_params.clear()
            st.rerun()
    else:
        st.sidebar.info("Login is currently disabled.")

    # Footer
    st.markdown(
        """
    ---
    Created by Dhruv Varshney & LEWAS Lab team | Virginia Tech
    """
    )


if __name__ == "__main__":
    main()
