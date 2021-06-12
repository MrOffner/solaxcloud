# Library imports
import json
import requests
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from datetime import datetime

from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.components.sensor import PLATFORM_SCHEMA

# Frequency of data retrieval (API allows for a maximum of 10 calls per minute)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

CONF_NAME = "name"
CONF_API_KEY = "api_key"
CONF_SN = "sn"
CONF_HAS_BATTERY = "battery"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_SN): cv.string,
        vol.Optional(CONF_HAS_BATTERY, default=False): bool
    }
)

# Set up the SolaxCloud platform
def setup_platform(hass, config, add_entities, discovery_info=None):
    solax_cloud = SolaxCloud(
        hass, config[CONF_NAME], config[CONF_API_KEY], config[CONF_SN], config[CONF_HAS_BATTERY])
    # Add the sensors to the platform
    add_entities([YieldTodaySensor(hass, solax_cloud),
                  YieldTotalSensor(hass, solax_cloud),
                  FeedinPowerSensor(hass, solax_cloud),
                  FeedinEnergySensor(hass, solax_cloud),
                  ConsumeEnergySensor(hass, solax_cloud),
                  FeedinPowerM2Sensor(hass, solax_cloud),
                  InverterTypeSensor(hass, solax_cloud),
                  InverterStatusSensor(hass, solax_cloud),
                  UpdateTimeSensor(hass, solax_cloud),
                  PowerDC1Sensor(hass, solax_cloud),
                  PowerDC2Sensor(hass, solax_cloud),
                  ], True)

    # Only add the battery sensors if user indicates that have storage available
    if (config[CONF_HAS_BATTERY]):
        add_entities([ACPowerSensor(hass, solax_cloud),
                      SocSensor(hass, solax_cloud),
                      Peps1Sensor(hass, solax_cloud),
                      Peps2Sensor(hass, solax_cloud),
                      Peps3Sensor(hass, solax_cloud),
                      BatPowerSensor(hass, solax_cloud),
                      ], True)

# Dictionary table that converts Inverter Type Code into Inverter Type (Table 4)
def inverter_type(code):
    switch = {
        '1'  : 'X1-LX',
        '2'  : 'X-Hybrid',
        '3'  : 'X1-Hybrid/Fit',
        '4'  : 'X1-Boost/Air/Mini',
        '5'  : 'X3-Hybrid/Fit',
        '6'  : 'X3-20K/30K',
        '7'  : 'X3-MIC/PRO',
        '8'  : 'X1-Smart',
        '9'  : 'X1-AC',
        '10' : 'A1-Hybrid',
        '11' : 'A1-Grid',
        '12' : 'J1-ESS'
    }
    return 'Unknown' if code not in switch else switch.get(code, 1)

# Dictionary table that converts Status Code into Inverter Status (Table 5)
def inverter_status(code):
    switch = {
        '100' : 'Wait Mode',
        '101' : 'Check Mode',
        '102' : 'Normal Mode',
        '103' : 'Fault Mode',
        '104' : 'Permanent Fault Mode',
        '105' : 'Update Mode',
        '106' : 'EPS Check Mode',
        '107' : 'EPS Mode',
        '108' : 'Self-Test Mode',
        '109' : 'Idle Mode',
        '110' : 'Standby Mode',
        '111' : 'Pv Wake Up Bat Mode',
        '112' : 'Gen Check Mode',
        '113' : 'Gen Run Mode'
    }
    return 'Unknown' if code not in switch else switch.get(code, 1)

class SolaxCloud:
    def __init__(self, hass, name, api_key, sn):
        self.hass = hass
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.sn = sn
        self.inverter_name = name
        self.data = {}
        self.uri = f'https://www.solaxcloud.com:9443/proxy/api/getRealtimeInfo.do?tokenId={api_key}&sn={sn}'
        self.last_data_time = None

    # Retrieve data from API access point
    def get_data(self):
        # If there is no data, or the data needs to be updated
        if not self.data or datetime.now() - self.last_data_time > MIN_TIME_BETWEEN_UPDATES:
            try:
                data = requests.get(self.uri).json()
                if data['success'] == True:
                    self.data = data['result']
                    self.last_data_time = datetime.now()
                    self.logger.info(
                        f'Retrieved new data from SolaxCloud {self.inverter_name}')
                else:
                    self.data = {}
                    self.logger.error(data['exception'])
            except requests.exceptions.ConnectionError as e:
                self.logger.error(str(e))
                self.data = {}


# Each sensor class is named using the convention: {API items}Sensor
# This comes from Table 3 of the API documentation

# Inverter.AC.power.total
class ACPowerSensor(Entity):
    # The current amount of solar generation (in watts)
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' Current Yield'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('acpower')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'W'

    @property
    def icon(self):
        return 'mdi:solar-power'

    @property
    def friendly_name(self):
        return 'Current Solar Generation'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter.AC.energy.out.daily
