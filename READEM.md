# Advanced Vehicle Surveillance System 

An AI-powered vehicle surveillance system that uses computer vision to automatically detect and read vehicle license plates in real time.

## 📌 Overview

This project combines object detection and optical character recognition (OCR) to build an automatic number plate recognition (ANPR) pipeline. It's designed for real-time surveillance use cases — detecting vehicles, isolating license plates, and extracting the plate number as text.

## ✨ Features

- Real-time vehicle detection using YOLOv5
- License plate localization and cropping
- Text extraction from plates using EasyOCR
- Achieved **94.2% license plate detection accuracy**
- Stores detected plate data in MongoDB for later retrieval and analysis

## 🛠️ Tech Stack

- **Language:** Python
- **Object Detection:** YOLOv5
- **OCR:** EasyOCR
- **Database:** MongoDB
- **Core Concepts:** Computer Vision, Machine Learning

## ⚙️ How It Works

1. Video/image feed is passed into the YOLOv5 model to detect vehicles and license plates.
2. Detected plate regions are cropped from the frame.
3. EasyOCR reads the text from the cropped plate image.
4. Extracted plate numbers (with timestamp) are stored in a MongoDB database.

## 🚀 Getting Started

```bash
# Clone the repository
git clone https://github.com/Saish118/vehicle-surveillance.git
cd vehicle-surveillance

# Install dependencies
pip install -r requirements.txt

# Run the detection script
python main.py
```

*(Update the commands above if your actual file/folder names are different.)*

## 📊 Results

The model achieved **94.2% accuracy** in license plate detection across test data, enabling reliable real-time automatic number plate recognition.

## 📌 Future Improvements

- Add support for multi-camera feeds
- Improve OCR accuracy in low-light conditions
- Build a simple dashboard to view detected vehicles

## 👤 Author

**Sai Narendra Joshi**
📧 JoshiSaish2004@gmail.com
🔗 [LinkedIn](https://linkedin.com/in/sai-joshi-423450380)
