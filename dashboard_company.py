# dashboard_company.py
import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
from datetime import datetime
import time
from queue import Queue, Empty
import os

EVENTS_FILE = "incident_events.jsonl"

# Page Config
st.set_page_config(page_title="ADAS Company Monitor", layout="wide")
st.title("🏢 ADAS Fleet Remote Monitor")

# Initialize session state to store alerts
if 'alert_history' not in st.session_state:
    st.session_state.alert_history = []
if 'messages_received' not in st.session_state:
    st.session_state.messages_received = 0
if 'incoming_queue' not in st.session_state:
    st.session_state.incoming_queue = Queue()
if 'event_ids' not in st.session_state:
    st.session_state.event_ids = set()
if 'file_offset' not in st.session_state:
    st.session_state.file_offset = 0

# MQTT Configuration
MQTT_BROKERS = ["broker.hivemq.com", "test.mosquitto.org"]
MQTT_TOPIC = "adas/alerts/company"

# MQTT Callback
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        payload['local_time'] = datetime.now().strftime("%H:%M:%S")
        # Push into a thread-safe queue provided as MQTT userdata.
        if userdata is not None:
            userdata.put(payload)

    except Exception as e:
        print(f"Error parsing MQTT: {e}")

# Setup MQTT Client (avoid reconnecting every rerun)
if "mqtt_client" not in st.session_state:
    client = mqtt.Client()
    client.user_data_set(st.session_state.incoming_queue)
    client.on_message = on_message
    st.session_state.mqtt_connected = False
    st.session_state.mqtt_broker = "none"
    last_error = None

    for broker in MQTT_BROKERS:
        try:
            rc = client.connect(broker, 1883, 60)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                sub_rc, _mid = client.subscribe(MQTT_TOPIC)
                if sub_rc == mqtt.MQTT_ERR_SUCCESS:
                    client.loop_start()
                    st.session_state.mqtt_client = client
                    st.session_state.mqtt_connected = True
                    st.session_state.mqtt_broker = broker
                    break
                else:
                    last_error = f"Subscribe failed on {broker} with code {sub_rc}"
            else:
                last_error = f"Connect failed on {broker} with code {rc}"
        except Exception as e:
            last_error = f"{broker}: {e}"

    if not st.session_state.mqtt_connected:
        st.error(f"MQTT Connection Error: {last_error}")

# Drain queued MQTT payloads into session state on the main Streamlit thread.
while True:
    try:
        item = st.session_state.incoming_queue.get_nowait()
        event_id = item.get('event_id')
        if event_id is None or event_id not in st.session_state.event_ids:
            if event_id is not None:
                st.session_state.event_ids.add(event_id)
            st.session_state.alert_history.insert(0, item)
            st.session_state.messages_received += 1
            if len(st.session_state.alert_history) > 50:
                st.session_state.alert_history.pop()
    except Empty:
        break

# Local file fallback ingestion for guaranteed prototype logging.
if os.path.exists(EVENTS_FILE):
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            f.seek(st.session_state.file_offset)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                event_id = item.get('event_id')
                if event_id is None or event_id not in st.session_state.event_ids:
                    if event_id is not None:
                        st.session_state.event_ids.add(event_id)
                    st.session_state.alert_history.insert(0, item)
                    if len(st.session_state.alert_history) > 50:
                        st.session_state.alert_history.pop()
            st.session_state.file_offset = f.tell()
    except Exception as e:
        st.warning(f"Local fallback read error: {e}")

# UI Layout
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Live Status")
    st.caption(f"MQTT connected: {st.session_state.get('mqtt_connected', False)} | Broker: {st.session_state.get('mqtt_broker', 'none')} | Topic: {MQTT_TOPIC}")
    st.caption(f"Messages received: {st.session_state.get('messages_received', 0)}")

    # ✅ FIX: Check if list has data
    if len(st.session_state.alert_history) > 0:
        latest = st.session_state.alert_history[0]

        status_text = str(latest.get('status', 'UNKNOWN')).upper()
        color = "red" if status_text.startswith("DANGER") else "green"

        st.markdown(
            f"### Current Vehicle State: <span style='color:{color}'>{latest.get('status', 'UNKNOWN')}</span>",
            unsafe_allow_html=True
        )
    else:
        st.info("Waiting for vehicle data...")

    st.subheader("What This Dashboard Shows")
    st.write("1. Current vehicle state (SAFE or DANGER)")
    st.write("2. Live incident log with event, status, object_type, source, timestamp")
    st.write("3. Last 50 MQTT messages on the subscribed topic")

    if st.button("Publish Test Event"):
        if st.session_state.get("mqtt_connected", False):
            test_payload = {
                "event": "UI Test",
                "status": "DANGER",
                "object_type": "person",
                "source": "dashboard-company",
                "timestamp": str(time.time()),
                "local_time": datetime.now().strftime("%H:%M:%S")
            }
            st.session_state.mqtt_client.publish(MQTT_TOPIC, json.dumps(test_payload))
            st.success("Test event published to topic.")
        else:
            st.error("MQTT is not connected.")

with col2:
    st.subheader("Incident Log")

    if len(st.session_state.alert_history) > 0:
        df = pd.DataFrame(st.session_state.alert_history)
        st.dataframe(df, use_container_width=True)
        st.caption(f"Events received: {len(st.session_state.alert_history)}")
        st.subheader("Latest Raw Event")
        st.json(st.session_state.alert_history[0])
    else:
        st.write("No incidents recorded yet.")

# Auto-refresh the dashboard every 2 seconds for data updates
placeholder = st.empty()
with placeholder.container():
    time.sleep(2)
    st.rerun()