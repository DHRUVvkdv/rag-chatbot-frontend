import streamlit as st
import boto3
import hashlib
import os
import re

# Cognito configuration
COGNITO_REGION = st.secrets["COGNITO_REGION"]
COGNITO_USER_POOL_ID = st.secrets["COGNITO_USER_POOL_ID"]
COGNITO_CLIENT_ID = st.secrets["COGNITO_CLIENT_ID"]

LOGIN_ENABLED = False  # Set this to False to disable login

client = boto3.client("cognito-idp", region_name=COGNITO_REGION)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None


def sign_up(email, password, name):
    if not is_valid_email(email):
        st.error("Please enter a valid email address.")
        return

    try:
        response = client.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "name", "Value": name},
                {"Name": "preferred_username", "Value": email},
            ],
        )
        st.success(
            "Sign-up successful! Please check your email to confirm your account."
        )
        st.session_state.signup_stage = "confirm"
        st.session_state.signup_email_value = email
    except client.exceptions.UsernameExistsException:
        # Check if the user exists but is unconfirmed
        try:
            user_info = client.admin_get_user(
                UserPoolId=COGNITO_USER_POOL_ID, Username=email
            )
            if user_info["UserStatus"] == "UNCONFIRMED":
                st.warning(
                    "You have already signed up but haven't confirmed your email. Please check your email for the confirmation code."
                )
                st.session_state.signup_stage = "confirm"
                st.session_state.signup_email_value = email
            else:
                st.error(
                    "Email already exists and is confirmed. Please use a different email or try logging in."
                )
        except client.exceptions.UserNotFoundException:
            st.error("An error occurred. Please try again.")
    except client.exceptions.InvalidPasswordException:
        st.error("Password does not meet the requirements.")
    except client.exceptions.UserLambdaValidationException:
        st.error("Invalid email address.")
    except Exception as e:
        st.error(f"Error: {e}")


def check_password_requirements(password):
    requirements = [
        ("At least 8 characters long", len(password) >= 8),
        ("Contains at least 1 number", bool(re.search(r"\d", password))),
        (
            "Contains at least 1 special character",
            bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)),
        ),
        ("Contains at least 1 uppercase letter", bool(re.search(r"[A-Z]", password))),
        ("Contains at least 1 lowercase letter", bool(re.search(r"[a-z]", password))),
    ]
    return requirements


def confirm_sign_up(username, confirmation_code):
    try:
        client.confirm_sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=username,
            ConfirmationCode=confirmation_code,
        )
        st.success("Account confirmed successfully!")
        return True
    except client.exceptions.CodeMismatchException:
        st.error("Invalid confirmation code. Please try again.")
    except client.exceptions.ExpiredCodeException:
        st.error("Confirmation code has expired. Please request a new one.")
    except Exception as e:
        st.error(f"Error: {e}")
    return False


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
        return True
    except client.exceptions.UserNotFoundException:
        st.error("Username or email not found.")
    except Exception as e:
        st.error(f"Error: {e}")
    return False


def confirm_forgot_password(username_or_email, confirmation_code, new_password):
    try:
        client.confirm_forgot_password(
            ClientId=COGNITO_CLIENT_ID,
            Username=username_or_email,
            ConfirmationCode=confirmation_code,
            Password=new_password,
        )
        return True
    except client.exceptions.CodeMismatchException:
        st.error("Invalid confirmation code.")
    except client.exceptions.ExpiredCodeException:
        st.error("Confirmation code has expired. Please request a new one.")
    except client.exceptions.InvalidPasswordException:
        st.error("Password does not meet the requirements.")
    except Exception as e:
        st.error(f"Error: {e}")
    return False


def main():
    st.set_page_config(
        page_title="LEWAS Lab Chatbot - Login", page_icon="💧", layout="centered"
    )

    # Initialize session state variables
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "signup_stage" not in st.session_state:
        st.session_state.signup_stage = "initial"
    if "reset_stage" not in st.session_state:
        st.session_state.reset_stage = "initial"

    # Get the directory of the current script
    current_dir = os.path.dirname(__file__)

    # Construct the path to the image
    image_path = os.path.join(current_dir, "images", "lewas_logo.png")

    # Use the image in your Streamlit app
    st.image(image_path, width=200)
    st.title("LEWAS Lab Chatbot")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if LOGIN_ENABLED:
        if st.session_state.authenticated:
            st.success("You are logged in!")
            st.markdown("[Go to Chatbot](/1_Chat)", unsafe_allow_html=True)
            # Automatically redirect to chatbot page
            st.switch_page("pages/chat.py")
        else:
            # Tabs for different actions
            tab1, tab2, tab3 = st.tabs(["Log In", "Sign Up", "Forgot Password"])

            with tab1:
                login_form()

            with tab2:
                signup_form()

            with tab3:
                forgot_password_form()

        # Add a logout button in the sidebar with a unique key
        if st.sidebar.button("Logout", key="sidebar_logout"):
            st.session_state.authenticated = False
            st.session_state.access_token = None
            st.session_state.id_token = None
            st.rerun()
    else:
        st.info(
            "Login is currently disabled due to demonstration purposes. You can access the chatbot directly."
        )
        if st.button("Go to Chatbot"):
            st.switch_page("pages/chat.py")

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

    # Footer
    st.markdown("---")
    st.markdown("Created by the LEWAS Lab team | Virginia Tech")

    # Add contact information for issues
    st.sidebar.title("Contact Us")
    st.sidebar.info(
        """
    Is something wrong? Email [lewas.vt@outlook.com](mailto:lewas.vt@outlook.com) or message on 
    [LinkedIn](https://www.linkedin.com/in/dhruvvarshneyvk/).
    """
    )


