import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# ==================== 1. 导入你写好的其他页面模块 ====================
# 【关键修改】：这里将直接调用你同一目录下的其他 py 文件中的主类
from main_page import SafetyDetectionDemo
from history_read import AlarmHistoryWindow
from setting_page import SystemSettingsWindow

# ==================== 全局样式表和配色 ====================
GLOBAL_STYLE = """
* {
    color: #ffffff;
    background-color: #1a233a; 
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
}

QGroupBox {
    border: 1px solid #4a5d8f; 
    border-radius: 5px;
    margin-top: 15px;
    font-weight: bold;
    font-size: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 10px;
    color: #92bdfa; 
}

QPushButton {
    color: #ffffff;
    background-color: #517ef7; 
    border-radius: 5px;
    padding: 15px; 
    font-weight: bold;
    font-size: 16px;
    margin-bottom: 5px;
}

QPushButton:hover { background-color: #6b8ffd; }
QPushButton:pressed { background-color: #3b5cbd; }

QLabel#statusLabel { color: #8898aa; font-size: 12px; }
"""

# ==================== 2. 纯控制面板导航菜单 ====================
class ControlPanelMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("安全作业检测导航控制台")
        self.resize(380, 500)
        self.setStyleSheet(GLOBAL_STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title_label = QLabel("高精度安全作业实时检测系统")
        title_font = QFont('Microsoft YaHei', 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #ffffff; background: transparent;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        main_layout.addSpacing(10)

        nav_group = QGroupBox("系统控制模块")
        nav_layout = QVBoxLayout(nav_group)
        nav_layout.setSpacing(15)
        nav_layout.setContentsMargins(15, 30, 15, 20)

        self.btn_main = QPushButton("▶ 打开实时监控主页")
        self.btn_history = QPushButton("≡ 查看违规历史记录")
        self.btn_setting = QPushButton("⚙ 进入系统参数设置")

        self.btn_main.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_history.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_setting.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        nav_layout.addWidget(self.btn_main)
        nav_layout.addWidget(self.btn_history)
        nav_layout.addWidget(self.btn_setting)

        main_layout.addWidget(nav_group)
        main_layout.addStretch()

        status_layout = QVBoxLayout()
        status_label1 = QLabel("● 系统核心：就绪")
        status_label1.setObjectName("statusLabel")
        status_label2 = QLabel("● 硬件加速：已检测 (RTX系列)")
        status_label2.setObjectName("statusLabel")

        status_layout.addWidget(status_label1)
        status_layout.addWidget(status_label2)
        main_layout.addLayout(status_layout)

        # 绑定点击事件
        self.btn_main.clicked.connect(self.open_main)
        self.btn_history.clicked.connect(self.open_history)
        self.btn_setting.clicked.connect(self.open_setting)

    # ==================== 3. 弹出真实窗口的核心逻辑 ====================
    def open_main(self):
        # 【关键修改】：这里调用的已经是 main_page.py 里的 SafetyDetectionDemo 了
        self.page_main = SafetyDetectionDemo()
        self.page_main.show()

    def open_history(self):
        # 调用 history_read.py 里的 AlarmHistoryWindow
        self.page_history = AlarmHistoryWindow()
        self.page_history.show()

    def open_setting(self):
        # 调用 setting_page.py 里的 SystemSettingsWindow
        self.page_setting = SystemSettingsWindow()
        self.page_setting.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    panel = ControlPanelMenu()
    panel.show()
    sys.exit(app.exec_())