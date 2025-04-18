from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivy.uix.widget import Widget
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.list import MDList, OneLineAvatarIconListItem
from kivymd.uix.scrollview import MDScrollView
from kivy.properties import ObjectProperty, StringProperty
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

import sys
import bcrypt
import requests
import json
import base64
import os
import re
import time

SERVER_URL = "https://hobbies.yoonjin2.kr:32000"
cert_path = ""

class CryptoHelper:
    @staticmethod
    def pad(s):
        return s + (AES.block_size - len(s) % AES.block_size) * chr(AES.block_size - len(s) % AES.block_size)

    @staticmethod
    def unpad(s):
        return s[:-ord(s[len(s) - 1:])]

    @staticmethod
    def encrypt(text, key):
        key = base64.b64decode(key)
        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_text = cipher.encrypt(CryptoHelper.pad(text).encode())
        return base64.b64encode(encrypted_text).decode(), base64.b64encode(iv).decode()

    @staticmethod
    def decrypt(encrypted_text, key, iv):
        key = base64.b64decode(key)
        iv = base64.b64decode(iv)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return CryptoHelper.unpad(cipher.decrypt(base64.b64decode(encrypted_text)).decode())

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8), size_hint=(1, 1), adaptive_height=True)
        self.layout = layout
        central_layout = MDBoxLayout(orientation='vertical', size_hint=(None, None), width=min(dp(320), Window.width * 0.8), pos_hint={'center_x': 0.5}, spacing=dp(20))
        central_layout.bind(minimum_height=central_layout.setter('height'))

        title_label = MDLabel(text="Linux Container Manager", halign='center', theme_text_color="Primary", font_style="H6")
        central_layout.add_widget(title_label)

        self.username_input = MDTextField(hint_text="Username", size_hint_x=None, width=central_layout.width)
        self.password_input = MDTextField(hint_text="Password", password=True, size_hint_x=None, width=central_layout.width)
        self.container_name            = MDTextField(hint_text="Container Label", size_hint_x=None, width=central_layout.width)
        self.container_tag             = MDTextField(hint_text="Container Tag"  , size_hint_x=None, width=central_layout.width)
        self.distro                    = MDTextField(hint_text="distro:version", size_hint_x=None, width=central_layout.width)
        central_layout.add_widget(self.username_input)
        central_layout.add_widget(self.password_input)
        central_layout.add_widget(self.distro)
        central_layout.add_widget(self.container_tag)

        buttons_container = MDBoxLayout(orientation='vertical', spacing=dp(15), size_hint_y=None, pos_hint={'center_x': 0.5}, adaptive_size = True)
        self.create_container_button = MDRaisedButton(text="Create Container", on_release=self.create_container, size_hint_x=None)
        self.register_button = MDRaisedButton(text="Register", on_release=self.register_user, size_hint_x=None)
        self.manage_button = MDRaisedButton(text="Manage Containers", on_release=self.go_to_manage, size_hint_x=None)

        buttons_container.add_widget(self.create_container_button)
        buttons_container.add_widget(self.register_button)
        buttons_container.add_widget(self.manage_button)

        central_layout.add_widget(Widget(size_hint_y=1))
        central_layout.add_widget(buttons_container)

        layout.add_widget(central_layout)

        self.result_label = MDLabel(text="", theme_text_color="Secondary", halign='center', font_style="Caption")
        layout.add_widget(self.result_label)

        self.add_widget(layout)
        self.container_info = {}

    def go_to_manage(self, instance):
        if not self.username_input.text or not self.password_input.text:
            self.result_label.text = "Please enter username and password before managing."
            return
        self.send_user_info()
        self.manager.current = "manage"

    def register_user(self, instance):
        if not self.username_input.text or not self.password_input.text:
            self.result_label.text = "Please enter username and password to register."
            return
        self.send_user_info()
        self.send_request("register")

    def create_container(self, instance):
        if not self.username_input.text or not self.password_input.text:
            self.result_label.text = "Please enter username and password to create a container."
            return
        if not hasattr(self.manager, 'user_info') or 'username' not in self.manager.user_info or 'key' not in self.manager.user_info or 'username_iv' not in self.manager.user_info:
            self.result_label.text = "User information not available. Please register or log in again."
            return
        self.send_request("create")

    def send_user_info(self):
        username = self.username_input.text
        password = self.password_input.text
        key = base64.b64encode(get_random_bytes(32)).decode()

        encrypted_username, iv_username = CryptoHelper.encrypt(username, key)
        password_bytes = password.encode('utf-8')
        hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8') # Decode to string

        data = {
            "username": encrypted_username,
            "username_iv": iv_username,
            "password": hashed_password,
            "key": key,
        }
        self.manager.user_info = data
        self.send_request("request")
        manage_screen = self.manager.get_screen("manage")
        manage_screen.update_container_list(self.containers)


    def send_request(self, endpoint):
        headers = {'Content-Type': 'application/json'}
    
        # Variable for the response
        response = None
    
        if endpoint == "register":
            data = self.manager.user_info
            response = requests.post(f"{SERVER_URL}/{endpoint}", headers=headers, json=data, verify=cert_path)
    
        elif endpoint == "create":
            if not hasattr(self.manager, 'user_info'):
                self.result_label.text = "User information not found. Please register first."
                return
    
            password = self.password_input.text
            key = self.manager.user_info['key']
            encrypted_password, password_iv = CryptoHelper.encrypt(password, key)
            distroinfo = ""
            if re.match(r'[a-z0-9:.]+$:', self.distro.text):
                distroinfo = self.distro.text
            else:
                distroinfo = ''.join(filter(lambda x: re.match(r'[a-z0-9:.]', x),self.distro.text)) 
            distro_and_version = distroinfo.split(":")
            self.distro.text = distroinfo
            if len(distro_and_version) < 2:
                return
            distro = distro_and_version[0]
            version = distro_and_version[1]
            modifiedformoftag = ""
            if re.match(r'[a-zA-Z0-9-]+$', self.container_tag.text):
                modifiedformoftag = self.container_tag.text
            else:
                for char in self.container_tag.text:
                    if re.match(r'[a-zA-Z0-9-]+$', char):
                        modifiedformoftag += char
                    else:
                        modifiedformoftag += "."
            self.container_tag.text = modifiedformoftag
            data = {
                "username": self.manager.user_info['username'],
                "username_iv": self.manager.user_info['username_iv'],
                "password": encrypted_password,
                "password_iv": password_iv,
                "key": self.manager.user_info['key'],
                "tag": modifiedformoftag,
                "distro": distro,
                "version": version
            } 
            response = requests.post(f"{SERVER_URL}/{endpoint}", headers=headers, json=data, verify=cert_path)
    
        else:
            if not hasattr(self.manager, 'user_info'):
                self.result_label.text = "User information not found. Please register first."
                return
    
            # For action endpoints like start, stop, restart, pause, delete, etc.
            if endpoint in ["start", "stop", "restart", "pause", "delete", "resume"]:
                if not hasattr(self, 'current_selected_tag') or not self.current_selected_tag:
                    self.result_label.text = "No container selected. Please select a container first."
                    return
    
                # Send only the raw tag as the request body
                response = requests.post(f"{SERVER_URL}/{endpoint}", data=self.current_selected_tag, verify=cert_path)
            else:
                # For request or other actions that don't require container_tag
                data = {
                    "username": self.manager.user_info['username'],
                    "username_iv": self.manager.user_info['username_iv'],
                    "key": self.manager.user_info['key'],
                }
                response = requests.post(f"{SERVER_URL}/{endpoint}", headers=headers, json=data, verify=cert_path)
    
        # Ensure the response is not None before proceeding
        if response is not None:
            try:
                response.raise_for_status()  # Will raise an exception if the HTTP request failed
    
                # For 'request' endpoint, handle container list response
                if endpoint == "request":
                    try:
                        self.containers = json.loads(response.text)
                        if self.manager.current == "manage":
                            manage_screen = self.manager.get_screen("manage")
                            manage_screen.update_container_list(self.containers)
                            
                    except json.JSONDecodeError:
                        if self.manager.current == "manage":
                            manage_screen = self.manager.get_screen("manage")
                            manage_screen.container_list.clear_widgets()
                            manage_screen.container_list.add_widget(MDLabel(text="Failed to decode container list", theme_text_color="Error", halign='center'))
    
                self.result_label.text = ""
            except requests.exceptions.RequestException as e:
                self.result_label.text = f"Error: {e}"
    
        else:
            # Handle the case where the response is None
            self.result_label.text = "No response from server."

