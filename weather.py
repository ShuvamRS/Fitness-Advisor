from pyowm import OWM
from geocoder import ip
from datetime import datetime

class Weather:
	def __init__(self, API_key):
		self.owm = OWM(API_key)
		self.location = ip('me').address # Gets client's address (city, state, country)


	def current_weather(self, unit='fahrenheit'):
		obs = self.owm.weather_at_place(self.location) # Observation object
		w = obs.get_weather() # Weather object from observation

		return {
			'cloud_coverage': w.get_clouds(),
			'rain_volume': w.get_rain(),
			'snow_volume': w.get_snow(),
			'wind_degree_and_speed': w.get_wind(),
			'humidity_percent': w.get_humidity(),
			'atmospheric_pressure': w.get_pressure(),
			'temperature': w.get_temperature(unit=unit),
			'short_weather_status': w.get_status(),
			'detailed_weather_status': w.get_detailed_status(),
			'weather_icon_url':  w.get_weather_icon_url(),
			'sunrise_time': str(datetime.fromtimestamp(int(w.get_sunrise_time()))),
			'sunset_time': str(datetime.fromtimestamp(int(w.get_sunset_time())))
		}


	def three_hours_forecast(self):
		fc = self.owm.three_hours_forecast(self.location)
		return {
			'will_have_rain': fc.will_have_rain(),
			'will_have_fog': fc.will_have_fog(),
			'will_have_clouds': fc.will_have_clouds(),
			'will_have_snow': fc.will_have_snow()
		}