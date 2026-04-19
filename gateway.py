# gateway.py
import can
import paho.mqtt.client as mqtt
import json
import time

# Configuration
MQTT_BROKERS = ["broker.hivemq.com", "test.mosquitto.org"]
MQTT_TOPIC = "adas/alerts/company"
CAN_CHANNEL = 'test_channel'
RECONNECT_INTERVAL = 5  # seconds


class ADASGateway:
    def __init__(self):
        self.mqtt_connected = False
        self.can_connected = False
        
        # 1. Setup MQTT
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.setup_mqtt()

        # 2. Setup CAN
        self.setup_can()

    def setup_mqtt(self):
        """Setup MQTT connection with error handling."""
        for broker in MQTT_BROKERS:
            try:
                rc = self.client.connect(broker, 1883, 60)
                if rc == mqtt.MQTT_ERR_SUCCESS:
                    self.client.loop_start()
                    self.mqtt_connected = True
                    print(f"Gateway: MQTT connected to {broker}")
                    return
            except Exception:
                continue
        self.mqtt_connected = False
        print("Gateway: MQTT connection failed on all brokers")

    def setup_can(self):
        """Setup CAN connection with error handling."""
        try:
            self.bus = can.interface.Bus(interface='virtual', channel=CAN_CHANNEL)
            self.can_connected = True
            print(f"Gateway: Listening to CAN channel {CAN_CHANNEL}...")
        except Exception as e:
            print(f"Gateway: CAN Error: {e}")
            self.can_connected = False
            self.bus = None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Gateway: Connected to MQTT Broker")
            self.mqtt_connected = True
            client.subscribe(MQTT_TOPIC)
        else:
            print(f"Gateway: MQTT Connection failed with code {rc}")
            self.mqtt_connected = False

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"Gateway: Unexpected MQTT disconnection ({rc})")
            self.mqtt_connected = False

    def run(self):
        if not self.can_connected:
            print("Gateway: Cannot run without CAN connection")
            return

        try:
            while True:
                if not self.bus:
                    time.sleep(1)
                    continue
                    
                try:
                    message = self.bus.recv(1.0)  # Wait for 1 second
                    if message is not None:
                        self.process_can_message(message)
                except can.CanError as e:
                    print(f"Gateway: CAN receive error: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("Gateway shutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Safely close connections."""
        try:
            self.client.loop_stop()
        except:
            pass
        try:
            if self.bus:
                self.bus.shutdown()
        except:
            pass

    def process_can_message(self, msg):
        """Process incoming CAN messages."""
        try:
            # Logic: If ID is 0x101 (Alert Status)
            if msg.arbitration_id == 0x101:
                status = "DANGER" if msg.data[0] == 1 else "SAFE"
                
                # Create a JSON payload for the company
                payload = {
                    "event": "Alert Update",
                    "status": status,
                    "timestamp": str(time.time())
                }
                
                if self.mqtt_connected:
                    self.client.publish(MQTT_TOPIC, json.dumps(payload))
                    print(f"Gateway: Published to MQTT: {payload}")
                else:
                    print(f"Gateway: MQTT not connected. Alert not sent.")

            # Logic: If ID is 0x100 (Object Type)
            elif msg.arbitration_id == 0x100:
                if len(msg.data) > 0:
                    obj_char = chr(msg.data[0]) if msg.data[0] < 128 else '?'
                    print(f"Gateway: Detected Object: {obj_char}")
        except Exception as e:
            print(f"Gateway: Error processing CAN message: {e}")


if __name__ == "__main__":
    gateway = ADASGateway()
    gateway.run()