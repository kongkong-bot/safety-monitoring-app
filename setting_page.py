import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QFrame, QGroupBox,
                             QGridLayout, QComboBox, QSlider, QDoubleSpinBox,
                             QLineEdit, QSizePolicy, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from path_utils import ensure_runtime_file, app_path


class SystemSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统核心设置 - 高精度安全作业实时检测系统")
        self.resize(1280, 800)

        # ================= 核心配置数据结构 =================
        self.config_file = ensure_runtime_file(os.path.join("model", "config.json"))
        self.toggle_updaters = {}  # 存放开关按钮的UI刷新函数

        # 默认配置字典
        self.default_config = {
            "weights_path": "model/best.pt",
            "confidence": 0.25,
            "hardware": "AUTO (自动选择)",
            "rule_hat": True,
            "rule_vest": True,
            "rule_dist": True,
            "dist_threshold": 2.5,
            "alarm_sound": True,
            "log_retention": "30 天",
            "rtsp_url": "rtsp://admin:password@192.168.1.108:554/stream1"
        }
        # 当前活跃配置
        self.current_config = self.default_config.copy()

        self.initUI()

        # 初始化完毕后，自动从本地读取并应用配置
        self.load_config()

    def initUI(self):
        # --- 完美复用统一的 QSS 风格 ---
        self.setStyleSheet("""
            QMainWindow { background-color: #E6F0FA; } 
            QGroupBox { 
                font-weight: bold; border: 2px solid #90B4CE; border-radius: 8px; 
                margin-top: 15px; background-color: #F8FBFF; padding-top: 10px;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #2B4257;
            }
            QPushButton { 
                background-color: #8CA8F9; color: white; border-radius: 5px; 
                padding: 8px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #7293F0; }
            QLabel { font-size: 14px; color: #333333; }

            /* 设置页专属组件美化 */
            QSlider::groove:horizontal {
                border: 1px solid #999; height: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFEB3B, stop:1 #4CAF50); 
                margin: 2px 0; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #1E3A8A; border: 1px solid #5c5c5c;
                width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
            }
            QLineEdit, QComboBox, QDoubleSpinBox {
                border: 1px solid #90B4CE; border-radius: 4px; padding: 5px; background-color: white;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 1. 顶部标题栏与核心操作 ---
        top_layout = QHBoxLayout()
        title_label = QLabel("系统核心功能与模型算法设置")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setStyleSheet("color: #1E3A8A;")
        top_layout.addWidget(title_label)
        top_layout.addStretch()

        # ================= 【新增】：页面跳转按钮 =================
        btn_nav_main = QPushButton("🏠 跳转: 监控主页")
        btn_nav_history = QPushButton("📜 跳转: 历史记录")
        btn_nav_main.setStyleSheet(
            "background-color: #5C6BC0; color: white; padding: 8px; border-radius: 4px; margin-right: 10px;")
        btn_nav_history.setStyleSheet(
            "background-color: #5C6BC0; color: white; padding: 8px; border-radius: 4px; margin-right: 10px;")
        btn_nav_main.clicked.connect(self.jump_to_main)
        btn_nav_history.clicked.connect(self.jump_to_history)

        top_layout.addWidget(btn_nav_main)
        top_layout.addWidget(btn_nav_history)
        # =======================================================

        btn_reset = QPushButton("🔄 恢复默认设置")
        btn_reset.setStyleSheet("background-color: #9381FF; margin-right: 10px;")
        btn_reset.clicked.connect(self.reset_config)
        top_layout.addWidget(btn_reset)

        btn_save = QPushButton("💾 保存并应用设置")
        btn_save.setStyleSheet("background-color: #4CAF50;")
        btn_save.clicked.connect(self.save_config)
        top_layout.addWidget(btn_save)
        main_layout.addLayout(top_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #90B4CE;")
        main_layout.addWidget(line)

        # --- 2. 下方主体：流式卡片布局 ---
        # 【模块 A】AI 推理引擎设置
        group_ai = QGroupBox("AI 推理引擎管理 (YOLOv8/v5)")
        grid_ai = QGridLayout(group_ai)
        grid_ai.setSpacing(15)

        lbl_weights = QLabel("YOLO权重路径 (.pt):")
        self.txt_weights = QLineEdit()
        self.txt_weights.setReadOnly(True)
        btn_browse_w = QPushButton("浏览...")
        btn_browse_w.clicked.connect(self.browse_weights)
        grid_ai.addWidget(lbl_weights, 0, 0)
        grid_ai.addWidget(self.txt_weights, 0, 1)
        grid_ai.addWidget(btn_browse_w, 0, 2)

        lbl_conf = QLabel("置信度阈值 (Confidence):")
        self.lbl_conf_val = QLabel("0.25")
        self.slider_conf = QSlider(Qt.Horizontal)
        self.slider_conf.setRange(0, 100)
        self.slider_conf.valueChanged.connect(lambda v: self.lbl_conf_val.setText(f"{v / 100.0:.2f}"))
        grid_ai.addWidget(lbl_conf, 1, 0)
        grid_ai.addWidget(self.slider_conf, 1, 1)
        grid_ai.addWidget(self.lbl_conf_val, 1, 2)

        lbl_hw = QLabel("硬件推理调度 (Inference Device):")
        self.combo_hw = QComboBox()
        self.combo_hw.addItems(["AUTO (自动选择)", "GPU 0 (NVIDIA RTX 3060)", "CPU (Intel Core i7)"])
        grid_ai.addWidget(lbl_hw, 2, 0)
        grid_ai.addWidget(self.combo_hw, 2, 1, 1, 2)

        main_layout.addWidget(group_ai)

        # 【模块 B】安全检测规则设置
        group_rules = QGroupBox("安全检测规则设置")
        grid_rules = QGridLayout(group_rules)
        grid_rules.setSpacing(15)

        self.create_toggle_rule(grid_rules, "安全帽佩戴检测", 0, "rule_hat")
        self.create_toggle_rule(grid_rules, "防护服穿戴检测", 1, "rule_vest")
        self.create_toggle_rule(grid_rules, "人机测距报警", 2, "rule_dist")

        lbl_dist = QLabel("核心安全距离阈值 (米):")
        self.spin_dist = QDoubleSpinBox()
        self.spin_dist.setRange(0.5, 10.0)
        self.spin_dist.setSingleStep(0.1)
        grid_rules.addWidget(lbl_dist, 3, 0)
        grid_rules.addWidget(self.spin_dist, 3, 1)
        grid_rules.addWidget(QLabel("(超过此距离触发警报)"), 3, 2)

        main_layout.addWidget(group_rules)

        # 【模块 C】警报与数据存储设置
        group_storage = QGroupBox("警报与数据存储设置")
        grid_storage = QGridLayout(group_storage)
        grid_storage.setSpacing(15)

        self.create_toggle_rule(grid_storage, "声音报警开关", 0, "alarm_sound")

        lbl_log_retention = QLabel("违规日志保留期限:")
        self.combo_log = QComboBox()
        self.combo_log.addItems(["30 天", "90 天", "180 天", "永久保留"])
        grid_storage.addWidget(lbl_log_retention, 1, 0)
        grid_storage.addWidget(self.combo_log, 1, 1, 1, 2)

        main_layout.addWidget(group_storage)

        # 【模块 D】输入源管理
        group_src = QGroupBox("系统数据源管理")
        grid_src = QGridLayout(group_src)
        lbl_src = QLabel("默认网络监控流 URL:")
        self.txt_src = QLineEdit()
        btn_src_t = QPushButton("连接测试")
        btn_src_t.clicked.connect(lambda: QMessageBox.information(self, "网络测试", "模拟测试成功！流媒体就绪。"))
        grid_src.addWidget(lbl_src, 0, 0)
        grid_src.addWidget(self.txt_src, 0, 1)
        grid_src.addWidget(btn_src_t, 0, 2)
        main_layout.addWidget(group_src)

        main_layout.addStretch()

    # ================= UI 生成与状态管理 =================
    def create_toggle_rule(self, layout, title, row, config_key):
        """生成带状态记忆的 ON/OFF 按钮对"""
        layout.addWidget(QLabel(title), row, 0)
        btn_on = QPushButton("开启 (ON)")
        btn_off = QPushButton("关闭 (OFF)")

        # 内部状态切换函数
        def set_state(is_on):
            self.current_config[config_key] = is_on
            if is_on:
                btn_on.setStyleSheet("background-color: #4CAF50; color: white;")
                btn_off.setStyleSheet("background-color: #E0E0E0; color: #777;")
            else:
                btn_on.setStyleSheet("background-color: #E0E0E0; color: #777;")
                btn_off.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")

        # 绑定点击事件
        btn_on.clicked.connect(lambda: set_state(True))
        btn_off.clicked.connect(lambda: set_state(False))

        hbox = QHBoxLayout()
        hbox.addWidget(btn_on)
        hbox.addWidget(btn_off)
        layout.addLayout(hbox, row, 1)
        layout.addWidget(QLabel("(默认开启)"), row, 2)

        # 把状态刷新函数存起来，供读取配置时调用
        self.toggle_updaters[config_key] = set_state

    def browse_weights(self):
        """选择权重文件"""
        # 替换这里的相对路径 'model' 为绝对的安全路径
        target_dir = app_path("model")
        os.makedirs(target_dir, exist_ok=True)
        fname, _ = QFileDialog.getOpenFileName(self, '选择 YOLO 权重文件', target_dir, 'Weights (*.pt)')
        if fname:
            self.txt_weights.setText(fname)

    # ================= 核心：配置读写逻辑 =================
    def load_config(self):
        """从 JSON 读取配置并渲染到 UI"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 更新当前配置字典
                    self.current_config.update(loaded_config)
            except Exception as e:
                print(f"配置文件读取失败: {e}")

        # 渲染到 UI 组件
        self.txt_weights.setText(self.current_config["weights_path"])

        conf_val = self.current_config["confidence"]
        self.slider_conf.setValue(int(conf_val * 100))
        self.lbl_conf_val.setText(f"{conf_val:.2f}")

        self.combo_hw.setCurrentText(self.current_config["hardware"])
        self.combo_log.setCurrentText(self.current_config["log_retention"])
        self.spin_dist.setValue(self.current_config["dist_threshold"])
        self.txt_src.setText(self.current_config["rtsp_url"])

        # 渲染开关按钮状态
        for key, updater in self.toggle_updaters.items():
            updater(self.current_config[key])

    def save_config(self):
        """收集 UI 数据并保存到 JSON"""
        # 从常规控件收集数据
        self.current_config["weights_path"] = self.txt_weights.text()
        self.current_config["confidence"] = self.slider_conf.value() / 100.0
        self.current_config["hardware"] = self.combo_hw.currentText()
        self.current_config["dist_threshold"] = self.spin_dist.value()
        self.current_config["log_retention"] = self.combo_log.currentText()
        self.current_config["rtsp_url"] = self.txt_src.text()

        # 写入 JSON 文件
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_config, f, indent=4, ensure_ascii=False)

            QMessageBox.information(self, "保存成功", "✅ 系统设置已保存并应用！\n(部分设置可能需要重启推理核心生效)")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"配置文件写入失败：\n{e}")

    def reset_config(self):
        """恢复默认配置"""
        reply = QMessageBox.question(self, '确认重置', '确定要将所有设置恢复为出厂默认值吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.current_config = self.default_config.copy()
            self.load_config()
            self.save_config()

            # ================= 【新增】：页面跳转核心逻辑 =================

    def jump_to_main(self):
        from main_page import SafetyDetectionDemo
        self.win_main = SafetyDetectionDemo()
        self.win_main.show()
        self.hide()

    def jump_to_history(self):
        from history_read import AlarmHistoryWindow
        self.win_history = AlarmHistoryWindow()
        self.win_history.show()
        self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SystemSettingsWindow()
    window.show()
    sys.exit(app.exec_())