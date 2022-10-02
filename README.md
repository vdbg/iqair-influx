# iqair-influx
Import air quality data from  to InfluxDB

Allows for importing data from [IQAir](https://www.iqair.com/) to [InfluxDB](https://www.influxdata.com/) v2.


## Requirements

- An [IQAir API Key](https://www.iqair.com/dashboard/api).
- A device with either [Docker](https://www.docker.com/) or Python 3.7 or later installed.
- [InfluxDB](https://en.wikipedia.org/wiki/InfluxDB) v2 installed on this device or another device, and a bucket created in influxDB.

## Setup

### With Docker

Dependency: Docker installed.
. 
2. Download and run the Docker image: `sudo docker run --name iqair -v config.yaml:/app/config.yaml vdbg/iqair-influx:latest`
3. Copy the template config file from the image: `sudo docker cp iqair:/app/template.config.yaml config.yaml`
4. Edit `config.yaml` by following the instructions in the file
5. Start the container again to verify the settings are correct: `sudo docker start iqair -i`
6. Once the settings are finalized, `Ctrl-C` to stop the container, `sudo docker container rm iqair` to delete it
7. Start the container with final settings:

``
sudo docker run \
  -d \
  --name iqair \
  -v /path_to_your/config.yaml:/app/config.yaml \
  --memory=100m \
  --pull=always \
  --restart=always \
  vdbg/iqair-influx:latest
``

### Without Docker

Dependency: Python3 and pip3 installed. `sudo apt-get install python3-pip` if missing on raspbian.

1. Git clone this repository and cd into directory
2. `cp template.config.yaml config.yaml`
3. Edit file `config.yaml` by following the instructions in the file
4. `pip3 install -r requirements.txt`
5. `python3 main.py` or `./main.py`


## Air Quality Index explained

The US and CN threseholds are both listed on [Wikipedia](https://en.wikipedia.org/wiki/Air_quality_index#United_States).