class YieldTodaySensor(Entity):
    # The amount of solar generation today (in kilowatts)
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' Daily Yield'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('yieldtoday')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'kWh'

    @property
    def icon(self):
        return 'mdi:solar-power'

    @property
    def friendly_name(self):
        return 'Daily Solar Yield'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter.AC.energy.out.total
class YieldTotalSensor(Entity):
    # The total lifetime solar generation (in kilowatts)
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' Total Yield'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('yieldtotal')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'kWh'

    @property
    def icon(self):
        return 'mdi:solar-power'

    @property
    def friendly_name(self):
        return 'Lifetime Solar Yield'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Grid.power.total
class FeedinPowerSensor(Entity):
    # ?? Current energy usage (in watts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' Grid Power Total'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('feedinpower')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'W'

    @property
    def icon(self):
        return 'mdi:transmission-tower'

    @property
    def friendly_name(self):
        return 'Current Energy Usage'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Grid.energy.toGrid.total
class FeedinEnergySensor(Entity):
    # ?? Amount of energy sent out to the main grid (in kilowatts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' To Grid Yield'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('feedinenergy')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'kWh'

    @property
    def icon(self):
        return 'mdi:transmission-tower'

    @property
    def friendly_name(self):
        return 'Energy To Grid'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Grid.energy.fromGrid.total
class ConsumeEnergySensor(Entity):
    # ?? Amount of energy drawn from the main grid (in kilowatts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' From Grid Yield'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('consumeenergy')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'kWh'

    @property
    def icon(self):
        return 'mdi:transmission-tower'

    @property
    def friendly_name(self):
        return 'Energy From Grid'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter.Meter2.AC.power.total
class FeedinPowerM2Sensor(Entity):
    # ?? -- (in watts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' AC power'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('feedinpowerM2')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'W'

    @property
    def icon(self):
        return 'mdi:solar-power'

    @property
    def friendly_name(self):
        return 'TBA'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# BMS.energy.SOC
class SocSensor(Entity):
    # ?? Current battery level (as a percentage) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' State of charge'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('soc')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return '%'

    @property
    def icon(self):
        return 'mdi:battery'

    @property
    def friendly_name(self):
        return 'Battery Charge Level'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter.AC.EPS.power.R
class Peps1Sensor(Entity):
    # ?? -- (in watts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' EPS R'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('peps1')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'W'

    @property
    def icon(self):
        return 'mdi:solar-power'

    @property
    def friendly_name(self):
        return 'TBA'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter.AC.EPS.power.S
class Peps2Sensor(Entity):
    # ?? -- (in watts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' EPS S'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('peps2')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'W'

    @property
    def icon(self):
        return 'mdi:solar-power'

    @property
    def friendly_name(self):
        return 'TBA'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter.AC.EPS.power.T
class Peps3Sensor(Entity):
    # ?? -- (in watts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' EPS T'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('peps3')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'W'

    @property
    def icon(self):
        return 'mdi:solar-power'

    @property
    def friendly_name(self):
        return 'TBA'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter type (Table 4)
class InverterTypeSensor(Entity):
    # The type/model of inverter
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' Inverter type'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('inverterType')
        return inverter_type(data)

    @property
    def icon(self):
        return 'mdi:solar-power'

    @property
    def friendly_name(self):
        return 'Inverter Type'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter status (Table 5)
class InverterStatusSensor(Entity):
    # The current status of the inverter
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' Inverter status'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('inverterStatus')
        return inverter_status(data)

    @property
    def icon(self):
        return 'mdi:solar-power'

    @property
    def friendly_name(self):
        return 'Inverter Status'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Update time
class UpdateTimeSensor(Entity):
    # The timestamp of the last data update (as a datetime)
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' Update time'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('uploadTime')
        return float('nan') if data is None else data

    @property
    def icon(self):
        return 'mdi:clock-outline'

    @property
    def friendly_name(self):
        return 'Data Last Updated'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter.DC.Battery.power.total
class BatPowerSensor(Entity):
    # ?? Current battery power storage (in watts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' Battery power'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('batpower')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'W'

    @property
    def icon(self):
        return 'mdi:battery'

    @property
    def friendly_name(self):
        return 'Battery Power'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter.DC.PV.power.MPPT1
class PowerDC1Sensor(Entity):
    # ?? -- (in watts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' MPPT 1'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('powerdc1')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'W'

    @property
    def icon(self):
        return 'mdi:solar-power'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()

# Inverter.DC.PV.power.MPPT2
class PowerDC2Sensor(Entity):
    # ?? -- (in watts) ??
    def __init__(self, hass, solax_cloud):
        self._name = solax_cloud.inverter_name + ' MPPT 2'
        self.hass = hass
        self.solax_cloud = solax_cloud

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        data = self.solax_cloud.data.get('powerdc2')
        return float('nan') if data is None else data

    @property
    def unit_of_measurement(self):
        return 'W'

    @property
    def icon(self):
        return 'mdi:solar-power'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.solax_cloud.get_data()