class ContainerListItem(MDBoxLayout):
    tag = StringProperty()
    actualTag = StringProperty()
    port = StringProperty()
    status = StringProperty()
    distro = StringProperty()
    version = StringProperty()
    checkbox_active = ObjectProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.padding = dp(8)
        self.spacing = dp(8)
        self.size_hint_y = None
        self.height = dp(70)

        self._checkbox = MDCheckbox(on_release=self.on_checkbox_toggle)
        self.add_widget(self._checkbox)

        self.text_container = MDBoxLayout(orientation='vertical', adaptive_height=True, size_hint_x=1)
        self.tag_label = MDLabel(text=f"{self.tag}", halign='left', adaptive_height=True, theme_text_color='Primary')
        self.distro_label = MDLabel(text=f"{self.distro}:{self.version}", halign='left', adaptive_height=True, theme_text_color='Primary')
        self.port_status_label = MDLabel(text=f"Port: {self.port}, Status: {self.status.capitalize()}", halign='left', adaptive_height=True, theme_text_color='Secondary')
        self.text_container.add_widget(self.tag_label)
        self.text_container.add_widget(self.port_status_label)
        self.add_widget(self.text_container)

    def on_tag(self, instance, value):
        if hasattr(self, 'tag_label'): 
            self.tag_label.text = f"Tag: {value}"

    def on_port(self, instance, value):
        if hasattr(self, 'port_status_label'): 
            self.port_status_label.text = f"Port: {value}, Status: {self.status.capitalize()}"

    def on_status(self, instance, value):
        if hasattr(self, 'port_status_label'): 
            self.port_status_label.text = f"Port: {self.port}, Status: {value.capitalize()}"

    def on_checkbox_toggle(self, checkbox):
        self.checkbox_active = checkbox.active

