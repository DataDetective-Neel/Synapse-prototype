# Working Explanation for Presentation

## What this project does
This project is a real-time blind-spot detection prototype for buses. It uses a webcam, YOLOv8 object detection, a simulated CAN bus, MQTT messaging, and a Streamlit dashboard to warn the driver and show alerts to the company.

## Big idea
The system is split into two communication layers:
- CAN handles the vehicle-side message flow.
- MQTT handles the remote dashboard flow.

That makes the prototype feel like a real vehicle safety system while still being easy to run on a laptop.

## End-to-end flow
1. The webcam feed goes into `core/detection.py`.
2. YOLOv8 detects objects such as people, cars, and bicycles.
3. The system tracks each object across frames.
4. If an object's bounding box keeps getting larger, the system treats it as approaching and creates a danger alert.
5. `dashboard_driver.py` shows the live camera feed, highlights danger in red, and plays a beep on Windows.
6. The alert is sent through `core/can_handler.py` as a simulated CAN message.
7. `gateway.py` reads the CAN message and publishes the alert to MQTT.
8. `dashboard_company.py` subscribes to MQTT and shows the live alert history in a web dashboard.
9. `incident_events.jsonl` stores a local backup log of events.

## How CAN works here
CAN stands for Controller Area Network. In real vehicles, it is the internal network used by ECUs and sensors to exchange short messages.

In this project, CAN is simulated using the `python-can` library in `core/can_handler.py`.

### What the CAN simulator sends
For each alert, the code sends two CAN frames:
- ID `0x101`: alert status
- ID `0x100`: object type

### What those messages mean
- Alert status uses a single byte:
	- `1` = danger
	- `0` = safe
- Object type is simplified to the first character of the class label, such as `p` for person.

### Why this is useful
- It imitates real vehicle communication.
- It keeps the driver side separate from the dashboard side.
- It gives the project an automotive-style architecture without requiring hardware.

## How MQTT works here
MQTT stands for Message Queuing Telemetry Transport. It is a lightweight publish/subscribe protocol used for IoT and live monitoring.

In this project, MQTT is used to send alerts from the vehicle side to the company dashboard.

### MQTT flow
- A publisher sends JSON messages to a topic.
- A subscriber listens to that topic and receives updates instantly.
- The topic used here is `adas/alerts/company`.

### Who publishes
- `dashboard_driver.py` publishes alert messages directly when it detects danger.
- `gateway.py` also publishes messages after reading CAN alerts.

### Who subscribes
- `dashboard_company.py` subscribes to the MQTT topic and displays incoming events.

### Why MQTT is useful
- It is simple and lightweight.
- One message can reach multiple dashboards.
- It works well for live monitoring.
- It keeps the sender and receiver loosely coupled.

## File by file explanation

### `core/detection.py`
This is the vision and decision-making part. The `ADASDetector` class loads the YOLOv8n model and processes each frame from the camera. It draws bounding boxes around detected objects and compares the current bounding-box area with the previous one. If the area increases by more than 10%, the object is assumed to be getting closer and an alert is created.

### `dashboard_driver.py`
This is the driver's live interface. It opens the webcam, sends each frame to the detector, and displays the annotated video. When alerts exist, it flashes a red overlay, shows a warning message, and triggers a beep. It also sends alert data to MQTT and writes a backup copy to the local event log.

### `core/can_handler.py`
This simulates a vehicle CAN bus. It sends two CAN messages for each alert: one for the alert status and one for the object type. This lets the project behave like an automotive system without real CAN hardware.

### `gateway.py`
This acts as the bridge between the vehicle side and the company side. It listens for CAN messages on the virtual bus. When it receives an alert message, it converts it into JSON and publishes it to the MQTT topic used by the company dashboard.

### `dashboard_company.py`
This is the remote monitoring dashboard built with Streamlit. It connects to MQTT, receives live alerts, stores them in session state, and displays them in a table. If MQTT is unavailable, it falls back to reading the local `incident_events.jsonl` file so the demo still works.

### `requirements.txt`
This file lists the dependencies needed to run the project, including OpenCV, Ultralytics, python-can, paho-mqtt, Streamlit, pandas, NumPy, and PyTorch.

## Important ideas to explain in the presentation
- YOLOv8 is used because it is fast enough for real-time detection.
- A growing bounding box means the object is getting closer.
- CAN is simulated so the system looks like a real vehicle communication setup.
- MQTT is used so the company dashboard can receive live alerts.
- Streamlit is used because it is simple, fast to build, and good for live dashboards.

## Simple presentation script
"The system starts with a webcam that monitors the bus blind spot. YOLOv8 detects nearby objects and tracks them across frames. If an object gets closer, the driver receives a red warning and a beep. The alert is then sent through a simulated CAN bus, forwarded by a gateway over MQTT, and displayed on a company dashboard in real time."

## Short architecture summary
- Perception: `core/detection.py`
- Driver warning UI: `dashboard_driver.py`
- CAN simulation: `core/can_handler.py`
- Network bridge: `gateway.py`
- Company dashboard: `dashboard_company.py`

## Event format
A typical event contains:
- `event_id`
- `event`
- `status`
- `object_type`
- `source`
- `timestamp`
- `local_time`

Safe events usually have `status: SAFE`, while danger events use `status: DANGER`.

## One-line summary
This project is a prototype ADAS pipeline that detects approaching objects, warns the driver immediately, and shares the alert with a remote company dashboard.
