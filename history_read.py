import sys
import os
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QGroupBox, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QComboBox, QDateEdit)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QPixmap, QColor
from path_utils import app_path


class AlarmHistoryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("历史检测记录库 - 高精度安全作业实时检测系统")
        self.resize(1280, 800)
        self.initUI()

        # 启动时自动加载一次数据
        self.load_csv_data()

    def initUI(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #E6F0FA; } 
            QGroupBox { 
                font-weight: bold; border: 2px solid #90B4CE; border-radius: 8px; 
                margin-top: 15px; background-color: #F8FBFF;
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
            QTableWidget {
                background-color: #FFFFFF; border: 1px solid #90B4CE; border-radius: 5px;
                gridline-color: #E0E0E0; selection-background-color: #D0E4F5;
                selection-color: #1E3A8A; font-size: 13px;
            }
            QHeaderView::section {
                background-color: #9381FF; color: white; font-weight: bold;
                border: none; padding: 5px;
            }
            QComboBox, QDateEdit {
                border: 1px solid #90B4CE; border-radius: 4px; padding: 4px; background-color: white;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_layout = QHBoxLayout()
        title_label = QLabel("系统历史检测记录库")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setStyleSheet("color: #1E3A8A;")
        top_layout.addWidget(title_label)
        top_layout.addStretch()

        # ================= 【新增】：页面跳转按钮 =================
        btn_nav_main = QPushButton("🏠 跳转: 监控主页")
        btn_nav_setting = QPushButton("⚙️ 跳转: 系统设置")
        btn_nav_main.setStyleSheet(
            "background-color: #5C6BC0; color: white; padding: 8px; border-radius: 4px; margin-right: 10px;")
        btn_nav_setting.setStyleSheet(
            "background-color: #5C6BC0; color: white; padding: 8px; border-radius: 4px; margin-right: 10px;")
        btn_nav_main.clicked.connect(self.jump_to_main)
        btn_nav_setting.clicked.connect(self.jump_to_setting)

        top_layout.addWidget(btn_nav_main)
        top_layout.addWidget(btn_nav_setting)
        # =======================================================

        btn_export = QPushButton("刷新日志列表")
        btn_export.setStyleSheet("background-color: #4CAF50;")
        btn_export.clicked.connect(self.load_csv_data)
        top_layout.addWidget(btn_export)
        main_layout.addLayout(top_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #90B4CE;")
        main_layout.addWidget(line)

        body_layout = QHBoxLayout()
        main_layout.addLayout(body_layout)

        # === 左侧：日志筛选面板 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_panel.setFixedWidth(280)

        group_filter = QGroupBox("日志多维筛选")
        vbox_filter = QVBoxLayout()
        vbox_filter.setSpacing(15)

        vbox_filter.addWidget(QLabel("起始日期:"))
        self.date_start = QDateEdit(QDate.currentDate().addDays(-7))
        self.date_start.setCalendarPopup(True)
        vbox_filter.addWidget(self.date_start)

        vbox_filter.addWidget(QLabel("结束日期:"))
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        vbox_filter.addWidget(self.date_end)

        vbox_filter.addWidget(QLabel("检测结果类型:"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["全部类型", "正常作业", "未戴安全帽", "未穿防护服", "过近", "危险区域闯入"])
        vbox_filter.addWidget(self.combo_type)

        vbox_filter.addWidget(QLabel("系统定级:"))
        self.combo_level = QComboBox()
        self.combo_level.addItems(["全部等级", "安全", "预警", "危险"])
        vbox_filter.addWidget(self.combo_level)

        self.btn_search = QPushButton("🔍 立即检索")
        self.btn_search.setStyleSheet("background-color: #FF9800; margin-top: 10px;")
        self.btn_search.clicked.connect(self.load_csv_data)
        vbox_filter.addWidget(self.btn_search)

        vbox_filter.addStretch()
        group_filter.setLayout(vbox_filter)
        left_layout.addWidget(group_filter)
        body_layout.addWidget(left_panel)

        # === 右侧：数据表格与画面预览 ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)

        group_table = QGroupBox("历史检测记录列表 (点击查看详情)")
        vbox_table = QVBoxLayout()

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["检测时间", "监控区域", "识别结果", "系统定级", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)

        self.table.itemSelectionChanged.connect(self.update_preview)

        vbox_table.addWidget(self.table)
        group_table.setLayout(vbox_table)
        right_layout.addWidget(group_table, 2)

        group_preview = QGroupBox("检测画面留存与详情")
        hbox_preview = QHBoxLayout()

        self.lbl_preview_img = QLabel("尚未选择记录...")
        self.lbl_preview_img.setAlignment(Qt.AlignCenter)
        self.lbl_preview_img.setStyleSheet("background-color: #2b2b2b; border: 2px solid #555; border-radius: 8px;")
        self.lbl_preview_img.setMinimumSize(400, 250)
        self.lbl_preview_img.setScaledContents(True)
        hbox_preview.addWidget(self.lbl_preview_img, 3)

        self.lbl_preview_text = QLabel("正在等待数据加载...")
        self.lbl_preview_text.setWordWrap(True)
        self.lbl_preview_text.setFont(QFont("Microsoft YaHei", 12))
        self.lbl_preview_text.setStyleSheet(
            "padding: 10px; background-color: #FFFFFF; border-radius: 8px; border: 1px solid #CFD8DC;")
        hbox_preview.addWidget(self.lbl_preview_text, 2)

        group_preview.setLayout(hbox_preview)
        right_layout.addWidget(group_preview, 1)

        body_layout.addWidget(right_panel)

    # ================= 核心：极其健壮的数据读取与过滤引擎 =================
    def load_csv_data(self):
        csv_file = app_path("history.csv")

        if not os.path.exists(csv_file):
            self.table.setRowCount(0)
            self.lbl_preview_img.setText("系统尚未产生任何检测数据记录。")
            self.lbl_preview_text.setText("请先返回主页进行图像或视频检测。")
            return

        all_rows = []
        try:
            with open(csv_file, mode="r", encoding="utf-8-sig") as f:
                all_rows = list(csv.reader(f))
        except UnicodeDecodeError:
            try:
                with open(csv_file, mode="r", encoding="gbk") as f:
                    all_rows = list(csv.reader(f))
            except Exception as e:
                print(f"读取失败: {e}")
                return

        if not all_rows:
            self.table.setRowCount(0)
            self.lbl_preview_img.setText("记录文件存在，但内容为空。")
            return

        if len(all_rows[0]) > 0 and ("时间" in all_rows[0][0] or "监控区域" in all_rows[0][1]):
            all_rows.pop(0)

        filter_type = self.combo_type.currentText()
        filter_level = self.combo_level.currentText()
        start_date = self.date_start.date()
        end_date = self.date_end.date()

        filtered_rows = []

        for row in all_rows:
            if len(row) < 6:
                row.extend([""] * (6 - len(row)))

            time_str, location, violation, level, state, img_path = row[:6]

            try:
                date_part = time_str.split(" ")[0]
                row_date = QDate.fromString(date_part, "yyyy-MM-dd")
                if row_date.isValid():
                    if row_date < start_date or row_date > end_date:
                        continue
            except:
                pass

            if filter_type != "全部类型":
                if filter_type not in violation:
                    continue

            if filter_level != "全部等级":
                if filter_level not in level:
                    continue

            filtered_rows.append(row)

        filtered_rows.reverse()
        self.table.setRowCount(len(filtered_rows))

        if len(filtered_rows) == 0:
            self.lbl_preview_img.clear()
            self.lbl_preview_img.setText("未能检索到符合条件的记录。")
            self.lbl_preview_text.setText("提示：尝试将左侧【起始日期】调前，\\n或选择【全部类型/等级】再试。")
        else:
            self.lbl_preview_img.setText("请在上方表格中点击任意一行查看详情。")
            self.lbl_preview_text.setText("数据加载完毕。")

        for row_idx, row_data in enumerate(filtered_rows):
            time_str, location, violation, level, state, img_path = row_data[:6]

            for col, text in enumerate([time_str, location, violation, level]):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 3:
                    if "危险" in text:
                        item.setForeground(QColor("#C62828"))
                    elif "预警" in text:
                        item.setForeground(QColor("#F57F17"))
                    elif "安全" in text:
                        item.setForeground(QColor("#2E7D32"))
                self.table.setItem(row_idx, col, item)

            action_item = QTableWidgetItem("查看图像")
            action_item.setTextAlignment(Qt.AlignCenter)
            action_item.setForeground(QColor("#1E3A8A"))
            self.table.setItem(row_idx, 4, action_item)

            self.table.item(row_idx, 0).setData(Qt.UserRole, state)
            self.table.item(row_idx, 1).setData(Qt.UserRole, img_path)

        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    # ================= 联动显示功能 =================
    def update_preview(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        time_str = self.table.item(row, 0).text()
        location = self.table.item(row, 1).text()
        violation = self.table.item(row, 2).text()
        level = self.table.item(row, 3).text()

        img_state = self.table.item(row, 0).data(Qt.UserRole)
        img_path = self.table.item(row, 1).data(Qt.UserRole)

        real_img_path = img_path if os.path.isabs(img_path) else app_path(img_path)

        if os.path.exists(real_img_path):
            pixmap = QPixmap(real_img_path)
            self.lbl_preview_img.setPixmap(pixmap)

            if img_state == "danger":
                self.lbl_preview_img.setStyleSheet("border: 4px solid #E57373; border-radius: 8px;")
            elif img_state == "warning":
                self.lbl_preview_img.setStyleSheet("border: 4px solid #FFD54F; border-radius: 8px;")
            else:
                self.lbl_preview_img.setStyleSheet("border: 4px solid #81C784; border-radius: 8px;")
        else:
            self.lbl_preview_img.clear()
            self.lbl_preview_img.setText(
                f"未能找到对应的留存图像！\n(文件可能已被删除或移动)\n\n预期路径: {real_img_path}"
            )
            self.lbl_preview_img.setStyleSheet("background-color: #2b2b2b; color: #E57373; border: 2px dashed #C62828;")
    # ================= 页面跳转逻辑 =================
    def jump_to_main(self):
        from main_page import SafetyDetectionDemo
        self.win_main = SafetyDetectionDemo()
        self.win_main.show()
        self.hide()

    def jump_to_setting(self):
        from setting_page import SystemSettingsWindow
        self.win_setting = SystemSettingsWindow()
        self.win_setting.show()
        self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlarmHistoryWindow()
    window.show()
    sys.exit(app.exec_())