class ManageScreen(Screen):
    container_list = ObjectProperty(None)
    feedback_label = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = MDBoxLayout(orientation='vertical', padding=dp(8), spacing=dp(4), size_hint=(1, 1)) 

        title_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, padding=(dp(4), 0)) 
        title_label = MDLabel(text="Container Management", halign='center', theme_text_color="Primary", font_style="H6")
        title_layout.add_widget(title_label)
        self.layout.add_widget(title_layout)


        self.scroll = MDScrollView()
        self.container_list = MDList(spacing=dp(24), padding=dp(24), size_hint_y=None) 
        self.container_list.bind(minimum_height=self.container_list.setter('height'))
        self.scroll.add_widget(self.container_list)
        self.layout.add_widget(self.scroll)

        button_layout_bottom = MDBoxLayout(orientation='horizontal', spacing=dp(16), size_hint_y=0.1, padding=(dp(8), 0)) 
        button_layout_bottom_second_line = MDBoxLayout(orientation='horizontal', spacing=dp(16), size_hint_y=0.1, padding=(dp(8), 0)) 
        button_layout_bottom_third_line = MDBoxLayout(orientation='horizontal', spacing=dp(16), size_hint_y=0.1, padding=(dp(8), 0)) 
        self.start_button = MDRaisedButton(text="Start", on_release=lambda x: self.manage_container("start"), size_hint_x=0.2)
        self.stop_button = MDRaisedButton(text="Stop", on_release=lambda x: self.manage_container("stop"), size_hint_x=0.2)
        self.pause_button = MDRaisedButton(text="Pause", on_release=lambda x: self.manage_container("pause"), size_hint_x=0.2)
        self.resume_button = MDRaisedButton(text="Resume", on_release=lambda x: self.manage_container("resume"), size_hint_x=0.2)
        self.restart_button = MDRaisedButton(text="Restart", on_release=lambda x: self.manage_container("restart"), size_hint_x=0.2)
        self.delete_button = MDRaisedButton(text="Delete", on_release=lambda x: self.manage_container("delete"), size_hint_x=0.2)
        self.refresh_button = MDRaisedButton(text="Refresh", on_release=self.list_containers_and_display_json, size_hint_x=0.5)
        self.go_back_button = MDRaisedButton(text="Back", on_release=lambda x: setattr(self.manager, "current", "main"), size_hint_x=0.5)
        button_layout_bottom.add_widget(self.start_button)
        button_layout_bottom.add_widget(self.stop_button)
        button_layout_bottom.add_widget(self.delete_button)
        button_layout_bottom_second_line.add_widget(self.pause_button)
        button_layout_bottom_second_line.add_widget(self.restart_button)
        button_layout_bottom_third_line.add_widget(self.resume_button)
        button_layout_bottom_third_line.add_widget(self.refresh_button)
        button_layout_bottom_third_line.add_widget(self.go_back_button)
        self.layout.add_widget(button_layout_bottom)
        self.layout.add_widget(button_layout_bottom_second_line)
        self.layout.add_widget(button_layout_bottom_third_line)

        self.feedback_label = MDLabel(text="", theme_text_color="Secondary", halign='center', font_style="Caption", size_hint_y=None, padding=(0, dp(5))) # feedback label padding 줄임
        self.layout.add_widget(self.feedback_label)

        self.add_widget(self.layout)
        self.selected_containers = {}

    def list_containers_and_display_json(self, instance):
        if not hasattr(self.manager, 'user_info'):
            self.feedback_label.text = "User information not found. Please log in again."
            return

    def update_container_list(self, containers):
        self.container_list.clear_widgets()
        self.selected_containers = {}
        placeholder = MDLabel(
        text="Container List",
        halign='center',
        theme_text_color="Hint",
        size_hint_y=None,
        height=dp(40),
        )
        self.container_list.add_widget(placeholder)
        for container in containers:
            tmp = container['tag']
            tag_split = tmp.split("-")
            tag_split = tag_split[:-1]
            containerLabel = ""
            for itm in tag_split:
                containerLabel += itm
                containerLabel += '-'
            containerLabel = containerLabel[:-1]
            print(containerLabel)
            item = ContainerListItem(tag=containerLabel, port=container['serverport'], distro=container['distro'], version=container['version'],  status=container['vmstatus'], actualTag = tmp)
            self.container_list.add_widget(item)
            self.selected_containers[container['tag']] = item

    def manage_container(self, action):
        selected_items = [item for item in self.container_list.children if isinstance(item, ContainerListItem) and item.checkbox_active]
        if not selected_items:
            self.feedback_label.text = "Please select at least one container."
            return

        main_screen = self.manager.get_screen("main")
        for item in selected_items:
            main_screen.current_selected_tag = item.actualTag
            self.manager.get_screen("main").send_request(action)
            main_screen.current_selected_tag = None # Reset selection after action
            self.list_containers_and_display_json(None)
            self.manager.get_screen("main").send_request("request")
            main_screen = self.manager.get_screen("main")
            prev_list = current_list = main_screen.containers
            manage_screen = self.manager.get_screen("manage")

            start = time.time()
            while prev_list == current_list:
                self.manager.get_screen("main").send_request("request")
                current_list = self.manager.get_screen("main").containers
                end = time.time()
                if end-start > 1:
                    break
            manage_screen.update_container_list(current_list)

class ContainerApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"
        sm = ScreenManager()
        sm.user_info = {}
        main_screen = MainScreen(name="main")
        sm.add_widget(main_screen)
        sm.add_widget(ManageScreen(name="manage"))
        return sm

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):  # For actual apk
        from kivy.utils import platform
        if platform == 'android':
            from android.storage import app_storage_path
            basedir = '/data/data/org.yoonjin67.lvirtfront/files/app/certs'
        else:
            import os
            basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certs')
    else:
        cert_path = './certs/ca.crt'  # for development or pc
    ContainerApp().run()
