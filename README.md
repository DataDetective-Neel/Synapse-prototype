# 🚌 ADAS: Blind Spot Detection System for Buses

## **WHAT DOES IT DO?**

This is an **Intelligent Driver Assistance System (ADAS)** designed to detect objects (vehicles, pedestrians, cyclists) in the **left blind spot** of a large bus and alert the driver in **real-time** with:
- 🔴 **Visual Alert**: Red flashing overlay on the driver's screen + bounding boxes
- 🔊 **Audio Alert**: High-frequency beep (1000Hz for 500ms) to grab the driver's attention
- 📊 **Remote Monitoring**: A company dashboard that tracks all alerts in real-time via MQTT

The system uses a **laptop webcam** instead of expensive IoT sensors, making it cost-effective for deployment on existing buses.

---

## **HOW DOES IT WORK?**

The system is divided into **3 Architectural Layers**:

### **Layer 1: Perception (The "Eyes")**
- **File**: `core/detection.py`
- **Tech**: YOLOv8 Nano (object detection) + OpenCV (frame processing)
- **Function**: Continuously monitors the webcam feed and detects objects (person, car, bicycle)
- **Output**: Bounding boxes around detected objects with labels

### **Layer 2: Decision Logic (The "Brain")**
- **File**: `core/detection.py` (same file, different method)
- **Function**: Analyzes detected objects to determine if they pose a danger
- **Algorithm**: 
  - Tracks objects across frames using unique IDs
  - Calculates the **bounding box area** (larger area = closer object)
  - Triggers an alert if the object area **increases by 10% per frame** (approaching)
  - Filters false positives (low confidence detections ignored)
- **Output**: List of "alerts" with object type and danger status

### **Layer 3: Communication & Monitoring (The "Network")**
- **Files**: 
  - `core/can_handler.py` (virtual CAN bus simulation)
  - `gateway.py` (MQTT bridge)
  - `dashboard_company.py` (web dashboard)
- **Function**:
  - Driver receives alerts on local screen (dashboard_driver.py) with beep
  - Alerts are sent as CAN bus messages (simulated via `python-can`)
  - Gateway listens to CAN messages and forwards them to MQTT broker
  - Company dashboard (Streamlit web app) subscribes to MQTT and displays live alerts

### **Data Flow Diagram**

```
Webcam Feed
    ↓
YOLOv8 Detection (YOLOv8n model)
    ↓
Decision Logic (Proximity Check)
    ↓ [Alert Triggered]
Driver Dashboard (Visual + Audio) ← → CAN Bus (Virtual Simulation)
                                       ↓
                                    Gateway
                                       ↓
                                  MQTT Broker (HiveMQ Public)
                                       ↓
                              Company Dashboard (Streamlit Web UI)
```

---

## **WHY WAS IT BUILT THIS WAY?**

