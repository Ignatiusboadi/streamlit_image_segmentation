import base64
import io
import requests
import streamlit as st
import zipfile
import os

try:
    if os.getenv('DOCKER_ENV') == "true":
        API_URL = "http://host.docker.internal:8000"
    else:
        API_URL = "http://127.0.0.1:8000"
except:
    API_URL = "http://127.0.0.1:8000"


st.set_page_config(page_title="BRAIN SEGMENTATION")
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'stored_token' not in st.session_state:
    st.session_state['stored_token'] = None


def add_bg_from_local(image_file):
    with open(image_file, "rb") as file:
        encoded_image = base64.b64encode(file.read()).decode()
    st.markdown(
        f"""
         <style>
         .stApp {{
             background-image: url("data:image/png;base64,{encoded_image}");
             background-size: cover;
             background-position: center;
         }}
         </style>
         """,
        unsafe_allow_html=True
    )


add_bg_from_local("assets/grad.webp")

st.markdown("<h1 style='text-align: center; color: white;'>BRAIN IMAGE TUMOR SEGMENTATION</h1>", unsafe_allow_html=True)


def generate_token(username, password):
    print(username, password)
    if username is None or password is None:
        return st.error("Failed to generate token. Please check your credentials.")
    print('request for token')
    response = requests.post(f"{API_URL}/token", data={"username": username, "password": password})
    try:
        if response.status_code == 200:
            st.session_state['stored_token'] = response.json().get('access_token')
            st.success("Token sent to your email. Enter the token below to authenticate.")
        else:
            st.error("Failed to generate token. Please check your credentials.")
    except AttributeError:
        st.error("Failed to generate token. Please check your credentials.")


def login_page():
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Generate Token"):
        if username and password:
            generate_token(username, password)

    token_input = st.text_input("Enter Token")

    if st.button("Authenticate"):
        if token_input == st.session_state.get('stored_token', ''):
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Invalid token.")


def segment_images_page():
    uploaded_files = st.file_uploader("Upload Folder", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

    if uploaded_files:
        allowed_extensions = ['jpg', 'jpeg', 'png']
        invalid_files = [file.name for file in uploaded_files if
                         file.name.split('.')[-1].lower() not in allowed_extensions]

        if invalid_files:
            st.error(f"Invalid file types: {', '.join(invalid_files)}. Please upload only JPG, JPEG, or PNG files.")
        else:
            st.write(f"You have uploaded {len(uploaded_files)} file(s). Click 'Segment files' to proceed.")

        if st.button("Segment Scans"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zf:
                for uploaded_file in uploaded_files:
                    zf.writestr(uploaded_file.name, uploaded_file.getvalue())

            zip_buffer.seek(0)
            files = {'file': ('segmented_scans.zip', zip_buffer, 'application/zip')}
            headers = {'Authorization': f"Bearer {st.session_state['stored_token']}"}

            response = requests.post(f"{API_URL}/prediction", headers=headers, files=files)

            if response.status_code == 200:
                st.download_button('Download Segmented Scans', data=response.content, file_name='segmented_scans.zip')
                st.success("Segmentation successful!")
            else:
                st.error("Segmentation failed. Please try again.")


def check_data_drift_page():
    if st.button("Check Data Drift"):
        headers = {'Authorization': f"Bearer {st.session_state['stored_token']}"}
        response = requests.post(f'{API_URL}/get_drift_report', headers=headers)

        if response.status_code == 200:
            try:
                if st.download_button('Download Data Drift Report', data=response.content,
                                   file_name='data_drift_report.zip'):
                    st.success("Download successful!")
            except Exception as e:
                st.error(f'Failed to download the report due to {e}. Try again later or contact Admin.')
        else:
            st.error(f"{response.status_code} error. Try again later.")


def main_dashboard():
    tabs = st.tabs(["Segment Images", "Check Data Drift"])

    with tabs[0]:
        segment_images_page()

    with tabs[1]:
        check_data_drift_page()


def main():
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    if st.session_state['authenticated']:
        main_dashboard()
    else:
        login_page()


if __name__ == '__main__':
    main()
