import streamlit as st
import boto3
import hashlib
import os

# Cognito configuration
COGNITO_REGION = st.secrets["COGNITO_REGION"]
COGNITO_USER_POOL_ID = st.secrets["COGNITO_USER_POOL_ID"]
COGNITO_CLIENT_ID = st.secrets["COGNITO_CLIENT_ID"]

client = boto3.client("cognito-idp", region_name=COGNITO_REGION)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def sign_up(username, password, email, name):
    try:
        response = client.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=username,
            Password=password,
            UserAttributes=[
                {"Name": "preferred_username", "Value": username},
                {"Name": "email", "Value": email},
                {"Name": "name", "Value": name},
            ],
        )
        st.success(
            "Sign-up successful! Please check your email to confirm your account."
        )
    except client.exceptions.UsernameExistsException:
        st.error("Username already exists.")
    except client.exceptions.InvalidPasswordException:
        st.error("Password does not meet the requirements.")
    except client.exceptions.UserLambdaValidationException:
        st.error("Invalid email address.")
    except Exception as e:
        st.error(f"Error: {e}")


def confirm_sign_up(username, confirmation_code):
    try:
        client.confirm_sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=username,
            ConfirmationCode=confirmation_code,
        )
        st.success("Account confirmed! You can now log in.")
    except client.exceptions.CodeMismatchException:
        st.error("Invalid confirmation code.")
    except client.exceptions.ExpiredCodeException:
        st.error("Confirmation code has expired.")
    except Exception as e:
        st.error(f"Error: {e}")


def log_in(username_or_email, password):
    try:
        response = client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username_or_email, "PASSWORD": password},
        )
        st.session_state.authenticated = True
        st.session_state.access_token = response["AuthenticationResult"]["AccessToken"]
        st.session_state.id_token = response["AuthenticationResult"]["IdToken"]
        st.success("You are logged in!")
        # Instead of st.experimental_rerun(), use:
        st.switch_page("pages/chat.py")
    except client.exceptions.NotAuthorizedException:
        st.error("Incorrect username/email or password.")
    except client.exceptions.UserNotConfirmedException:
        st.error("User is not confirmed. Please check your email.")
    except Exception as e:
        st.error(f"Error: {e}")


def forgot_password(username_or_email):
    try:
        client.forgot_password(ClientId=COGNITO_CLIENT_ID, Username=username_or_email)
        st.success(
            "Password reset requested. Please check your email for the confirmation code."
        )
    except client.exceptions.UserNotFoundException:
        st.error("Username or email not found.")
    except Exception as e:
        st.error(f"Error: {e}")


def confirm_forgot_password(username_or_email, confirmation_code, new_password):
    try:
        client.confirm_forgot_password(
            ClientId=COGNITO_CLIENT_ID,
            Username=username_or_email,
            ConfirmationCode=confirmation_code,
            Password=new_password,
        )
        st.success(
            "Password reset successful! You can now log in with your new password."
        )
    except client.exceptions.CodeMismatchException:
        st.error("Invalid confirmation code.")
    except client.exceptions.ExpiredCodeException:
        st.error("Confirmation code has expired.")
    except client.exceptions.InvalidPasswordException:
        st.error("Password does not meet the requirements.")
    except Exception as e:
        st.error(f"Error: {e}")


def main():
    st.set_page_config(
        page_title="LEWAS Lab Chatbot - Login", page_icon="💧", layout="centered"
    )

    # Get the directory of the current script
    current_dir = os.path.dirname(__file__)

    # Construct the path to the image
    image_path = os.path.join(current_dir, "images", "lewas_logo.png")

    # Use the image in your Streamlit app
    st.image(image_path, width=200)
    st.title("LEWAS Lab Chatbot")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        st.success("You are logged in!")
        st.markdown("[Go to Chatbot](/1_Chat)", unsafe_allow_html=True)
        # Automatically redirect to chatbot page
        st.experimental_set_query_params(page="1_Chat")
        st.experimental_rerun()
    else:
        # Tabs for different actions
        tab1, tab2, tab3 = st.tabs(["Log In", "Sign Up", "Forgot Password"])

        with tab1:
            login_form()

        with tab2:
            signup_form()

        with tab3:
            forgot_password_form()

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

    # Add a logout button in the sidebar with a unique key
    if st.sidebar.button("Logout", key="sidebar_logout"):
        st.session_state.authenticated = False
        st.session_state.access_token = None
        st.session_state.id_token = None
        st.experimental_rerun()

    # Footer
    st.markdown("---")
    st.markdown("Created by the LEWAS Lab team | Virginia Tech")


def login_form():
    with st.form("login_form"):
        st.subheader("Log In")
        username_or_email = st.text_input("Username or Email", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        remember_me = st.checkbox("Remember Me")
        submit_button = st.form_submit_button("Log In")

        if submit_button:
            log_in(username_or_email, password)


def signup_form():
    with st.form("signup_form"):
        st.subheader("Sign Up")
        username = st.text_input("Username", key="signup_username")
        email = st.text_input("Email", key="signup_email")
        name = st.text_input("Name", key="signup_name")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input(
            "Confirm Password", type="password", key="signup_confirm"
        )
        submit_button = st.form_submit_button("Sign Up")

        if submit_button:
            if password == confirm_password:
                sign_up(username, password, email, name)
            else:
                st.error("Passwords do not match.")


def forgot_password_form():
    with st.form("forgot_password_form"):
        st.subheader("Reset Password")
        username_or_email = st.text_input("Username or Email", key="reset_email")
        submit_button = st.form_submit_button("Reset Password")

        if submit_button:
            forgot_password(username_or_email)


if __name__ == "__main__":
    main()
