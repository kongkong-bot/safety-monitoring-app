🚀 Quick Start
Due to GitHub's file size limitations, the core YOLOv5 library and the large pre-trained weights are not included in this repository. Please follow the steps below to configure your environment:

1. Environment Setup
Ensure you have Python 3.8+ and PyTorch installed, then install the base dependencies:

Bash
pip install torch torchvision torchaudio opencv-python matplotlib tqdm
2. Clone Dependencies
This project relies on the official Ultralytics YOLOv5 framework. Please clone it into the root directory:

Bash
git clone https://github.com/ultralytics/yolov5
pip install -r yolov5/requirements.txt
3. Retrieve Model Weights (best.pt)
The optimized weight file (best.pt) is hosted on Hugging Face for better accessibility:

Download Link: Download best.pt from Hugging Face

Placement: Please place the downloaded best.pt file directly into the project root directory so that caidan.py can locate it.

📂 Project Structure
Plaintext
├── yolov5/             # YOLOv5 official core code (Clone manually)
├── caidan.py           # Main software logic and entry point
├── requirements.txt    # Project environment configuration
├── best.pt             # Optimized model weights (Download from Hugging Face)
└── README.md           # Project documentation
🖥️ Usage
After configuring the environment and weights, launch the monitoring system via:

Bash
python caidan.py
🛠️ Tech Stack
Language: Python 3.x

Deep Learning: PyTorch / YOLOv5

Advanced Research: DSN-FNO (Dual-Spectrum Based Neural Operator)

Application: Industrial Safety & Human-Machine Interaction Monitoring
