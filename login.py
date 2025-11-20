import streamlit as st
import hashlib

# ------------------------------
# PASSWORD HASHING FUNCTION
# ------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------------------
# USER DATABASE (hashed passwords)
# ------------------------------
USERS = {
    "admin": hash_password("admin123"),   # change password
    "shree": hash_password("shree@123"),  # change password
}

# ------------------------------
# LOGIN CHECK
# ------------------------------
def check_login(username, password):
    if username in USERS:
        return USERS[username] == hash_password(password)
    return False

# ------------------------------
# LOGIN SCREEN
# ------------------------------
def login_screen():
    st.title("🔐 Algo Dashboard Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if check_login(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success("Login successful! Loading dashboard...")
                st.rerun()
            else:
                st.error("Invalid username or password")
