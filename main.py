import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD
import time
import requests
import signal
import sys

API_URL = "http://YOUR_BACKEND_IP:3000/api/log"
SHUTDOWN_URL = "http://YOUR_BACKEND_IP:3000/api/shutdown"

# Force BCM numbering so we don't conflict with RPLCD's setup
GPIO.setmode(GPIO.BCM)

# Initialize the LCD using GPIO parallel pins
lcd = CharLCD(
    pin_rs=7, pin_e=8, pins_data=[9, 10, 11, 12],
    numbering_mode=GPIO.BCM,
    cols=16, rows=2,
    dotsize=8
)

# Keypad setup (Using same BCM pins as before)
MATRIX = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]
ROW = [17, 27, 22, 23]
COL = [24, 25, 5, 6]

for j in range(4):
    GPIO.setup(COL[j], GPIO.OUT)
    GPIO.output(COL[j], 1)
for i in range(4):
    GPIO.setup(ROW[i], GPIO.IN, pull_up_down=GPIO.PUD_UP)

def graceful_exit(signum, frame):
    lcd.clear()
    lcd.write_string('Shutting down...')
    try:
        requests.post(SHUTDOWN_URL, timeout=3)
    except:
        pass
    lcd.clear()
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_exit)
signal.signal(signal.SIGINT, graceful_exit)

def read_keypad():
    for j in range(4):
        GPIO.output(COL[j], 0)
        for i in range(4):
            if GPIO.input(ROW[i]) == 0:
                time.sleep(0.2) # Debounce
                while GPIO.input(ROW[i]) == 0: pass
                GPIO.output(COL[j], 1)
                return MATRIX[i][j]
        GPIO.output(COL[j], 1)
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