def login_form():
    with st.form("login_form"):
        st.subheader("Log In")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submit_button = st.form_submit_button("Log In")

        if submit_button:
            log_in(email, password)


def signup_form():
    st.subheader("Sign Up")

    if "signup_stage" not in st.session_state:
        st.session_state.signup_stage = "initial"
    if "signup_email_value" not in st.session_state:
        st.session_state.signup_email_value = ""

    if st.session_state.signup_stage == "initial":
        email = st.text_input(
            "Email", key="signup_email", value=st.session_state.signup_email_value
        )
        name = st.text_input("Name", key="signup_name")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input(
            "Confirm Password", type="password", key="signup_confirm"
        )

        # Display password requirements
        if password:
            requirements = check_password_requirements(password)
            st.write("Password requirements:")
            for req, met in requirements:
                st.markdown(f"{'✅' if met else '❌'} {req}")

        if st.button("Sign Up"):
            if not is_valid_email(email):
                st.error("Please enter a valid email address.")
            elif password == confirm_password:
                requirements = check_password_requirements(password)
                if all(met for _, met in requirements):
                    sign_up(email, password, name)
                    st.session_state.signup_stage = "confirm"
                    st.session_state.signup_email_value = email
                else:
                    st.error("Please meet all password requirements before submitting.")
            else:
                st.error("Passwords do not match.")

    elif st.session_state.signup_stage == "confirm":
        st.info(
            f"Please check your email ({st.session_state.signup_email_value}) for a confirmation code."
        )
        confirmation_code = st.text_input("Confirmation Code")
        if st.button("Confirm Sign Up"):
            if confirm_sign_up(st.session_state.signup_email_value, confirmation_code):
                st.session_state.signup_stage = "login"
                st.rerun()

    elif st.session_state.signup_stage == "login":
        st.success("Your account has been confirmed. Please log in to continue.")
        email = st.text_input(
            "Email", value=st.session_state.signup_email_value, disabled=True
        )
        password = st.text_input("Password", type="password")
        if st.button("Log In"):
            log_in(email, password)

    # Option to resend confirmation code or change email
    if st.session_state.signup_stage == "confirm":
        if st.button("Resend Confirmation Code"):
            resend_confirmation_code(st.session_state.signup_email_value)
            st.success("Confirmation code resent. Please check your email.")

        if st.button("Change Email"):
            st.session_state.signup_stage = "initial"
            st.session_state.signup_email_value = ""
            st.rerun()


def resend_confirmation_code(username):
    try:
        client.resend_confirmation_code(ClientId=COGNITO_CLIENT_ID, Username=username)
    except Exception as e:
        st.error(f"Error resending confirmation code: {e}")


def forgot_password_form():
    st.subheader("Reset Password")

    if st.session_state.reset_stage == "initial":
        username_or_email = st.text_input("Username or Email", key="reset_email_input")
        if st.button("Reset Password"):
            if forgot_password(username_or_email):
                st.session_state.reset_stage = "confirm"
                st.session_state.reset_username = username_or_email
                st.rerun()

    elif st.session_state.reset_stage == "confirm":
        st.info(
            f"Please check your email ({st.session_state.reset_username}) for a confirmation code."
        )
        confirmation_code = st.text_input("Confirmation Code")
        new_password = st.text_input("New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")

        # Display password requirements
        if new_password:
            requirements = check_password_requirements(new_password)
            st.write("Password requirements:")
            for req, met in requirements:
                st.markdown(f"{'✅' if met else '❌'} {req}")

        if st.button("Confirm Password Reset"):
            if new_password != confirm_new_password:
                st.error("Passwords do not match.")
            else:
                requirements = check_password_requirements(new_password)
                if all(met for _, met in requirements):
                    if confirm_forgot_password(
                        st.session_state.reset_username, confirmation_code, new_password
                    ):
                        st.success(
                            "Password reset successfully. You can now log in with your new password."
                        )
                        st.session_state.reset_stage = "initial"
                        st.session_state.reset_username = ""
                        st.rerun()
                else:
                    st.error("Please meet all password requirements before submitting.")

    # Option to resend confirmation code or change email
    if st.session_state.reset_stage == "confirm":
        if st.button("Resend Confirmation Code"):
            if forgot_password(st.session_state.reset_username):
                st.success("Confirmation code resent. Please check your email.")

        if st.button("Change Email"):
            st.session_state.reset_stage = "initial"
            st.session_state.reset_username = ""
            st.rerun()


if __name__ == "__main__":
    main()
