import urequests as requests
import ujson as json
import time
import network
from time import sleep, ticks_ms, sleep_ms
import gc
import uzlib
from io import BytesIO
import ntptime
import machine
from machine import Pin, I2C, PWM
import ssd1306
import _thread as th
from font import Font
#import keys_info
try:
    import keys_info
    print('found local keys')
    keys_ = keys_info.keys
    google_translate_key = keys_info.google_translate_key
except:
    print('oops')
    keys_ = {'SSID1': '*****',
            'SSID2': '*****'
            } # Your wifi keys
    google_translate_key = 'Your_Google_Translate _API key'
#from data import locations

boot = Pin(0, Pin.IN)
led = Pin(19, Pin.OUT)
buzzer_pin = Pin(23, Pin.OUT)
buzzer_pwm = PWM(buzzer_pin)
button = Pin(4, Pin.IN, Pin.PULL_UP)

i2c = I2C(scl=Pin(22), sda=Pin(21), freq=4000000) 
display = ssd1306.SSD1306_I2C(128, 64, i2c)  # display object
f=Font(display)

def buzz(duration_ms, frequency):
    buzzer_pwm.freq(frequency)  # Set the PWM frequency
    buzzer_pwm.duty(512)        # Set the PWM duty cycle (50% for a beep)
    sleep_ms(duration_ms)
    buzzer_pwm.duty(0)

buzz(500, 880)

def blink():
    led.value(1)
    sleep_ms(20)
    led.value(0)
    
blink()

def check_alive():
    while True:
        blink()
        sleep(10)

th.start_new_thread(check_alive, ())


# translat functions. 
def urlencode(data):
    """URL encode a dictionary of data."""
    return "&".join(f"{k}={uquote(v)}" for k, v in data.items())

def uquote(string):
    """Manually URL quote a string."""
    # For our use case, just replacing spaces; can be extended for other characters
    return string.replace(" ", "%20")

def connect():
    # keys_ hold the wifi keys

    station = network.WLAN(network.STA_IF)
    sleep(0.2)
    station.active(True)
    stat = station.scan()
    best_ap = (None,0,0,-100)
    #print(stat)
    SSID = ''
    for s in stat:
        #print(s)
        check = s[0].decode('utf-8')
        if check in keys_.keys() and s[3] > best_ap[3]:
            #print('Im in')
            best_ap = s
            print(f'The best Access Point found is {best_ap[0]}')
            SSID = best_ap[0].decode('utf-8')

    if best_ap[0] != None:
        print(1)
        print(f'SSID {SSID} {keys_[SSID]}')
        station.connect(SSID, keys_[SSID])
        while station.isconnected() == False:
            sleep(1)
            pass
        print(f'Connected to {SSID}')
        return SSID
    else:
        print('Did not connect')
    
    return 'No Internet'

