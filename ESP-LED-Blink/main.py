



import time
from machine import Pin



def loop():
    while True:
        led.value(1)
        time.sleep(1)
        print('Les is on...')
        led.value(0)
        time.sleep(1)
        print('Les is off...')


led = Pin(32, Pin.OUT)
loop()