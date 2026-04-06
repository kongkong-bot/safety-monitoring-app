import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QLineEdit,
                             QFrame, QMessageBox, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
import os
from path_utils import ensure_runtime_file
from caidan import ControlPanelMenu
# 找到原来的：from path_utils import resource_path
# 替换为：



# ==========================================
# 1. 这里放入你刚才写好的主界面完整代码
# ==========================================
class SafetyDetectionDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("基于YOLO的高精度安全作业实时检测系统")
        self.resize(1280, 800)
        # 为了演示登录跳转，这里随便放个文字，
        # !!! 请把这里替换为你上一版代码里完整的 initUI() 等全部内容 !!!
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        lbl = QLabel("欢迎来到主监控界面！\n(请将完整的 SafetyDetectionDemo 代码粘贴回这里)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Microsoft YaHei", 24))
        layout.addWidget(lbl)


# ==========================================
# 2. 全新设计的登录页面 (风格与主界面高度一致)
# ==========================================
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统登录 - 安全作业检测系统")
        self.resize(600, 450)  # 登录窗口不需要太大
        self.initUI()

    def initUI(self):
        # 整体背景色 (与主界面一致的浅蓝色)
        self.setStyleSheet("background-color: #E6F0FA;")

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # --- 核心登录框 (带阴影和白底) ---
        login_frame = QFrame()
        login_frame.setFixedSize(450, 320)
        login_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
            }
        """)

        # 添加高级阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        login_frame.setGraphicsEffect(shadow)

        # 登录框内的布局
        frame_layout = QVBoxLayout(login_frame)
        frame_layout.setContentsMargins(40, 30, 40, 30)
        frame_layout.setSpacing(15)

        # 1. 标题
        title_lbl = QLabel("系统登录")
        title_lbl.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title_lbl.setStyleSheet("color: #1E3A8A; background: transparent;")
        title_lbl.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(title_lbl)

        sub_title = QLabel("基于YOLO的高精度安全作业实时检测系统")
        sub_title.setFont(QFont("Microsoft YaHei", 10))
        sub_title.setStyleSheet("color: #607D8B; background: transparent;")
        sub_title.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(sub_title)

        frame_layout.addSpacing(10)

        # 2. 账号输入框
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("请输入管理员账号 (默认: admin)")
        self.setup_input_style(self.user_input)
        frame_layout.addWidget(self.user_input)

        # 3. 密码输入框
        self.pwd_input = QLineEdit()
        self.pwd_input.setPlaceholderText("请输入密码 (默认: 123456)")
        self.pwd_input.setEchoMode(QLineEdit.Password)  # 密码变黑点
        self.setup_input_style(self.pwd_input)
        frame_layout.addWidget(self.pwd_input)

        frame_layout.addSpacing(10)

        # 4. 登录按钮
        self.btn_login = QPushButton("登 入 系 统")
        self.btn_login.setFixedHeight(45)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #9381FF;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #7A68E8;
            }
            QPushButton:pressed {
                background-color: #5E4BCC;
            }
        """)
        self.btn_login.clicked.connect(self.check_login)
        frame_layout.addWidget(self.btn_login)

        main_layout.addWidget(login_frame)

    def setup_input_style(self, line_edit):
        """复用输入框的样式设置"""
        line_edit.setFixedHeight(40)
        line_edit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #90B4CE;
                border-radius: 6px;
                padding: 0 15px;
                font-family: 'Microsoft YaHei';
                font-size: 13px;
                background-color: #F8FBFF;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #9381FF;
                background-color: #FFFFFF;
            }
        """)

    def check_login(self):
        """读取 login.csv 进行真实登录验证"""
        username = self.user_input.text().strip()
        password = self.pwd_input.text().strip()

        # 检查是否输入为空
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入账号和密码！")
            return

        login_success = False
        # 找到原来的：csv_file = resource_path("login.csv")
        # 替换为：
        csv_file = ensure_runtime_file("login.csv")

        # 1. 检查 login.csv 文件是否存在
        if not os.path.exists(csv_file):
            QMessageBox.critical(self, "系统错误", f"找不到配置文件 '{csv_file}'，请将其放置在同级目录下！")
            return

        # 2. 读取并验证文件内容
        try:
            # 使用 utf-8-sig 防止带 BOM 的文件头导致第一个账号读取失败
            with open(csv_file, mode="r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue  # 跳过空行

                    # 因为账号和密码用空格隔开，这里使用 split() 自动按空格或多个空格切分
                    parts = line.split()

                    # 确保这一行正确包含了账号和密码两个部分
                    if len(parts) >= 2:
                        csv_user = parts[0]
                        csv_pwd = parts[1]

                        # 校验输入是否匹配
                        if username == csv_user and password == csv_pwd:
                            login_success = True
                            break  # 验证成功，立即跳出循环

        except Exception as e:
            QMessageBox.critical(self, "系统错误", f"读取账号文件失败：\n{e}")
            return

        # 3. 根据验证结果执行跳转或报错
        if login_success:
            # 登录成功，跳转到导航菜单 (caidan.py 里的 ControlPanelMenu)

            self.main_menu = ControlPanelMenu()
            self.main_menu.show()
            self.close()  # 关闭当前登录窗口
        else:
            # 登录失败，弹出提示框
            QMessageBox.warning(self, "登录失败", "账号或密码错误！")
# ==========================================
# 3. 程序的唯一入口
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())