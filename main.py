import pigpio
from RPLCD.pigpio import CharLCD
import time
import requests
import signal
import sys

API_URL = "http://YOUR_BACKEND_IP:3000/api/log"
SHUTDOWN_URL = "http://YOUR_BACKEND_IP:3000/api/shutdown"

# Connect to local pigpio daemon
pi = pigpio.pi()
if not pi.connected:
    print("Error: pigpio daemon not running. Run 'sudo systemctl start pigpiod'")
    sys.exit(1)

# Initialize the LCD using the pigpio backend and standard BCM pins
lcd = CharLCD(
    pi,
    pin_rs=17, pin_e=27, pins_data=[22, 23, 24, 25],
    cols=16, rows=2,
    dotsize=8
)

# Keypad setup using standard BCM pins
MATRIX = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]
ROW = [5, 6, 13, 19]
COL = [26, 12, 16, 20]

for j in range(4):
    pi.set_mode(COL[j], pigpio.OUTPUT)
    pi.write(COL[j], 1)
for i in range(4):
    pi.set_mode(ROW[i], pigpio.INPUT)
    pi.set_pull_up_down(ROW[i], pigpio.PUD_UP)

def graceful_exit(signum, frame):
    lcd.clear()
    lcd.write_string('Shutting down...')
    try:
        requests.post(SHUTDOWN_URL, timeout=3)
    except:
        pass
    lcd.clear()
    lcd.close() # Clean up RPLCD pigpio instance
    pi.stop()   # Disconnect from daemon
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_exit)
signal.signal(signal.SIGINT, graceful_exit)

def read_keypad():
    for j in range(4):
        pi.write(COL[j], 0)
        for i in range(4):
            if pi.read(ROW[i]) == 0:
                time.sleep(0.2) # Debounce
                while pi.read(ROW[i]) == 0: pass
                pi.write(COL[j], 1)
                return MATRIX[i][j]
        pi.write(COL[j], 1)
    return None

def main():
    current_input = ""
    lcd.clear()
    lcd.write_string('Enter ENR:')
    
    while True:
        key = read_keypad()
        if key:
            if key == '#': # Enter
                lcd.clear()
                lcd.write_string('Processing...')
                try:
                    res = requests.post(API_URL, json={"enr": current_input}, timeout=5)
                    msg = res.json().get('message', 'Success')
                    lcd.clear()
                    lcd.write_string(msg)
                except requests.exceptions.RequestException:
                    lcd.clear()
                    lcd.write_string('Network Error!')
                
                time.sleep(2)
                current_input = ""
                lcd.clear()
                lcd.write_string('Enter ENR:')
            
            elif key == '*': # Backspace/Clear
                current_input = ""
                lcd.clear()
                lcd.write_string('Enter ENR:')
            
            else:
                current_input += key
                lcd.cursor_pos = (1, 0)
                lcd.write_string(current_input)
        time.sleep(0.05)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        graceful_exit(None, None)
