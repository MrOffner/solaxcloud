# SolaxCloud integration for Home Assistant.

Solax Cloud integration based on the SolaxCloud API.
This component is basically a rewrite of [thomascys/solaxcloud]
(https://github.com/thomascys/solaxcloud) which used the old system.

To use this component you will need the following:
- An API key: Which can be created from the online portal
  (https://www.solaxcloud.com/#/api) under the 'Service > API' menu
- The Inverter's Serial Number (SN): The 10 character Registration No. of the
  specific inverter (see the Inverter's menu in SolaxCloud)

## Installation

This component currently only supports manual installation:
- Place this directory in `/config/custom_components`. If `custom_components`
  does not exist, you will have to create it.
- Add the sensor to your configuration.yaml file:

```yaml
sensor:
  - platform: solaxcloud
    name: Inverter 1
    api_key: YOUR_API_KEY
    sn: YOUR_INVERTER_SN
```
- Verify that the custom entities are available in home assistant (Total Yield,
  Daily Yield, AC Power etc).


## Config
| Key | Type | Required | Value | Description |
|---|---|---|---|---|
| `name` | string | true | | A unique name for the Solax inverter |
| `api_key` | string | true | | The unique API key generate from the online Solax Cloud portal |
| `sn` | string | true | | The serial number of the inverter. |
| `battery` | boolean | false | default: `False` | Is there battery storage attached to the inverter? |

## Multiple Inverters

If you have multiple inverters in your PV installation they can be added by
creating additional sensors and changing the inverter SN:

```yaml
sensor:
  - platform: solaxcloud
    name: Inverter 2
    api_key: YOUR_API_KEY
    sn: YOUR_INVERTER_2_SN
```
If you want the combined value of your inverters, this can be achieved by using
Home Assistant's template platform to combine the values together:

```yaml
- platform: template
  sensors:
    total_yield:
      friendly_name: 'Total Yield'
      icon_template: 'mdi:solar-power'
      unit_of_measurement: 'kWh'
      value_template: "{{ states('sensor.inverter_1_total_yield')|float + states('sensor.inverter_2_total_yield')|float }}"

    daily_yield:
      friendly_name: 'Daily Yield'
      icon_template: 'mdi:solar-power'
      unit_of_measurement: 'kWh'
      value_template: "{{ states('sensor.inverter_1_daily_yield')|float + states('sensor.inverter_2_daily_yield')|float }}"

    ac_power:
      friendly_name: 'AC Power'
      icon_template: 'mdi:solar-power'
      unit_of_measurement: 'kW'
      value_template: "{{ states('sensor.inverter_1_ac_power')|float + states('sensor.inverter_2_ac_power')|float }}"
```
## Documentation

Documentation for the API can be found on the SolaxCloud website:
https://www.solaxcloud.com/user_api/SolaxCloud_User_Monitoring_API_V6.1.pdf

## Notes

- My system only contains a single inverter with no battery storage, so much of this is guesswork.
- I am not in any way an electrical engineer so have a very limited understanding of the terminology.