class RedAlert():

    def __init__(self):
        # initialize locations list
        # self.locations = self.get_locations_list()
        # cookies
        self.cookies = ""
        # initialize user agent for web requests
        self.headers = {
           "Host":"www.oref.org.il",
           "Connection":"close", #changed
           "Content-Type":"application/json",
           "charset":"utf-8",
           "X-Requested-With":"XMLHttpRequest",
           "sec-ch-ua-mobile":"?0",
           "User-Agent":"",
           "sec-ch-ua-platform":"macOS",
           "Accept":"*/*", # changed
           "sec-ch-ua": '".Not/A)Brand"v="99", "Google Chrome";v="103", "Chromium";v="103"',
           "Sec-Fetch-Site":"same-origin",
           "Sec-Fetch-Mode":"cors",
           "Sec-Fetch-Dest":"empty",
           "Referer":"https://www.oref.org.il/12481-he/Pakar.aspx",
           "Accept-Encoding":"gzip, deflate, br",
           "Accept-Language":"en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        }
        # intiiate cokies
        #self.get_cookies()
        self.TLA = 'Nope'
        self.other = ''
        self.time_stamp = ''

    def get_red_alerts(self):

        URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
        try:
            r = requests.get(URL, headers=self.headers)

            if r.status_code != 200:
                print(f"HTTP error. Status code: {r.status_code}")
                return {'title': 'No alerts on 1'}

        except Exception as e:
            print(f"Network or request error: {e}")
            return {'title': 'No alerts on 2'}

        decompressor = uzlib.DecompIO(BytesIO(r.content), 31)  # 31 is the gzip window size
        decompressed_data = decompressor.read()

        alerts = decompressed_data.decode('utf-8-sig').strip()  # 'utf-8-sig' will automatically remove BOM if it exists
        print(alerts)
        alerts = alerts.replace('\ufeff', '')
        self.debug1 = alerts

        if len(alerts) <= 1: 
            alerts = {'title': 'No alerts on 3'}
        else:
            try:
                alerts = json.loads(alerts)
            except ValueError:
                print("Error parsing JSON")
                alerts = {'title': 'No alerts on 4'}

        return alerts
    
    def check_alerts(self, alarm):
        print('checking')
        print(alarm)
        try:
            print(alarm['title'])
            print(alarm['data'])
        except:
            pass
        for site in alarm['data']:
            print(site)
            if ("תל אביב" in site):
                self.TLA = 'Tel Aviv'
                for n in range(20):
                    buzz(500, 880)
                    sleep(0.2)
                    buzz(800, 1200)
                    sleep(0.1)
        # check whwre alarm has been:
        
        self.other = alarm['data'][0]
        self.time_stamp = print_time()

        url = "https://google-translate1.p.rapidapi.com/language/translate/v2/detect"

        payload = {"q": self.other, "target": "en",	"source": "he" }
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "application/gzip",
            "X-RapidAPI-Key": google_translate_key,
            "X-RapidAPI-Host": "google-translate1.p.rapidapi.com"
        }

        # Convert the payload dictionary to a URL-encoded byte string
        data = urlencode(payload).encode('utf-8')

        response = requests.post(url, data=data, headers=headers)

        #self.other = 'eee'
        print(response.json())


def print_time():
    dt = rtc.datetime()
    # adjust to Israel:
    year, month, day, _, hour, minute, second, _ = dt
    dst_start = (year, 3, (31 - (5 + year * 5 // 4) % 7), 2)  # Friday before last Sunday in March at 2am
    dst_end = (year, 10, (31 - (2 + year * 5 // 4) % 7), 2)  # Last Sunday in October at 2am
    is_dst = dst_start <= (year, month, day, hour) < dst_end

    # Adjust for timezone and DST
    hour += 2 + is_dst  # UTC+2 for IST and +1 for DST

    # Handle overflow
    if hour >= 24:
        hour -= 24
        day += 1
        # Handle day overflow for each month
        if month in [4, 6, 9, 11] and day > 30 or month == 2 and (day > 29 or (year % 4 != 0 or (year % 100 == 0 and year % 400 != 0)) and day > 28) or day > 31:
            day = 1
            month += 1
            if month > 12:
                month = 1
                year += 1

    dt = (year, month, day, hour, minute, second)
    return ("{:02d}:{:02d}:{:02d}".format(dt[3], dt[4], dt[5]))



# ******************************************************

SSID = connect()
ntptime.settime()  # This will set the board's RTC using an NTP server
rtc = machine.RTC()
alert = RedAlert()

gc.collect()






while True:
    display.fill(0)
    if not boot.value():
        break
    time = print_time()
    print(time)
    display.text(time, 0, 0, 1)
    display.text(f'Wifi: {SSID}', 0, 15 ,1)
    display.text(f'TLA: {alert.TLA}', 0, 30, 1)
    display.text(f'> {alert.other}', 0, 45, 1)
    #display.text("בקעה", 0, 45, 1)
    display.text(f'> {alert.time_stamp}', 0, 55, 1)
    
    alarm = alert.get_red_alerts()
    print(f'{alarm} \nType is: {type(alarm)}')
    try:
        if alarm['id']:
            alert.check_alerts(alarm)
    except:
        pass

    display.show()
    sleep(1)
