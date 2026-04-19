# dashboard_driver.py
import cv2
import time
import sys
import json
from datetime import datetime
import paho.mqtt.client as mqtt
from core.detection import ADASDetector
from core.can_handler import CANBusSimulator

MQTT_BROKERS = ["broker.hivemq.com", "test.mosquitto.org"]
MQTT_TOPIC = "adas/alerts/company"
EVENTS_FILE = "incident_events.jsonl"

# Platform-specific audio alert
try:
    import winsound  # Windows only
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    print("Note: Audio alerts not available on this OS.")


def trigger_audio_alert():
    """Trigger a loud beep alert for the driver."""
    if SOUND_AVAILABLE:
        try:
            # Beep: frequency=1000Hz, duration=500ms
            winsound.Beep(1000, 500)
        except Exception as e:
            print(f"Audio alert error: {e}")


def append_local_event(payload):
    """Write events locally so company dashboard can always show incident history."""
    try:
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        print(f"Local event write error: {e}")


def run_driver_dashboard(source=0):
    """
    Main loop for the Driver's view.
    source: 0 for webcam, or 'path/to/video.mp4'
    """
    detector = ADASDetector()
    can_bus = CANBusSimulator()
    cap = cv2.VideoCapture(source)
    mqtt_client = mqtt.Client()
    mqtt_connected = False
    last_heartbeat_ts = 0.0

    for broker in MQTT_BROKERS:
        try:
            rc = mqtt_client.connect(broker, 1883, 60)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                mqtt_client.loop_start()
                mqtt_connected = True
                print(f"Driver MQTT connected to {broker}")
                break
        except Exception:
            continue

    if not mqtt_connected:
        print("MQTT connection failed (driver dashboard) on all brokers.")
    
    print("Starting ADAS Driver Dashboard...")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 1. Perform Detection & Logic
        annotated_frame, alerts = detector.process_frame(frame)

        # 2. Handle Alerts and CAN communication
        if alerts:
            # Trigger Audio Alert (Beep)
            trigger_audio_alert()
            
            # Trigger Visual Alert (Flash Red)
            overlay = annotated_frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), -1)
            cv2.addWeighted(overlay, 0.3, annotated_frame, 0.7, 0, annotated_frame)
            
            for alert in alerts:
                # Send to CAN Bus
                can_bus.send_alert(alert['type'], alert['status'])

                # Publish to MQTT directly so company dashboard can always receive updates.
                if mqtt_connected:
                    status_text = str(alert['status']).upper()
                    status_label = "DANGER" if status_text.startswith("DANGER") else "SAFE"
                    payload = {
                        "event_id": str(time.time_ns()),
                        "event": "Alert Update",
                        "status": status_label,
                        "object_type": alert['type'],
                        "source": "driver-dashboard",
                        "timestamp": str(time.time()),
                        "local_time": datetime.now().strftime("%H:%M:%S")
                    }
                    mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
                    append_local_event(payload)
                else:
                    status_text = str(alert['status']).upper()
                    status_label = "DANGER" if status_text.startswith("DANGER") else "SAFE"
                    payload = {
                        "event_id": str(time.time_ns()),
                        "event": "Alert Update",
                        "status": status_label,
                        "object_type": alert['type'],
                        "source": "driver-dashboard-local",
                        "timestamp": str(time.time()),
                        "local_time": datetime.now().strftime("%H:%M:%S")
                    }
                    append_local_event(payload)
                
                # Add text alert to screen
                cv2.putText(annotated_frame, "!!! WARNING !!!", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        else:
            # Heartbeat every 2 seconds so remote dashboard confirms pipeline health.
            now = time.time()
            if mqtt_connected and (now - last_heartbeat_ts) >= 2.0:
                payload = {
                    "event_id": str(time.time_ns()),
                    "event": "Heartbeat",
                    "status": "SAFE",
                    "object_type": "none",
                    "source": "driver-dashboard",
                    "timestamp": str(now),
                    "local_time": datetime.now().strftime("%H:%M:%S")
                }
                mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
                append_local_event(payload)
                last_heartbeat_ts = now

        # 3. Display the Dashboard
        cv2.imshow('ADAS Driver Dashboard', annotated_frame)

        # Break loop on 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    if mqtt_connected:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    can_bus.close()


if __name__ == "__main__":
    # Change '0' to 'video.mp4' to test with a file
    run_driver_dashboard(source=0)