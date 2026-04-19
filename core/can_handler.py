# core/can_handler.py
import can
import time

class CANBusSimulator:
    def __init__(self, interface='virtual', channel='test_channel'):
        """
        Initializes the virtual CAN bus.
        'virtual' interface allows testing without physical hardware.
        """
        try:
            self.bus = can.interface.Bus(interface=interface, channel=channel)
            print(f"CAN Bus initialized on {channel} ({interface})")
        except Exception as e:
            print(f"Failed to initialize CAN Bus: {e}")
            self.bus = None

    def send_alert(self, object_type, status):
        """
        Sends an alert message over the CAN bus.
        CAN ID 0x101: Alert Status (0 for Safe, 1 for Danger)
        CAN ID 0x100: Object Detection (Data contains object type index)
        """
        if not self.bus:
            return
        
        # Validate inputs
        if not object_type or not isinstance(object_type, str):
            print("Warning: Invalid object_type. Using default.")
            object_type = "Unknown"

        # Status: 1 for Danger, 0 for Safe. Accept values like "DANGER: Approaching".
        normalized_status = str(status).strip().upper()
        status_val = 1 if normalized_status.startswith('DANGER') else 0
        
        # 1. Send Alert Status (ID 0x101)
        msg_status = can.Message(
            arbitration_id=0x101,
            data=[status_val],
            is_extended_id=False
        )
        
        # 2. Send Object Type (ID 0x100) 
        # For simplicity, we'll send the first byte as an encoded type or ID
        # In a real system, this would be a structured protocol
        msg_data = can.Message(
            arbitration_id=0x100,
            data=[ord(object_type[0])], # Just sending first char for simulation
            is_extended_id=False
        )

        try:
            self.bus.send(msg_status)
            self.bus.send(msg_data)
            print(f"CAN Sent: Alert={status}, Object_Char={object_type[0]}")
        except can.CanError as e:
            print(f"CAN Error: {e}")

    def close(self):
        if self.bus:
            self.bus.shutdown()
