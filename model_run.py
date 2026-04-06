import sys
import os
import torch
import cv2
import math
import numpy as np

import warnings
import logging

# 1. 屏蔽所有的 Python 运行警告 (消除 FutureWarning 等红字)
warnings.filterwarnings("ignore")

# 2. 调高日志拦截级别，屏蔽 YOLOv5 内部的 INFO 打印 (消除 Fusing layers 等白字)
logging.getLogger().setLevel(logging.ERROR)

YOLOV5_DIR = '../yolov5'
if os.path.exists(YOLOV5_DIR):
    sys.path.insert(0, YOLOV5_DIR)
    try:
        import utils.general

        utils.general.check_requirements = lambda *args, **kwargs: None
        #print("🔧 已成功拦截 YOLOv5 自动环境检查！")
    except ImportError:
        pass


# ======================================================================

def calculate_depth(real_height, focal_length, pixel_height):
    """计算目标距离摄像头的深度 (Z轴)"""
    if pixel_height <= 0: return 0.0
    return (real_height * focal_length) / pixel_height


def main():
    # ================= 1. 配置路径与参数 =================
    MODEL_PATH = 'best.pt'
    IMAGE_PATH = 'input/test_image.jpg'  # 确认你的图片名

    # 相机与物理预设参数
    CAMERA_FOCAL_LENGTH = 800
    REAL_LOADER_HEIGHT = 3.2  # 装载机参考高度(米)
    REAL_HAT_HEIGHT = 0.25  # 安全帽高度(米)

    print("🚀 正在加载 YOLOv5 模型...")

    # ================= 2. 加载模型 =================
    try:
        model = torch.hub.load('../yolov5', 'custom', path=MODEL_PATH, source='local',_verbose=False)
        model.conf = 0.1
        model.iou = 0.60

    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return

    # ================= 3. 执行检测 =================
    results = model(IMAGE_PATH,size=1280)
    predictions = results.pandas().xyxy[0]

    # 获取图像的中心点坐标（用于计算真实世界的 X 和 Y 坐标）
    # YOLOv5 results 里面保存了原图的 numpy 数组
    img_height, img_width = results.ims[0].shape[:2]
    cx, cy = img_width / 2, img_height / 2

    # 分别创建工人和机器的列表，用于存放它们的真实 3D 坐标
    people = []
    machines = []

    # ================= 4. 解析数据并构建 3D 坐标系 =================
    for index, row in predictions.iterrows():
        label = str(row['name']).lower()
        xmin, ymin, xmax, ymax = row['xmin'], row['ymin'], row['xmax'], row['ymax']

        # 计算在画面中的参数
        h_px = ymax - ymin
        x_center = (xmin + xmax) / 2
        y_center = (ymin + ymax) / 2

        # 匹配机械类
        if 'loader' in label or 'excavator' in label:
            depth_Z = calculate_depth(REAL_LOADER_HEIGHT, CAMERA_FOCAL_LENGTH, h_px)
            # 计算真实的 X 和 Y 坐标
            real_X = (x_center - cx) * depth_Z / CAMERA_FOCAL_LENGTH
            real_Y = (y_center - cy) * depth_Z / CAMERA_FOCAL_LENGTH

            machines.append({
                'label': label, 'Z': depth_Z, 'X': real_X, 'Y': real_Y,
                'px_center': (int(x_center), int(y_center))  # 存下来为了后面画图
            })

        # 匹配人员类
        elif 'hardhat' in label or 'person' in label:
            depth_Z = calculate_depth(REAL_HAT_HEIGHT, CAMERA_FOCAL_LENGTH, h_px)
            real_X = (x_center - cx) * depth_Z / CAMERA_FOCAL_LENGTH
            real_Y = (y_center - cy) * depth_Z / CAMERA_FOCAL_LENGTH

            people.append({
                'label': label, 'Z': depth_Z, 'X': real_X, 'Y': real_Y,
                'px_center': (int(x_center), int(y_center))
            })

    # ================= 5. 核心逻辑：判断并寻找最近的人机距离 =================
    print("-" * 40)

    # 如果没有同时识别到人或机器，直接跳过计算
    if len(people) == 0 or len(machines) == 0:
        print(f"⚠️ 当前画面识别到 {len(people)} 个人, {len(machines)} 台机器。")
        print("💡 未同时检测到人与机器，不存在交互风险，跳过距离计算。")
        results.show()
        return

    # 寻找最短距离
    min_distance = float('inf')
    closest_pair = None

    for p in people:
        for m in machines:
            # 空间三维两点距离公式: D = √((X1-X2)² + (Y1-Y2)² + (Z1-Z2)²)
            dist = math.sqrt((p['X'] - m['X']) ** 2 + (p['Y'] - m['Y']) ** 2 + (p['Z'] - m['Z']) ** 2)

            if dist < min_distance:
                min_distance = dist
                closest_pair = (p, m)

    # ================= 6. 输出结果与可视化 =================
    print("🚨 警告：发现安全作业半径内的人机交互！")
    print(f"🎯 最危险目标: [工人 {closest_pair[0]['label']}] <---> [机械 {closest_pair[1]['label']}]")
    print(f"📏 真实空间距离: {min_distance:.2f} 米")
    print("-" * 40)

    # 【可视化强化】提取画好框的图片，并用 OpenCV 连线
    # results.render()[0] 会返回带有 YOLO 框的 RGB 图像矩阵
    img_rendered = results.render()[0]
    img_bgr = cv2.cvtColor(img_rendered, cv2.COLOR_RGB2BGR)  # OpenCV 需要 BGR 格式

    # 获取最危险的两人在画面中的中心坐标
    pt1 = closest_pair[0]['px_center']
    pt2 = closest_pair[1]['px_center']

    # 在两人之间画一条醒目的红线
    cv2.line(img_bgr, pt1, pt2, (0, 0, 255), 3)

    # 在线段中间写上距离
    mid_pt = ((pt1[0] + pt2[0]) // 2, (pt1[1] + pt2[1]) // 2 - 10)
    cv2.putText(img_bgr, f"{min_distance:.2f}m", mid_pt, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    # 弹出窗口显示最终结果
    #cv2.imshow("Safety Operation Monitoring", img_bgr)
    #cv2.waitKey(0)  # 按任意键关闭窗口
    #cv2.destroyAllWindows()
    cv2.imwrite("output/final_result.jpg", img_bgr)
    print("📸 测距结果已成功画线，并保存为当前目录下的 'final_result.jpg'")


if __name__ == "__main__":
    main()