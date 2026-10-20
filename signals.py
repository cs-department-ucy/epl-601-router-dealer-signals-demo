import signal
import sys
import time

def signal_handler(sig, frame):
    print("\nCtrl+C detected but ignored...")

print("Program is running. Press Ctrl+C to stop.")
time.sleep(3)

previous_handler = signal.getsignal(signal.SIGINT)
signal.signal(signal.SIGINT, signal_handler)
print("Program is running. Ctrl+C does not stop process.")
time.sleep(3)

print("Program is running. Press Ctrl+C to stop.")
signal.signal(signal.SIGINT, previous_handler)
time.sleep(3)

