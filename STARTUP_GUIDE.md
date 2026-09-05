# 🚀 Advanced Vehicle Surveillance System - Startup Guide

## Prerequisites Checklist ✅

Before starting the project, ensure you have:

- ✅ **Python 3.8+** installed
- ✅ **Node.js 16+** installed  
- ✅ **MongoDB** database (local or cloud)
- ✅ **Tesseract OCR** installed at `C:\Program Files\Tesseract-OCR\`
- ✅ **Virtual Environment** created and activated

## 🎯 Quick Start (Recommended)

### Step 1: Environment Setup

1. **Create Environment File**:
   ```bash
   cd "D:\ADVANCED VEHICLE SURVILLENCE SYSTEM\backend"
   copy con .env
   ```
   
   Add your MongoDB connection string:
   ```
   MONGODB_URI=mongodb://localhost:27017/vehicle_surveillance
   # OR for MongoDB Atlas:
   # MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/vehicle_surveillance
   ```

2. **Activate Virtual Environment**:
   ```bash
   cd "D:\ADVANCED VEHICLE SURVILLENCE SYSTEM\backend"
   .\venv\Scripts\Activate.ps1
   ```

### Step 2: Start Backend Server

```bash
cd "D:\ADVANCED VEHICLE SURVILLENCE SYSTEM\backend\src"
python server.py
```

**Expected Output**:
```
INFO - Successfully connected to MongoDB
INFO - Server starting on http://localhost:5000
```

### Step 3: Start Frontend (New Terminal)

```bash
cd "D:\ADVANCED VEHICLE SURVILLENCE SYSTEM\frontend"
npm install
npm run dev
```

**Expected Output**:
```
Local:   http://localhost:5173/
Network: http://192.168.x.x:5173/
```

### Step 4: Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:5000

---

## 🔧 Detailed Setup Instructions

### Backend Setup

1. **Navigate to Backend Directory**:
   ```bash
   cd "D:\ADVANCED VEHICLE SURVILLENCE SYSTEM\backend"
   ```

2. **Activate Virtual Environment**:
   ```bash
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

4. **Create Environment File**:
   ```bash
   # Create .env file in backend directory
   echo MONGODB_URI=mongodb://localhost:27017/vehicle_surveillance > .env
   ```

5. **Test Tesseract Configuration**:
   ```bash
   cd src
   python test_complete_tesseract.py
   ```

6. **Start Backend Server**:
   ```bash
   python server.py
   ```

### Frontend Setup

1. **Navigate to Frontend Directory**:
   ```bash
   cd "D:\ADVANCED VEHICLE SURVILLENCE SYSTEM\frontend"
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

3. **Start Development Server**:
   ```bash
   npm run dev
   ```

---

## 🧪 Testing the System

### Test 1: Backend Health Check
```bash
curl http://localhost:5000/health
```

### Test 2: Upload a Video
1. Go to http://localhost:5173
2. Navigate to "Upload Footage" page
3. Upload a traffic video file
4. Monitor the processing in the backend logs

### Test 3: Check Processing Results
1. Go to "Detection Results" page
2. View detected license plates
3. Check the database for stored results

---

## 📊 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (React)       │◄──►│   (Flask)       │◄──►│   (MongoDB)     │
│   Port: 5173    │    │   Port: 5000    │    │   Port: 27017   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   AI Processing │
                       │   - YOLOv5      │
                       │   - EasyOCR     │
                       │   - Tesseract   │
                       └─────────────────┘
```

---

## 🚨 Troubleshooting

### Common Issues

#### 1. MongoDB Connection Error
```
ERROR: Failed to connect to MongoDB
```
**Solution**: 
- Check if MongoDB is running
- Verify the connection string in `.env`
- For local MongoDB: `mongodb://localhost:27017/vehicle_surveillance`

#### 2. Tesseract Not Found
```
ERROR: tesseract is not installed or it's not in your PATH
```
**Solution**: 
- Tesseract is already configured at `C:\Program Files\Tesseract-OCR\`
- Run `python test_complete_tesseract.py` to verify

#### 3. Port Already in Use
```
ERROR: Address already in use
```
**Solution**:
- Kill processes using ports 5000 or 5173
- Or change ports in the configuration

#### 4. Virtual Environment Issues
```
ERROR: No module named 'cv2'
```
**Solution**:
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### Performance Optimization

#### For Better Processing Speed:
1. **GPU Support**: Ensure CUDA is available for PyTorch
2. **Memory**: Allocate at least 8GB RAM for video processing
3. **Storage**: Use SSD for faster file I/O

#### For Better Accuracy:
1. **Video Quality**: Use high-resolution videos (1080p+)
2. **Lighting**: Ensure good lighting conditions
3. **Camera Angle**: Position camera at optimal angle

---

## 📁 Project Structure

```
ADVANCED VEHICLE SURVILLENCE SYSTEM/
├── backend/
│   ├── src/
│   │   ├── server.py              # Main Flask server
│   │   ├── plate_recognition.py   # Video processing
│   │   ├── extract_unique_plates.py # Plate extraction
│   │   ├── config/
│   │   │   └── tesseract_config.py # Tesseract settings
│   │   └── test_complete_tesseract.py # Test suite
│   ├── requirements.txt
│   ├── .env                       # Environment variables
│   └── venv/                      # Virtual environment
├── frontend/
│   ├── src/
│   │   ├── components/            # React components
│   │   ├── pages/                 # Application pages
│   │   └── utils/                 # Utility functions
│   ├── package.json
│   └── node_modules/              # Node dependencies
└── STARTUP_GUIDE.md              # This file
```

---

## 🎯 Next Steps

After successful startup:

1. **Upload Test Video**: Try uploading a traffic video
2. **Monitor Processing**: Check logs for processing status
3. **View Results**: Browse detected license plates
4. **Customize Settings**: Adjust Tesseract configuration if needed
5. **Scale Up**: Deploy to production environment

---

## 📞 Support

If you encounter issues:

1. Check the logs in `backend/app.log`
2. Run the test suite: `python test_complete_tesseract.py`
3. Verify all prerequisites are installed
4. Check MongoDB connection
5. Ensure virtual environment is activated

---

## 🎉 Success Indicators

You'll know the system is working correctly when:

- ✅ Backend server starts without errors
- ✅ Frontend loads at http://localhost:5173
- ✅ MongoDB connection is successful
- ✅ Tesseract tests pass
- ✅ Video upload and processing works
- ✅ License plates are detected and stored

**Happy Processing! 🚗📹🔍**


