import threading
import time
import logging
import queue
from .pcprox import open_pcprox

logger = logging.getLogger(__name__)

class RFIDProvider:
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.thread = None
        self.command_queue = queue.Queue()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def indicate_success(self):
        """Signal a successful operation (e.g. Green Flash)"""
        self.command_queue.put('success')

    def indicate_error(self):
        """Signal an error (e.g. Red Flash)"""
        self.command_queue.put('error')

    def _loop(self):
        # To be implemented by subclasses
        pass

class PcProxRFIDProvider(RFIDProvider):
    def _loop(self):
        reader = None
        last_tag = None
        
        while self.running:
            try:
                # 1. Connection Phase
                if reader is None:
                    try:
                        reader = open_pcprox()
                        logger.info("Connected to pcProx reader")
                        
                        # Initial Configuration
                        config = reader.get_config()
                        config.bHaltKBSnd = True      # Stop keystrokes (CRITICAL)
                        config.bAppCtrlsLED = True    # We control LEDs
                        config.iRedLEDState = True    # Red On (Ready)
                        config.iGrnLEDState = False   # Green Off
                        config.iBeeperState = False
                        
                        # Apply Config (Page 0 for HaltKB, Page 2 for LEDs)
                        config.set_config(reader, pages=[0, 2])
                        reader.end_config()
                        
                        # Verify HaltKB is set (read back to confirm)
                        verify_config = reader.get_config()
                        if not verify_config.bHaltKBSnd:
                            logger.warning("bHaltKBSnd not set properly, retrying...")
                            verify_config.bHaltKBSnd = True
                            verify_config.set_config(reader, pages=[0])
                            reader.end_config()
                        
                        logger.info("Reader configured: Keyboard output disabled")
                        
                    except Exception as e:
                        time.sleep(2)
                        continue

                # 2. Command Processing Phase
                # Handle queued feedback commands (Success/Error signals)
                while not self.command_queue.empty():
                    cmd = self.command_queue.get()
                    try:
                        config = reader.get_config()
                        # We only need to touch Page 2 for LEDs
                        
                        if cmd == 'success':
                            # Green Flash
                            config.iRedLEDState = False
                            config.iGrnLEDState = True
                            config.bAppCtrlsLED = True
                            config.set_config(reader, pages=[2])
                            reader.end_config()
                            
                            time.sleep(0.5)
                            
                            # Revert to Ready
                            config.iRedLEDState = True
                            config.iGrnLEDState = False
                            config.set_config(reader, pages=[2])
                            reader.end_config()
                            
                        elif cmd == 'error':
                            # Red Blink
                            for _ in range(3):
                                config.iRedLEDState = False
                                config.set_config(reader, pages=[2])
                                reader.end_config()
                                time.sleep(0.1)
                                
                                config.iRedLEDState = True
                                config.set_config(reader, pages=[2])
                                reader.end_config()
                                time.sleep(0.1)

                    except Exception as e:
                        logger.error(f"Error processing feedback command: {e}")
                        reader = None # Force reconnect logic if we lost device
                        break

                if reader is None: continue

                # 3. Polling Phase
                try:
                    result = reader.get_tag()
                    if result:
                        raw_data, bits = result
                        
                        if bits > 0 and len(raw_data) > 0:
                            # Big Endian Conversion
                            tag_id = raw_data[::-1].hex().upper()
                            
                            if tag_id != last_tag:
                                last_tag = tag_id
                                self.callback(tag_id)
                    else:
                        last_tag = None
                        
                    time.sleep(0.5) # Poll interval
                    
                except Exception as e:
                    logger.error(f"Error during read loop: {e}")
                    if reader:
                        try: reader.close()
                        except: pass
                    reader = None
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Unhandled error in RFID loop: {e}")
                time.sleep(1)
        
        # Cleanup on exit
        if reader:
            try:
                # Ideally restore defaults, but HaltKB might be preferred to stay
                config = reader.get_config()
                config.bAppCtrlsLED = False # Give back control
                config.set_config(reader, pages=[2])
                reader.end_config()
                reader.close()
            except:
                pass

class MockRFIDProvider(RFIDProvider):
    def _loop(self):
        logger.info("Started Mock RFID Provider")
        while self.running:
            while not self.command_queue.empty():
                cmd = self.command_queue.get()
                logger.info(f"Mock Feedback: {cmd.upper()}")
            time.sleep(0.1)

    def simulate_scan(self, tag_id):
        logger.info(f"Simulating scan: {tag_id}")
        self.callback(tag_id)

def get_rfid_provider(callback, use_mock=False):
    if use_mock:
        return MockRFIDProvider(callback)
    try:
        import hid
        return PcProxRFIDProvider(callback)
    except ImportError:
        logger.warning("HID library not found, falling back to mock.")
        return MockRFIDProvider(callback)
    except Exception as e:
        logger.warning(f"Failed to initialize real RFID provider ({e}), falling back to mock.")
        return MockRFIDProvider(callback)
