from __future__ import print_function, division
from RPi import GPIO
import Adafruit_DHT
import sqlite3 as sqlite
from datetime import datetime
from time import sleep, time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

db = sqlite.connect("/home/pi/db/greenhouse.db")
cursor = db.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS
        greenhouse (
            datetime TEXT,
            temperature REAL,
            humidity REAL,
            soil REAL,
            light REAL
        )
""")
db.commit()


class Greenhouse(object):
    LEDS = {
        'white': [13, 9, 27],
        'red': [16, 11, 23],
        'blue': [20, 6, 22],
        'green': [21, 12, 25],
    }

    DHT_SENSOR = Adafruit_DHT.DHT22
    DHT = 19
    SOIL = 26
    LIGHT = 18

    SENSOR_LOW = -1
    SENSOR_OK = 0
    SENSOR_HIGH = 1

    target_temperature_lower = 20
    target_temperature_upper = 30

    target_humidity_lower = 40
    target_humidity_upper = 60

    target_light = 60

    @property
    def temperature_status(self):
        lower = self.target_temperature_lower
        upper = self.target_temperature_upper

        if lower <= self.temperature <= upper:
            return self.SENSOR_OK
        elif self.temperature < lower:
            return self.SENSOR_LOW
        elif self.temperature > higher:
            return self.SENSOR_HIGH

    @property
    def humidity_status(self):
        lower = self.target_humidity_lower
        upper = self.target_humidity_upper

        if lower <= self.humidity <= upper:
            return self.SENSOR_OK
        elif self.humidity < lower:
            return self.SENSOR_LOW
        elif self.humidity > upper:
            return self.SENSOR_HIGH

    @property
    def soil_status(self):
        if self.soil:
            return self.SENSOR_OK
        else:
            return self.SENSOR_LOW

    @property
    def light_status(self):
        if self.light >= self.target_light:
            return self.SENSOR_OK
        else:
            return self.SENSOR_LOW

    def __init__(self):
        self._setup_gpio()
        self._init_sensors()

    def _setup_gpio(self):
        for colour in self.LEDS:
            for led in self.LEDS[colour]:
                GPIO.setup(led, GPIO.OUT)
                GPIO.output(led, False)

    def _init_sensors(self):
        self._get_humidity_and_temperature()
        self.get_soil()
        self.get_light()

    def _turn_led_on_or_off(self, colour, index, on_or_off):
        led = self.LEDS[colour][index]
        GPIO.output(led, on_or_off)

    def _turn_colour_leds_on_or_off(self, colour, on_or_off):
        leds = self.LEDS[colour]
        for led in range(len(leds)):
            if on_or_off:
                self.turn_led_on(colour, led)
            else:
                self.turn_led_off(colour, led)

    def _turn_all_leds_on_or_off(self, on_or_off):
        for colour in self.LEDS:
            if on_or_off:
                self.turn_colour_leds_on(colour)
            else:
                self.turn_colour_leds_off(colour)

    def _get_humidity_and_temperature(self):
        humidity, temperature = Adafruit_DHT.read_retry(
            sensor=self.DHT_SENSOR,
            pin=self.DHT,
            retries=5
        )
        self.humidity = humidity
        self.temperature = temperature
        return (humidity, temperature)

    def _get_soil_moisture(self):
        pin = self.SOIL
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
        sleep(0.1)
        GPIO.setup(pin, GPIO.IN)

        start_time = time()
        end_time = time()
        while GPIO.input(pin) == GPIO.LOW:
            end_time = time()
            if (end_time - start_time) > 1:
                end_time = start_time + 1
                break

        value = 100 * (1 - (end_time - start_time))
        return value

    def _get_light_level(self):
        pin = self.LIGHT
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
        sleep(0.1)
        GPIO.setup(pin, GPIO.IN)
        start_time = time()
        while GPIO.input(pin) == GPIO.LOW:
            end_time = time()
            if ((end_time - start_time) * 10000) > 100:
                return 0
        end_time = time()
        return 100 - ((end_time - start_time) * 10000)

    def _get_average_soil_moisture(self, num):
        values = [self._get_soil_moisture() for n in range(num)]
        average_value = sum(values) / len(values)
        return average_value

    def _get_average_light_level(self, num):
        values = [self._get_light_level() for n in range(num)]
        average_value = sum(values) / len(values)
        return average_value

    def turn_led_on(self, colour, index):
        """
        Turn a single LED on, by colour and index

        e.g. turn_led_on('red', 0)
        """
        self._turn_led_on_or_off(colour, index, on_or_off=True)

    def turn_led_off(self, colour, index):
        """
        Turn a single LED off, by colour and index

        e.g. turn_led_off('red', 0)
        """
        self._turn_led_on_or_off(colour, index, on_or_off=False)

    def turn_colour_leds_on(self, colour):
        """
        Turn all LEDs of a particular colour on

        e.g. turn_colour_leds_on('red')
        """
        self._turn_colour_leds_on_or_off(colour, on_or_off=True)

    def turn_colour_leds_off(self, colour):
        """
        Turn all LEDs of a particular colour off

        e.g. turn_colour_leds_off('red')
        """
        self._turn_colour_leds_on_or_off(colour, on_or_off=False)

    def turn_all_leds_on(self):
        """
        Turn all LEDs on
        """
        self._turn_all_leds_on_or_off(on_or_off=True)

    def turn_all_leds_off(self):
        """
        Turn all LEDs off
        """
        self._turn_all_leds_on_or_off(on_or_off=False)

    def get_temperature(self):
        """
        Return temperature value from sensor, in degrees Celsius

        (use self.temperature for cached value)
        """
        humidity, temperature = self._get_humidity_and_temperature()
        self.temperature = temperature
        return temperature

    def get_humidity(self):
        """
        Return humidity value from sensor, in percentage

        (use self.humidity for cached value)
        """
        humidity, temperature = self._get_humidity_and_temperature()
        self.humidity = humidity
        return humidity

    def get_soil(self):
        """
        Return soil moisture value from sensor, in percentage

        (use self.soil for cached value)
        """
        soil = self._get_average_soil_moisture(5)
        self.soil = soil > 50
        return self.soil

    def get_light(self):
        """
        Return light value from sensor, in percentage

        (use self.light for cached value)
        """
        self.light = self._get_average_light_level(5)
        return self.light

    def record_sensor_values(self):
        """
        Save sensor readings to database
        """
        timestamp = datetime.now().isoformat()
        temperature = self.temperature
        humidity = self.humidity
        soil = "%0.6d" % self.soil
        light = self.light

        values = (timestamp, temperature, humidity, soil, light)
        cursor.execute("""
            INSERT INTO greenhouse
            VALUES (?, ?, ?, ?, ?)
        """, values)
        db.commit()

    def export_to_csv(self, file_path):
        """
        Export sensor data from database and save as CSV file in file_path
        """
        cursor.execute("SELECT * from greenhouse")
        results = cursor.fetchall()
        with open(file_path, 'w') as f:
            for result in results:
                for data in result:
                    f.write('%s,' % data)
                f.write('\n')


def main():
    greenhouse = Greenhouse()
    greenhouse.record_sensor_values()
    greenhouse.export_to_csv('/home/pi/test.csv')
    print("Temperature: %f" % greenhouse.temperature)
    print("Humidity: %f" % greenhouse.humidity)
    print("Soil: %s" % greenhouse.soil)
    print("Light: %f" % greenhouse.light)

    if greenhouse.temperature_status == greenhouse.SENSOR_OK:
        print("Temperature ok")
    elif greenhouse.temperature_status == greenhouse.SENSOR_LOW:
        print("Temperature too low")
    elif greenhouse.temperature_status == greenhouse.SENSOR_HIGH:
        print("Temperature too high")

    if greenhouse.humidity_status == greenhouse.SENSOR_OK:
        print("Humidity ok")
    elif greenhouse.humidity_status == greenhouse.SENSOR_LOW:
        print("Humidity too low")
    elif greenhouse.humidity_status == greenhouse.SENSOR_HIGH:
        print("Humidity too high")

    if greenhouse.soil_status == greenhouse.SENSOR_OK:
        print("Soil ok")
    else:
        print("Soil too dry")

    if greenhouse.light_status == greenhouse.SENSOR_OK:
        print("Light ok")
    else:
        print("Light not ok")

    while True:
        for colour in greenhouse.LEDS:
            greenhouse.turn_colour_leds_on(colour)
            sleep(1)
            greenhouse.turn_all_leds_off()
            sleep(1)

if __name__ == '__main__':
    main()
