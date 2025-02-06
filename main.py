import sys
import json
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QTextEdit, QPushButton,
    QDoubleSpinBox, QSpinBox, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings


class ApiThread(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key, model, messages, parameters):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.messages = messages
        self.parameters = parameters

    def run(self):
        try:
            #headers是HTTP请求的头部信息
            headers = {
                "Authorization": f"Bearer {self.api_key}",                  #Authorization：用于身份验证，格式为Bearer <API密钥>。
                "Content-Type": "application/json"                          #Content-Type：指定请求体的格式为JSON。
            }
            #data是发送给API的请求体，包含以下内容：
            data = {
                "model": self.model,                                        #model：指定使用的模型（如deepseek - chat或deepseek - r1）。
                "messages": self.messages,                                  #messages：对话历史记录，格式为列表，包含用户和助手的消息。
                **self.parameters                                           #self.parameters：展开self.parameters字典，包含其他可调参数（如temperature、top_p等）。
            }
            #使用requests.post方法向DeepSeekAPI发送POST请求。
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",         #API的URL。
                headers=headers,                                            #headers：包含认证和内容类型的请求头。
                json=data,                                                  #json = data：将data字典转换为JSON格式并作为请求体发送。
                timeout=30                                                  #timeout = 30：设置请求超时时间为30秒，如果超过30秒未收到响应，会抛出超时异常。
            )

            if response.status_code == 200:                                 #检查HTTP响应的状态码。200表示请求成功，API返回了有效数据。
                result = response.json()                                    #将API返回的JSON格式的响应内容解析为Python字典。

                if 'choices' in result and len(result['choices']) > 0:      #检查响应中是否包含choices字段，并且choices列表不为空。
                    content = result['choices'][0]['message']['content']    #提取第一个choice中的message的content字段，即DeepSeek的回复内容。
                    self.response_received.emit(content)                    #使用self.response_received.emit(content)将回复内容通过信号发送到主线程，以便更新UI。
                else:
                    self.error_occurred.emit("无效的API响应格式")              #如果响应中没有choices字段或choices为空，表示API返回的数据格式不符合预期。

            else:                                                           #如果状态码不是200，表示API请求失败。使用self.error_occurred.emit发送错误信号，包含状态码和错误信息。
                self.error_occurred.emit(f"API错误: {response.status_code} - {response.text}")

        except Exception as e:                                              #如果在try块中发生任何异常（如网络错误、超时、JSON解析错误等），程序会跳转到except块。
            self.error_occurred.emit(f"请求失败: {str(e)}")