### **1. Why YOLOv8 Nano?**
- **Speed**: Runs in real-time on laptops without high-end GPUs (even with RTX 3050, it's overkill for Nano)
- **Accuracy**: YOLOv8n achieves 80%+ mAP (mean average precision) with 80.4 FPS on CPU
- **Memory**: Only ~6.3MB model size, easily fits in 6GB VRAM
- **Alternative considered**: Faster RCNN was too slow; YOLOv5 is heavier

### **2. Why Virtual CAN Bus?**
- **Real vehicles use CAN**: The protocol is standard in automotive systems
- **No hardware needed**: Simulated via `python-can` library
- **Scalability**: In production, replace `interface='virtual'` with `interface='socketcan'` + actual CAN hardware
- **Standardization**: Company systems already listen to CAN; this maintains compatibility

### **3. Why MQTT for Company Dashboard?**
- **Real-time**: Events push to subscribers instantly
- **Scalable**: One bus can broadcast to multiple dashboards
- **Cloud-ready**: MQTT easily bridges to AWS IoT, Azure IoT Hub, etc.
- **Public broker**: HiveMQ allows testing without setting up infrastructure

### **4. Why Streamlit for Company Dashboard?**
- **Fast deployment**: No frontend framework needed; pure Python
- **Real-time**: Built-in `st.rerun()` for live updates
- **Professional UI**: Charts, tables, and status indicators out-of-the-box
- **Mobile-friendly**: Responsive design works on tablets/phones

### **5. Why Laptop Webcam Instead of IoT?**
- **Cost**: Webcam is free (already on laptop); IoT sensors cost $50-200 each
- **Installation**: No wiring; just mount the laptop
- **Maintenance**: Single unit to maintain vs. multiple sensors
- **Trade-off**: Narrower field-of-view (FOV ~60-90°) vs. wide-angle IoT (~120°+)

---

## **HOW TO RUN IT?**

### **Prerequisites**
- **OS**: Windows 10+ (for `winsound` audio alerts) or Linux/Mac (falls back to silent mode)
- **Hardware**: Laptop with webcam + GPU (RTX 3050 or better, or CPU-only mode)
- **Python**: Python 3.8+

### **Step 1: Setup Environment**

```bash
# Navigate to project folder
cd a:\Synapse\ prototype

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download YOLOv8 model (runs automatically on first use)
# Or pre-download:
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### **Step 2: Run the System**

**Terminal 1: Start the Driver Dashboard** (Real-time detection + alerts)
```bash
python dashboard_driver.py
```
- Opens a window showing live webcam feed with bounding boxes
- When an object approaches, the screen turns RED and a BEEP sounds
- Press `q` to quit

**Terminal 2: Start the Gateway** (CAN Bus → MQTT Bridge)
```bash
python gateway.py
```
- Listens to the virtual CAN bus
- Forwards alerts to MQTT broker
- Shows: `"Gateway: Published to MQTT: ..."`

**Terminal 3: Start the Company Dashboard** (Web UI)
```bash
streamlit run dashboard_company.py
```
- Opens a web dashboard at `http://localhost:8501`
- Shows live alerts and incident log
- Auto-refreshes every 2 seconds

### **Step 3: Test the System**

1. **In the driver dashboard window**:
   - Hold your phone/hand close to the webcam
   - Watch the bounding box grow
   - Listen for the BEEP and watch the screen turn RED

2. **In the company dashboard (web browser)**:
   - Open `http://localhost:8501`
   - You should see "DANGER" status appear
   - The incident log should show the alert with timestamp

### **Step 4: Customize Parameters**

Edit these files to tune the system:

**`core/detection.py`**:
- Line 6: `threshold=0.5` → Confidence threshold (0-1). Lower = more detections but more false positives
- Line 28: `if area > prev_area * 1.1:` → Change `1.1` (10% increase) to adjust sensitivity

**`dashboard_driver.py`**:
- Line 59: `trigger_audio_alert()` → Modify beep frequency/duration in `trigger_audio_alert()` function

**`gateway.py`**:
- Line 3: `MQTT_BROKER = "broker.hivemq.com"` → Replace with your own MQTT broker

**`dashboard_company.py`**:
- Line 10: `MQTT_TOPIC = "adas/alerts/company"` → Change topic name

---

## **TROUBLESHOOTING**

| Issue | Solution |
|-------|----------|
| **Webcam not detected** | Check if camera is in use by another app. Disable Zoom/Teams camera. |
| **YOLOv8 model download fails** | Manually download from [ultralytics releases](https://github.com/ultralytics/ultralytics/releases) and place in project folder. |
| **No audio beep on Mac/Linux** | Audio falls back to silent. Install `simpleaudio` for cross-platform support. |
| **MQTT not connecting** | Check internet connection. Switch to localhost if you run your own MQTT broker. |
| **Streamlit dashboard not loading** | Run `pip install --upgrade streamlit`. Check port 8501 is not in use. |
| **High GPU usage** | Use YOLOv8n instead of YOLOv8s or YOLOv8m. Reduce frame size. |

---

## **SYSTEM ARCHITECTURE DIAGRAM**

```
┌─────────────────────────────────────────────────────────────┐
│                   DRIVER'S LAPTOP                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Webcam      │→→→ │ YOLOv8 Nano  │→→→ │ Decision     │  │
│  │  Feed        │    │ (Detection)  │    │ Logic        │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         ↓                   ↓                     ↓           │
│    (Raw 30 FPS)    (Annotated Frame)       (Alerts List)    │
│         ↓                                         ↓           │
│         └─────────────────────────────────────────┘          │
│                         ↓                                    │
│         ┌───────────────────────────────┐                   │
│         │  Driver Dashboard             │                   │
│         │  - Live Video + Bounding Box  │                   │
│         │  - RED Overlay on Alert       │                   │
│         │  - BEEP Audio (1000Hz)        │                   │
│         └───────────────────────────────┘                   │
│                         ↓                                    │
│         ┌───────────────────────────────┐                   │
│         │  CAN Bus Simulator            │                   │
│         │  (Virtual Interface)          │                   │
│         │  - ID 0x100: Object Type      │                   │
│         │  - ID 0x101: Alert Status     │                   │
│         └───────────────────────────────┘                   │
│                         ↓                                    │
└─────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────┐
│                    GATEWAY SERVER                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  CAN Message → Parse → MQTT Publish                         │
│  (Virtual CAN)   ↓     (HiveMQ Broker)                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────┐
│                   COMPANY SERVER                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────────────────────┐         │
│  │  Company Dashboard (Streamlit Web UI)          │         │
│  │  - Live Status: DANGER / SAFE                  │         │
│  │  - Incident Log (last 50 events)               │         │
│  │  - Auto-refresh every 2 seconds                │         │
│  │  - URL: http://localhost:8501                  │         │
│  └────────────────────────────────────────────────┘         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## **KEY PARAMETERS & THRESHOLDS**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **Confidence Threshold** | 0.5 | Only detections >50% confidence are shown |
| **Area Increase Threshold** | 10% (1.1x) | Alert if bounding box area grows 10% between frames |
| **YOLO Model** | YOLOv8n | Nano version for real-time on any hardware |
| **Beep Frequency** | 1000 Hz | High pitch to grab driver's attention |
| **Beep Duration** | 500 ms | Long enough to hear but not annoying |
| **MQTT Topic** | adas/alerts/company | Company subscribes here |
| **MQTT Broker** | broker.hivemq.com | Public broker (change for production) |
| **Company Dashboard Refresh** | 2 seconds | Update rate for alert visualization |

---

## **FUTURE ENHANCEMENTS**

1. **Multi-Camera Support**: Monitor left, right, and rear blind spots simultaneously
2. **Speed Estimation**: Use optical flow to estimate approaching object velocity
3. **Edge Computing**: Deploy YOLOv8 on a Raspberry Pi in the vehicle
4. **Physical CAN Hardware**: Connect MCP2515 CAN transceiver for real vehicle integration
5. **Cloud Logging**: Store all alerts in a database (PostgreSQL/MongoDB) for analytics
6. **Driver Behavior**: Track if driver ignores alerts; send reports to company
7. **AI-Based Filtering**: Learn false positives specific to a bus model

---

## **FILE STRUCTURE**

```
📁 Synapse prototype/
├── 📄 README.md                    ← You are here
├── 📄 requirements.txt             ← Python dependencies
├── 📄 dashboard_driver.py          ← Driver's real-time dashboard
├── 📄 dashboard_company.py         ← Company's web dashboard
├── 📄 gateway.py                   ← CAN-to-MQTT bridge
├── 📁 core/
│   ├── 📄 detection.py             ← YOLOv8 + decision logic
│   └── 📄 can_handler.py           ← Virtual CAN bus simulator
├── 📄 yolov8n.pt                   ← YOLOv8 model (auto-downloaded)
└── 📁 .venv/                       ← Virtual environment
```

---

## **CONTACT & SUPPORT**

- **Issue**: Something not working? Check troubleshooting section above.
- **Enhancement**: Want to add a feature? Modify the relevant file in `core/` folder.
- **Deployment**: For production, contact your vehicle system integrator.

---

**Built for Real-Time Bus Safety** 🚌✨
