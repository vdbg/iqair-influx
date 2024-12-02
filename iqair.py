import random
import logging
import json
import time
import urllib.error
import urllib.request
import urllib.parse

# AQI API documentation is at https://api-docs.iqair.com/?version=latest


class Location:
    def __init__(self, name: str, conf: dict) -> None:
        self.name: str = name
        self.country: str = conf["country"]
        self.state: str = conf["state"]
        self.city: str = conf["city"]
        logging.debug(f"Loaded {self.name} with country={self.country}, state={self.state}, city={self.city}")


class IqAirConnector:
    def __init__(self, conf: dict) -> None:
        self._apikeys: list[str] = list(map(str.strip, conf["apikeys"]))
        self._api: str = conf["api"]
        self._measurement_pollution: str = conf["measurement_pollution"]
        self._measurement_weather: str = conf["measurement_weather"]
        self._throttle_retry_wait_seconds: int = conf["throttle_retry_wait_seconds"]
        self._throttle_retry_max_count: int = conf["throttle_retry_max_count"]
        self._throttle_count: int = 0
        if not self._measurement_weather and not self._measurement_pollution:
            logging.warning("Both measurement_pollution and measurement_weather aren't specified, therefore no records will be imported.")
        self._locations: list[Location] = [Location(name, data) for name, data in conf["locations"].items()]

    def __fetch_data(self, location: Location, apiKeys: list[str]) -> json:
        logging.debug(f"{len(apiKeys)} API key(s) available.")
        
        apiKey = random.choice(apiKeys)
        url = f"{self._api}/city?{urllib.parse.urlencode({'state': location.state, 'city' : location.city, 'country': location.country, 'key': apiKey})}"
        logging.debug(f"Request url: {url}")

        try:
            response = urllib.request.urlopen(url).read()
            self._throttle_count = 0
            return json.loads(response)
        except urllib.error.HTTPError as e:
            if e.status == 400:
                logging.error(f"Invalid request; possible reason: wrong location '{location.country}/{location.state}/{location.city}' specified.")
                exit(1)
            if e.status in [401, 403]:
                logging.error(f"Invalid API key '{apiKey}'. https://www.iqair.com/dashboard/api to retrieve one.")
                exit(1)
            if e.status == 404:
                logging.error("Invalid request; possible reason: API change.")
                exit(1)
            if e.status in [429, 402]:
                logging.warning(f"Being throttled with status {e.status} for API key {apiKey}. See README.md for options.")
                self._throttle_count += 1
                # if we have multiple keys, remove the throttled one from the list of candidates
                if len(apiKeys) > 1:
                    apiKeys.remove(apiKey)
                if self._throttle_count <= self._throttle_retry_max_count:
                    time.sleep(1+self._throttle_count*random.randint(1, self._throttle_retry_wait_seconds))
                    return self.__fetch_data(location, apiKeys)

            logging.error(f"Request to IqAir failed: {e.status}, {e.strerror}")
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
        apiKeys = list(self._apikeys)
        for location in self._locations:
            data = self.__fetch_data(location, apiKeys)
            if not data:
                continue
            status = data["status"]
            data = data["data"]
            if status != "success":
                logging.error(f"Unsuccessful call: {data['message']}")
                continue
            pollution = data["current"]["pollution"]
            weather = data["current"]["weather"]
            record = self.__construct_record(self._measurement_weather, location, data, weather)
            if record:
                record["fields"] = {
                    "temperature": weather['tp'],     # temperature in Celsius
                    "pressure": weather['pr'],        # atmospheric pressure in hPa
                    "humidity": weather['hu'],        # humidity in %
                    # The influxDB python library tries being smart which ends up hurting
                    # https://github.com/influxdata/influxdb-python/issues/572
                    "wind_speed": float(weather['ws']),  # wind speed in m/s
                    "wind_direction": weather['wd'],  # wind direction, as an angle of 360 (N=0, E=90, S=180, W=270)
                    "icon": weather['ic']             # weather icon. Can be retrieved at https://www.airvisual.com/images/<icon>.png
                }
                records.append(record)

            record = self.__construct_record(self._measurement_pollution, location, data, pollution)
            if record:
                record["fields"] = {
                    "aqi_us": pollution["aqius"],  # Air Quality Index value based on US EPA standard
                    "aqi_cn": pollution["aqicn"]   # Air Quality Index value based on China MEP standard
                }
                records.append(record)
        return records
