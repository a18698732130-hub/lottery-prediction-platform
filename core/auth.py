import hashlib
import streamlit as st
from core.db import Database

class AuthManager:
    def __init__(self):
        self.db = Database()

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username, password):
        if not username or not password:
            return False, "用户名和密码不能为空"
        
        hashed = self._hash_password(password)
        if self.db.create_user(username, hashed):
            return True, "注册成功，请登录"
        else:
            return False, "用户名已存在"

    def login(self, username, password):
        user = self.db.get_user(username)
        if user:
            hashed = self._hash_password(password)
            if user['password_hash'] == hashed:
                return True, "登录成功"
        return False, "用户名或密码错误"

    def login_form(self):
        st.title("彩票分析平台 - 用户登录")
        
        tab1, tab2 = st.tabs(["登录", "注册"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("用户名", key="login_user")
                password = st.text_input("密码", type="password", key="login_pass")
                submit = st.form_submit_button("登录")
                
                if submit:
                    success, msg = self.login(username, password)
                    if success:
                        st.session_state['user'] = username
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        
        with tab2:
            with st.form("register_form"):
                new_user = st.text_input("新用户名", key="reg_user")
                new_pass = st.text_input("设置密码", type="password", key="reg_pass")
                confirm_pass = st.text_input("确认密码", type="password", key="reg_pass_2")
                submit_reg = st.form_submit_button("注册")
                
                if submit_reg:
                    if new_pass != confirm_pass:
                        st.error("两次密码输入不一致")
                    else:
                        success, msg = self.register(new_user, new_pass)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
