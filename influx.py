from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import logging


class InfluxConnector:

    def __init__(self, bucket: str, token: str, org: str, url: str):
        self.bucket = bucket
        self.token = token
        self.org = org
        self.url = url
        logging.debug(f"Influx url: {self.url}")

    def __get_client(self) -> InfluxDBClient:
        return InfluxDBClient(url=self.url, token=self.token, org=self.org, debug=False)

    def add_samples(self, records, size: int) -> None:
        if size < 1:
            return

        logging.info(f"Importing {size} record(s) to influx")
        with self.__get_client() as client:
            with client.write_api() as write_api:
                write_api.write(bucket=self.bucket, record=records)
