import logging
import json
import urllib.error
import urllib.request
import urllib.parse

# AQI API documentation is at https://api-docs.iqair.com/?version=latest


class Location:
    def __init__(self, name: str, conf: dict) -> None:
        self.name = name
        self.country = conf["country"]
        self.state = conf["state"]
        self.city = conf["city"]
        logging.debug(f"Loaded {self.name} with country={self.country}, state={self.state}, city={self.city}")


class IqAirConnector:
    def __init__(self, conf: dict) -> None:
        self.apikey: str = conf["apikey"]
        self.api = conf["api"]
        self.measurement_pollution: str = conf["measurement_pollution"]
        self.measurement_weather: str = conf["measurement_weather"]
        if not self.measurement_weather and not self.measurement_pollution:
            logging.warn("Both measurement_pollution and measurement_weather aren't specified, therefore no records will be imported.")
        self.locations: list[Location] = [Location(name, data) for name, data in conf["locations"].items()]

    def __fetch_data(self, location: Location) -> json:
        url = f"{self.api}/city?{urllib.parse.urlencode({'state': location.state, 'city' : location.city, 'country': location.country, 'key': self.apikey})}"
        logging.debug(f"url: {url}")

        try:
            response = urllib.request.urlopen(url).read()
            return json.loads(response)
        except urllib.error.HTTPError as e:
            logging.error(f"Request to IqAir failed: {e.status}, {e.strerror}")
            if e.status == 400:
                logging.error("Invalid request; possible reason: wrong location specified.")
                exit(1)
            if e.status == 401:
                logging.error("Invalid API key. https://www.iqair.com/dashboard/api to retrieve one.")
                exit(1)
            if e.status == 404:
                logging.error("Invalid request; possible reason: API change.")
                exit(1)
            if e.status == 429:
                logging.warn("Being throttled. Increase value of main.loop_seconds in config.yaml if non-zero.")
            return None

    def __construct_record(self, measurement: str, location: Location, data: dict, measurement_data: dict) -> dict:
        if not measurement:
            return None
        return {
            "measurement": measurement,
            "tags": {"location": location.name, "city": data["city"], "state": data["state"], "country": data["country"]},
            "time": measurement_data["ts"]
        }

    def fetch_data(self) -> list:
        records = []
        for location in self.locations:
            data = self.__fetch_data(location)
            if not data:
                continue
            status = data["status"]
            data = data["data"]
            if status != "success":
                logging.error(f"Unsuccessful call: {data['message']}")
                continue
            pollution = data["current"]["pollution"]
            weather = data["current"]["weather"]
            record = self.__construct_record(self.measurement_weather, location, data, weather)
            if record:
                record["fields"] = {
                    "temperature": weather['tp'],     # temperature in Celsius
                    "pressure": weather['pr'],        # atmospheric pressure in hPa
                    "humidity": weather['hu'],        # humidity in %
                    "wind_speed": weather['ws'],      # wind speed in m/s
                    "wind_direction": weather['wd'],  # wind direction, as an angle of 360 (N=0, E=90, S=180, W=270)
                    "icon": weather['ic']             # weather icon. Can be retrieved at https://www.airvisual.com/images/<icon>.png
                }
                records.append(record)

            record = self.__construct_record(self.measurement_pollution, location, data, pollution)
            if record:
                record["fields"] = {
                    "aqi_us": pollution["aqius"],  # Air Quality Index value based on US EPA standard
                    "aqi_cn": pollution["aqicn"]   # Air Quality Index value based on China MEP standard
                }
                records.append(record)
        return records