class DeepSeekChat(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("DeepSeek", "ChatClient")
        self.init_ui()
        self.load_settings()
        self.history = []

    def init_ui(self):
        self.setWindowTitle("DeepSeek API简易接入程序（达莉娅制）")
        self.setMinimumSize(1280, 720)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # API设置区域
        api_group = QGroupBox("API设置")
        api_layout = QHBoxLayout()
        self.api_combo = QComboBox()
        self.api_combo.setEditable(True)
        self.api_combo.setMinimumWidth(300)
        api_layout.addWidget(QLabel("API密钥:"))
        api_layout.addWidget(self.api_combo)
        api_group.setLayout(api_layout)
        main_layout.addWidget(api_group)

        # 参数设置区域
        params_group = QGroupBox("模型参数")
        params_layout = QHBoxLayout()

        # 模型选择
        self.model_combo = QComboBox()
        self.model_combo.addItems(["deepseek-chat", "deepseek-reasoner"])
        params_layout.addWidget(QLabel("模型:"))
        params_layout.addWidget(self.model_combo)

        # 温度参数
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(0.7)
        params_layout.addWidget(QLabel("温度:"))
        params_layout.addWidget(self.temperature)

        # Top P参数
        self.top_p = QDoubleSpinBox()
        self.top_p.setRange(0.0, 1.0)
        self.top_p.setSingleStep(0.1)
        self.top_p.setValue(1.0)
        params_layout.addWidget(QLabel("Top P:"))
        params_layout.addWidget(self.top_p)

        # 最大令牌数
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(1, 4096)
        self.max_tokens.setValue(1024)
        params_layout.addWidget(QLabel("最大长度:"))
        params_layout.addWidget(self.max_tokens)

        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)

        # 对话区域
        chat_widget = QWidget()
        chat_layout = QHBoxLayout(chat_widget)

        # 输入区域
        input_group = QGroupBox("输入")
        input_layout = QVBoxLayout()
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("输入您的问题...")
        input_layout.addWidget(self.input_text)
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        input_group.setLayout(input_layout)
        chat_layout.addWidget(input_group, 1)

        # 输出区域
        output_group = QGroupBox("回复")
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        chat_layout.addWidget(output_group, 1)

        main_layout.addWidget(chat_widget, 1)

        # 状态栏
        self.statusBar().showMessage("就绪")

    #加载用户之前保存的API密钥历史记录。
    def load_settings(self):                                                    #加载用户之前保存的API密钥历史记录
        api_history = self.settings.value("api_history", [])                    #从程序的设置中读取键为"api_history"的值。如果该键不存在，则返回一个空列表[]作为默认值。
        self.api_combo.addItems(api_history)                                    #将加载的API密钥历史记录添加到下拉框（QComboBox）中。
        if api_history:
            self.api_combo.setCurrentIndex(0)                                   #如果有，则将下拉框的当前选项设置为第一个历史记录（setCurrentIndex(0)）。
    #保存当前的API密钥历史记录。
    def save_settings(self):                                                    #保存当前的API密钥历史记录。
        api_history = [self.api_combo.itemText(i) for i in range(self.api_combo.count())]
        self.settings.setValue("api_history", api_history)                      #将当前的API密钥列表保存到程序的设置中，键为"api_history"。

    #发送用户输入的消息到DeepSeek API。
    def send_message(self):
        api_key = self.api_combo.currentText().strip()                          #获取下拉框中当前选中的API密钥，并去除首尾空白字符。
        if not api_key:
            QMessageBox.warning(self, "警告", "请输入有效的API密钥")                #如果为空，弹出警告对话框（QMessageBox.warning），提示用户输入有效的API密钥，并退出方法。
            return

        #检查用户输入的消息内容。
        message = self.input_text.toPlainText().strip()                         #获取用户输入的消息内容，并去除首尾空白字符。
        if not message:
            QMessageBox.warning(self, "警告", "请输入消息内容")                     #如果为空，弹出警告对话框，提示用户输入消息内容，并退出方法。
            return

        # 保存当前API密钥到历史记录
        if api_key not in [self.api_combo.itemText(i) for i in range(self.api_combo.count())]:
            self.api_combo.addItem(api_key)
        self.save_settings()                                                    #调用save_settings方法，保存当前的API密钥历史记录。

        # 准备对话参数,parameters是一个字典，包含以下参数：
        parameters = {
            "temperature": self.temperature.value(),                            #temperature：从温度调节控件（QDoubleSpinBox）中获取的值。
            "top_p": self.top_p.value(),                                        #top_p：从TopP控件（QDoubleSpinBox）中获取的值。
            "max_tokens": self.max_tokens.value(),                              #max_tokens：从最大长度控件（QSpinBox）中获取的值。
        }

        # 创建对话历史
        self.history.append({"role": "user", "content": message})
        if len(self.history) > 10:  # 限制历史记录长度
            self.history = self.history[-10:]

        # 禁用发送按钮
        self.send_btn.setEnabled(False)
        self.statusBar().showMessage("正在请求...")

        # 创建并启动工作线程
        self.thread = ApiThread(
            api_key=api_key,
            model=self.model_combo.currentText(),
            messages=self.history,
            parameters=parameters
        )
        self.thread.response_received.connect(self.handle_response)         #将线程的response_received信号连接到handle_response方法，用于处理API的响应。
        self.thread.error_occurred.connect(self.handle_error)               #将线程的error_occurred信号连接到handle_error方法，用于处理错误。
        self.thread.start()                                                 #启动线程，开始发送请求。

    def handle_response(self, response):
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("请求完成", 2000)
        #self.output_text.append(f"你: {self.history[-1]['content']}")
        self.output_text.append(f"DeepSeek: {response}\n")
        self.history.append({"role": "assistant", "content": response})
        self.input_text.clear()

    def handle_error(self, error):
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("请求失败", 2000)
        self.output_text.append(f"错误: {error}\n")
        QMessageBox.critical(self, "错误", error)

    def closeEvent(self, event):
        self.save_settings()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeepSeekChat()
    window.show()
    sys.exit(app.exec_())