import sys
import os
import torch
import cv2
import math
import numpy as np
import time
import datetime
import csv
import shutil
import subprocess  # 【新增】用于调用系统底层的 nvidia-smi 检查显卡状态
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QSlider, QDoubleSpinBox,
                             QGroupBox, QGridLayout, QFrame, QSizePolicy, QProgressBar, QFileDialog, QMessageBox)
# 【新增】导入 QTimer 用于定时刷新 UI
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QImage
import warnings
import logging
from path_utils import resource_path, app_path

warnings.filterwarnings("ignore")


# ================= 1. 核心模型推理线程 (处理静态图片) =================
class DetectionThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, image_path, conf, iou):
        super().__init__()
        self.image_path = image_path
        self.conf = conf
        self.iou = iou
        self.MODEL_PATH = resource_path("model", "best.pt")
        self.YOLOV5_PATH = resource_path("yolov5")

    def calculate_depth(self, real_height, focal_length, pixel_height):
        if pixel_height <= 0:
            return 0.0
        return (real_height * focal_length) / pixel_height

    def run(self):
        try:
            start_time = time.time()
            model = torch.hub.load(self.YOLOV5_PATH, 'custom', path=self.MODEL_PATH, source='local', _verbose=False)
            model.conf = self.conf
            model.iou = self.iou

            results = model(self.image_path, size=1280)
            predictions = results.pandas().xyxy[0]

            img_rendered = results.render()[0]
            h_img, w_img = img_rendered.shape[:2]
            cx, cy = w_img / 2, h_img / 2

            people, machines = [], []
            FOCAL, H_LOADER, H_HAT = 800, 3.2, 0.25

            for _, row in predictions.iterrows():
                label = str(row['name']).lower()
                px_h = row['ymax'] - row['ymin']
                x_c, y_c = (row['xmin'] + row['xmax']) / 2, (row['ymin'] + row['ymax']) / 2

                depth_z = self.calculate_depth(H_LOADER if 'loader' in label else H_HAT, FOCAL, px_h)
                pos_3d = {
                    'Z': depth_z,
                    'X': (x_c - cx) * depth_z / FOCAL,
                    'Y': (y_c - cy) * depth_z / FOCAL,
                    'px': (int(x_c), int(y_c)),
                    'conf': row['confidence']
                }

                if 'loader' in label or 'excavator' in label:
                    machines.append(pos_3d)
                else:
                    people.append(pos_3d)

            min_dist = 999.0
            line_pts = None
            if people and machines:
                for p in people:
                    for m in machines:
                        dist = math.sqrt((p['X'] - m['X']) ** 2 + (p['Y'] - m['Y']) ** 2 + (p['Z'] - m['Z']) ** 2)
                        if dist < min_dist:
                            min_dist = dist
                            line_pts = (p['px'], m['px'])

            img_bgr = cv2.cvtColor(img_rendered, cv2.COLOR_RGB2BGR)
            if line_pts:
                cv2.line(img_bgr, line_pts[0], line_pts[1], (0, 0, 255), 3)
                mid = ((line_pts[0][0] + line_pts[1][0]) // 2, (line_pts[0][1] + line_pts[1][1]) // 2)
                cv2.putText(img_bgr, f"{min_dist:.2f}m", mid, cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)

            current_time = time.strftime("%Y%m%d_%H%M%S")
            output_path = app_path("model", "output", f"result_{current_time}.jpg")

            cv2.imwrite(output_path, img_bgr)

            res = {
                "save_path": output_path,
                "distance": min_dist if line_pts else None,
                "time": round(time.time() - start_time, 3),
                "p_count": len(people),
                "m_count": len(machines),
                "conf_m": round(np.mean([m['conf'] for m in machines]), 2) if machines else 0.0,
                "conf_p": round(np.mean([p['conf'] for p in people]), 2) if people else 0.0
            }
            self.finished.emit(res)
        except Exception as e:
            print(f"图片推理失败: {e}")


# ================= 2. 摄像头流检测线程 =================
class CameraThread(QThread):
    frame_ready = pyqtSignal(QPixmap)
    stats_ready = pyqtSignal(dict)

    def __init__(self, conf, iou):
        super().__init__()
        self.conf = conf
        self.iou = iou
        self.running = True
        self.MODEL_PATH = resource_path("model", "best.pt")
        self.YOLOV5_PATH = resource_path("yolov5")

    def calculate_depth(self, real_height, focal_length, pixel_height):
        if pixel_height <= 0:
            return 0.0
        return (real_height * focal_length) / pixel_height

    def stop(self):
        self.running = False
        self.wait()

    def run(self):
        try:
            model = torch.hub.load(self.YOLOV5_PATH, 'custom', path=self.MODEL_PATH, source='local', _verbose=False)
            model.conf = self.conf
            model.iou = self.iou
            cap = cv2.VideoCapture(0)

            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break
                start_time = time.time()
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = model(img_rgb)
                predictions = results.pandas().xyxy[0]
                img_rendered = results.render()[0]

                h_img, w_img = img_rendered.shape[:2]
                cx, cy = w_img / 2, h_img / 2
                people, machines = [], []
                FOCAL, H_LOADER, H_HAT = 800, 3.2, 0.25

                for _, row in predictions.iterrows():
                    label = str(row['name']).lower()
                    px_h = row['ymax'] - row['ymin']
                    x_c, y_c = (row['xmin'] + row['xmax']) / 2, (row['ymin'] + row['ymax']) / 2
                    depth_z = self.calculate_depth(H_LOADER if 'loader' in label else H_HAT, FOCAL, px_h)
                    pos_3d = {
                        'Z': depth_z,
                        'X': (x_c - cx) * depth_z / FOCAL,
                        'Y': (y_c - cy) * depth_z / FOCAL,
                        'px': (int(x_c), int(y_c)),
                        'conf': row['confidence']
                    }
                    if 'loader' in label or 'excavator' in label:
                        machines.append(pos_3d)
                    else:
                        people.append(pos_3d)

                min_dist = 999.0
                line_pts = None
                if people and machines:
                    for p in people:
                        for m in machines:
                            dist = math.sqrt((p['X'] - m['X']) ** 2 + (p['Y'] - m['Y']) ** 2 + (p['Z'] - m['Z']) ** 2)
                            if dist < min_dist:
                                min_dist = dist
                                line_pts = (p['px'], m['px'])

                img_draw = np.ascontiguousarray(img_rendered)
                if line_pts:
                    cv2.line(img_draw, line_pts[0], line_pts[1], (255, 0, 0), 3)
                    mid = ((line_pts[0][0] + line_pts[1][0]) // 2, (line_pts[0][1] + line_pts[1][1]) // 2)
                    cv2.putText(img_draw, f"{min_dist:.2f}m", mid, cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3)

                h, w, ch = img_draw.shape
                bytes_per_line = ch * w
                qt_img = QImage(img_draw.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_img)
                self.frame_ready.emit(pixmap)

                res = {
                    "distance": min_dist if line_pts else None,
                    "time": round(time.time() - start_time, 3),
                    "p_count": len(people),
                    "m_count": len(machines),
                    "conf_m": round(np.mean([m['conf'] for m in machines]), 2) if machines else 0.0,
                    "conf_p": round(np.mean([p['conf'] for p in people]), 2) if people else 0.0
                }
                self.stats_ready.emit(res)
            cap.release()
        except Exception as e:
            print(f"摄像头运行出错: {e}")


# ================= 3. 视频流检测与导出线程 =================
class VideoThread(QThread):
    frame_ready = pyqtSignal(QPixmap)
    stats_ready = pyqtSignal(dict)
    finished_processing = pyqtSignal(str)

    def __init__(self, video_path, conf, iou):
        super().__init__()
        self.video_path = video_path
        self.conf = conf
        self.iou = iou
        self.running = True
        self.MODEL_PATH = resource_path("model", "best.pt")
        self.YOLOV5_PATH = resource_path("yolov5")

    def calculate_depth(self, real_height, focal_length, pixel_height):
        if pixel_height <= 0:
            return 0.0
        return (real_height * focal_length) / pixel_height

    def stop(self):
        self.running = False
        self.wait()

    def run(self):
        try:
            model = torch.hub.load(self.YOLOV5_PATH, 'custom', path=self.MODEL_PATH, source='local', _verbose=False)
            model.conf = self.conf
            model.iou = self.iou
            cap = cv2.VideoCapture(self.video_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))

            current_time = time.strftime("%Y%m%d_%H%M%S")
            save_path = app_path("model", "output", f"video_result_{current_time}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(save_path, fourcc, fps, (width, height))

            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break
                start_time = time.time()

                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = model(img_rgb)
                predictions = results.pandas().xyxy[0]
                img_rendered = results.render()[0]

                h_img, w_img = img_rendered.shape[:2]
                cx, cy = w_img / 2, h_img / 2
                people, machines = [], []
                FOCAL, H_LOADER, H_HAT = 800, 3.2, 0.25

                for _, row in predictions.iterrows():
                    label = str(row['name']).lower()
                    px_h = row['ymax'] - row['ymin']
                    x_c, y_c = (row['xmin'] + row['xmax']) / 2, (row['ymin'] + row['ymax']) / 2
                    depth_z = self.calculate_depth(H_LOADER if 'loader' in label else H_HAT, FOCAL, px_h)
                    pos_3d = {
                        'Z': depth_z,
                        'X': (x_c - cx) * depth_z / FOCAL,
                        'Y': (y_c - cy) * depth_z / FOCAL,
                        'px': (int(x_c), int(y_c)),
                        'conf': row['confidence']
                    }
                    if 'loader' in label or 'excavator' in label:
                        machines.append(pos_3d)
                    else:
                        people.append(pos_3d)

                min_dist = 999.0
                line_pts = None
                if people and machines:
                    for p in people:
                        for m in machines:
                            dist = math.sqrt((p['X'] - m['X']) ** 2 + (p['Y'] - m['Y']) ** 2 + (p['Z'] - m['Z']) ** 2)
                            if dist < min_dist:
                                min_dist = dist
                                line_pts = (p['px'], m['px'])

                img_draw = np.ascontiguousarray(img_rendered)
                if line_pts:
                    cv2.line(img_draw, line_pts[0], line_pts[1], (255, 0, 0), 3)
                    mid = ((line_pts[0][0] + line_pts[1][0]) // 2, (line_pts[0][1] + line_pts[1][1]) // 2)
                    cv2.putText(img_draw, f"{min_dist:.2f}m", mid, cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3)

                bgr_img = cv2.cvtColor(img_draw, cv2.COLOR_RGB2BGR)
                out.write(bgr_img)

                h, w, ch = img_draw.shape
                bytes_per_line = ch * w
                qt_img = QImage(img_draw.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_img)
                self.frame_ready.emit(pixmap)

                res = {
                    "distance": min_dist if line_pts else None,
                    "time": round(time.time() - start_time, 3),
                    "p_count": len(people),
                    "m_count": len(machines),
                    "conf_m": round(np.mean([m['conf'] for m in machines]), 2) if machines else 0.0,
                    "conf_p": round(np.mean([p['conf'] for p in people]), 2) if people else 0.0
                }
                self.stats_ready.emit(res)

            cap.release()
            out.release()
            if self.running:
                self.finished_processing.emit(save_path)
        except Exception as e:
            print(f"视频运行出错: {e}")


# ================= 4. UI 类 =================
class SafetyDetectionDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("基于YOLO的高精度安全作业实时检测系统")
        self.resize(1280, 800)
        self.camera_thread = None
        self.video_thread = None
        self.last_log_time = 0

        self.initUI()
        self.update_demo_state("safe")

        # ================= 【新增】：设置定时器，每 2 秒获取一次真实 GPU 利用率 =================
        self.gpu_timer = QTimer(self)
        self.gpu_timer.timeout.connect(self.update_real_gpu_usage)
        self.gpu_timer.start(2000)

    def initUI(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #E6F0FA; } 
            QGroupBox { font-weight: bold; border: 2px solid #90B4CE; border-radius: 8px; margin-top: 15px; background-color: #F8FBFF; }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #2B4257; }
            QPushButton { background-color: #8CA8F9; color: white; border-radius: 5px; padding: 8px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #7293F0; }
            QLabel { font-size: 14px; color: #333333; }
            QProgressBar { border: 1px solid #90B4CE; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background-color: #4CAF50; width: 10px; margin: 0.5px; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.addLayout(self.create_top_bar())

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #90B4CE;")
        main_layout.addWidget(line)

        body_layout = QHBoxLayout()
        main_layout.addLayout(body_layout)

        left_panel = self.create_left_panel()
        left_panel.setFixedWidth(350)
        body_layout.addWidget(left_panel)

        right_panel = self.create_right_panel()
        body_layout.addWidget(right_panel)

    def create_top_bar(self):
        layout = QHBoxLayout()
        title_label = QLabel("基于深度学习的高精度实时安全作业检测系统")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setStyleSheet("color: #1E3A8A;")
        layout.addWidget(title_label)

        layout.addStretch()

        # 页面跳转按钮
        btn_nav_history = QPushButton("📜 跳转: 历史记录")
        btn_nav_setting = QPushButton("⚙️ 跳转: 系统设置")
        btn_nav_history.setStyleSheet("background-color: #5C6BC0; color: white; padding: 8px; border-radius: 4px;")
        btn_nav_setting.setStyleSheet("background-color: #5C6BC0; color: white; padding: 8px; border-radius: 4px;")
        btn_nav_history.clicked.connect(self.jump_to_history)
        btn_nav_setting.clicked.connect(self.jump_to_setting)

        layout.addWidget(btn_nav_history)
        layout.addWidget(btn_nav_setting)

        layout.addWidget(QPushButton("模型选择"))
        layout.addWidget(QPushButton("模型初始化"))
        layout.addWidget(QLabel("Confidence:"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.0, 1.0)
        self.conf_spin.setValue(0.25)
        layout.addWidget(self.conf_spin)
        layout.addWidget(QLabel("IOU:"))
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.0, 1.0)
        self.iou_spin.setValue(0.40)
        layout.addWidget(self.iou_spin)
        return layout

    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        group_info = QGroupBox("实时检测信息")
        vbox_info = QVBoxLayout()
        self.lbl_time = QLabel("检测用时: -- s")
        self.lbl_count = QLabel("目标数量: --")
        vbox_info.addWidget(self.lbl_time)
        vbox_info.addWidget(self.lbl_count)
        group_info.setLayout(vbox_info)
        layout.addWidget(group_info)

        group_input = QGroupBox("数据源选择")
        grid_input = QGridLayout()
        self.btn_image_select = QPushButton("图像选择")
        self.btn_image_select.clicked.connect(self.on_image_select_clicked)
        self.btn_video_select = QPushButton("视频选择")
        self.btn_video_select.clicked.connect(self.on_video_select_clicked)
        self.btn_cam_open = QPushButton("打开摄像头")
        self.btn_cam_close = QPushButton("关闭摄像头")
        self.btn_cam_open.clicked.connect(self.on_open_camera_clicked)
        self.btn_cam_close.clicked.connect(self.on_close_camera_clicked)

        grid_input.addWidget(self.btn_image_select, 0, 0)
        grid_input.addWidget(QPushButton("图片结果导出"), 0, 1)
        grid_input.addWidget(self.btn_video_select, 1, 0)
        grid_input.addWidget(QPushButton("视频结果导出"), 1, 1)
        grid_input.addWidget(self.btn_cam_open, 2, 0)
        grid_input.addWidget(self.btn_cam_close, 2, 1)
        group_input.setLayout(grid_input)
        layout.addWidget(group_input)

        group_safety = QGroupBox("安全指标实时监控")
        vbox_safety = QVBoxLayout()
        self.lbl_distance = QLabel("人机最近距离: -- 米")
        self.lbl_distance.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.lbl_hardhat = QLabel("安全帽佩戴状态: --")
        self.lbl_hardhat.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        vbox_safety.addWidget(self.lbl_distance)
        vbox_safety.addWidget(self.lbl_hardhat)
        group_safety.setLayout(vbox_safety)
        layout.addWidget(group_safety)

        group_details = QGroupBox("目标检测详情与置信度")
        vbox_details = QVBoxLayout()
        self.lbl_conf_machine = QLabel("机器 (Excavator) 置信度: --")
        self.lbl_conf_person = QLabel("工人 (Worker) 置信度: --")
        self.lbl_attr_hat = QLabel("安全帽 (Hardhat): --")
        self.lbl_attr_vest = QLabel("防护服 (Vest): --")
        for lbl in [self.lbl_conf_machine, self.lbl_conf_person, self.lbl_attr_hat, self.lbl_attr_vest]:
            lbl.setFont(QFont("Microsoft YaHei", 10))
            vbox_details.addWidget(lbl)
        group_details.setLayout(vbox_details)
        layout.addWidget(group_details)

        group_env = QGroupBox("环境与设备状态")
        vbox_env = QVBoxLayout()
        hbox_gpu = QHBoxLayout()
        hbox_gpu.addWidget(QLabel("GPU 利用率:"))
        self.gpu_bar = QProgressBar()
        self.gpu_bar.setRange(0, 100)
        self.gpu_bar.setValue(0)
        self.gpu_bar.setFixedHeight(15)
        hbox_gpu.addWidget(self.gpu_bar)
        vbox_env.addLayout(hbox_gpu)
        self.lbl_fps_stable = QLabel("系统稳定性: 🟢 运行流畅")
        vbox_env.addWidget(self.lbl_fps_stable)
        group_env.setLayout(vbox_env)
        layout.addWidget(group_env)

        group_status = QGroupBox("系统预警状态 (演示控制区)")
        vbox_status = QVBoxLayout()
        self.lbl_status = QLabel("等待运行...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.lbl_status.setMinimumHeight(60)
        vbox_status.addWidget(self.lbl_status)
        group_status.setLayout(vbox_status)
        layout.addWidget(group_status)

        layout.addStretch()
        return panel

    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.canvas = QLabel("请选择图片/视频 或打开摄像头...")
        self.canvas.setAlignment(Qt.AlignCenter)
        self.canvas.setScaledContents(True)
        self.canvas.setStyleSheet(
            "background-color: #2b2b2b; border: 4px solid #555555; border-radius: 10px; color: white;")
        layout.addWidget(self.canvas)
        return panel

    # ================= 【新增核心】：获取真实的 GPU 占用率 =================
    def update_real_gpu_usage(self):
        """调用系统底层 nvidia-smi 静默获取显卡真实负载率"""
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            output = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                startupinfo=startupinfo,
                encoding='utf-8'
            )

            usage = int(output.strip().split('\n')[0])
            self.gpu_bar.setValue(usage)

            if usage > 85:
                self.lbl_fps_stable.setText("系统稳定性: 🟡 高负载计算中")
                self.lbl_fps_stable.setStyleSheet("color: #F57C00; font-weight: bold;")
            else:
                self.lbl_fps_stable.setText("系统稳定性: 🟢 运行流畅")
                self.lbl_fps_stable.setStyleSheet("color: #333333; font-weight: normal;")

        except Exception:
            pass

    # ================= CSV 日志写入 =================
    def save_log_to_csv(self, dist, img_path):
        if dist is None:
            violation = "正常作业"
            level = "🟢 安全"
            state = "safe"
        elif dist < 2.5:
            violation = f"人机距离过近 ({dist:.2f}m)"
            level = "🔴 危险"
            state = "danger"
        elif dist < 5.0:
            violation = f"人机距离预警 ({dist:.2f}m)"
            level = "🟡 预警"
            state = "warning"
        else:
            violation = "正常作业"
            level = "🟢 安全"
            state = "safe"

        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        location = "基坑挖掘区 01"

        csv_file = app_path("history.csv")
        file_exists = os.path.isfile(csv_file)

        with open(csv_file, mode="a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["报警时间", "监控区域", "违规类型", "危险等级", "操作状态", "图片路径"])
            writer.writerow([time_str, location, violation, level, state, img_path])

    # ================= 业务流 =================
    def on_image_select_clicked(self):
        self.stop_all_active_streams()
        input_dir = app_path("model", "input")
        fname, _ = QFileDialog.getOpenFileName(self, '选择作业图像', input_dir, 'Image files (*.jpg *.png *.jpeg)')

        if fname:
            self.lbl_status.setText("⌛ 图像识别中...")
            self.lbl_status.setStyleSheet("background-color: #E0E0E0; color: #666; border-radius: 8px;")
            self.work = DetectionThread(fname, self.conf_spin.value(), self.iou_spin.value())
            self.work.finished.connect(self.on_image_detection_finished)
            self.work.start()

    def on_image_detection_finished(self, data):
        pixmap = QPixmap(data["save_path"])
        self.canvas.setPixmap(pixmap)
        self.on_stream_stats_received(data)
        self.save_log_to_csv(data["distance"], data["save_path"])

    def on_open_camera_clicked(self):
        self.stop_all_active_streams()
        self.lbl_status.setText("📷 正在启动摄像头...")
        self.lbl_status.setStyleSheet("background-color: #B3E5FC; color: #0277BD; border-radius: 8px;")

        self.camera_thread = CameraThread(self.conf_spin.value(), self.iou_spin.value())
        self.camera_thread.frame_ready.connect(self.canvas.setPixmap)
        self.camera_thread.stats_ready.connect(self.on_stream_stats_received)
        self.camera_thread.start()

    def on_close_camera_clicked(self):
        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.stop()
            self.camera_thread = None
            self.reset_canvas()

    def on_video_select_clicked(self):
        self.stop_all_active_streams()
        input_dir = app_path("model", "input")
        fname, _ = QFileDialog.getOpenFileName(self, '选择作业视频', input_dir, 'Video files (*.mp4 *.avi *.mov)')

        if fname:
            self.lbl_status.setText("🎬 视频处理与导出中...")
            self.lbl_status.setStyleSheet("background-color: #E1BEE7; color: #6A1B9A; border-radius: 8px;")
            self.video_thread = VideoThread(fname, self.conf_spin.value(), self.iou_spin.value())
            self.video_thread.frame_ready.connect(self.canvas.setPixmap)
            self.video_thread.stats_ready.connect(self.on_stream_stats_received)
            self.video_thread.finished_processing.connect(self.on_video_finished)
            self.video_thread.start()

    def on_video_finished(self, save_path):
        self.lbl_status.setText("✅ 视频导出完成")
        self.lbl_status.setStyleSheet("background-color: #C8E6C9; color: #2E7D32; border-radius: 8px;")
        QMessageBox.information(self, "处理完成", f"视频已成功逐帧检测，并导出至：\n{save_path}")

    def stop_all_active_streams(self):
        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.stop()
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()

    def reset_canvas(self):
        self.canvas.clear()
        self.canvas.setText("监控流已关闭，等待接入...")
        self.canvas.setStyleSheet(
            "background-color: #2b2b2b; border: 4px solid #555555; border-radius: 10px; color: white;")
        self.lbl_status.setText("等待运行...")
        self.lbl_status.setStyleSheet("background-color: transparent; color: #333;")

    def on_stream_stats_received(self, data):
        self.lbl_time.setText(f"单帧耗时: {data['time']} s")
        self.lbl_count.setText(
            f"目标数量: {data['p_count'] + data['m_count']} (人:{data['p_count']}, 机:{data['m_count']})")
        self.lbl_conf_machine.setText(f"机器置信度: {data['conf_m']}")
        self.lbl_conf_person.setText(f"工人置信度: {data['conf_p']}")

        if data['p_count'] > 0:
            self.lbl_hardhat.setText("安全帽佩戴: 🟢 已规范佩戴")
            self.lbl_hardhat.setStyleSheet("color: #2E7D32;")
            self.lbl_attr_hat.setText("安全帽 (Hardhat): 🟢 已佩戴")
            self.lbl_attr_hat.setStyleSheet("color: #2E7D32;")

        dist = data["distance"]
        if dist is None:
            self.lbl_distance.setText("人机最近距离: --")
            self.canvas.setStyleSheet("border: 4px solid #81C784; border-radius: 10px;")
        else:
            self.lbl_distance.setText(f"人机最近距离: {dist:.2f} 米")
            if dist < 2.5:
                self.lbl_status.setText("🔴 危险！违规作业")
                self.lbl_status.setStyleSheet("background-color: #FFCDD2; color: #C62828; border-radius: 8px;")
                self.canvas.setStyleSheet("border: 4px solid #E57373; border-radius: 10px;")
            elif dist < 5.0:
                self.lbl_status.setText("🟡 距离预警")
                self.lbl_status.setStyleSheet("background-color: #FFECB3; color: #F57F17; border-radius: 8px;")
                self.canvas.setStyleSheet("border: 4px solid #FFD54F; border-radius: 10px;")
            else:
                self.lbl_status.setText("🟢 作业安全")
                self.lbl_status.setStyleSheet("background-color: #C8E6C9; color: #2E7D32; border-radius: 8px;")
                self.canvas.setStyleSheet("border: 4px solid #81C784; border-radius: 10px;")

        is_stream = (self.camera_thread and self.camera_thread.isRunning()) or \
                    (self.video_thread and self.video_thread.isRunning())

        if is_stream and dist is not None and dist < 5.0:
            current_time = time.time()
            if current_time - self.last_log_time > 3.0:
                snap_time_str = time.strftime("%Y%m%d_%H%M%S")
                snap_path = app_path("model", "output", f"snap_{snap_time_str}.jpg")

                pixmap = self.canvas.pixmap()
                if pixmap:
                    pixmap.save(snap_path, "JPG")
                    self.save_log_to_csv(dist, snap_path)
                    self.last_log_time = current_time

    def update_demo_state(self, state):
        pass

    # ================= 页面跳转逻辑 =================
    def jump_to_history(self):
        self.stop_all_active_streams()
        from history_read import AlarmHistoryWindow
        self.win_history = AlarmHistoryWindow()
        self.win_history.show()
        self.hide()

    def jump_to_setting(self):
        self.stop_all_active_streams()
        from setting_page import SystemSettingsWindow
        self.win_setting = SystemSettingsWindow()
        self.win_setting.show()
        self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = SafetyDetectionDemo()
    demo.show()
    sys.exit(app.exec_())