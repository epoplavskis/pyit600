# Python: Asynchronous client for Salus iT600 devices

## For end users
See https://github.com/jvitkauskas/homeassistant_salus to use this in Home Assistant.

## About

This package allows you to control and monitor your Salus iT600 smart home devices locally through Salus UG600 universal gateway. Currently heating thermostats, binary sensors, temperature sensors, covers and switches are supported. You have any other devices and would like to contribute - you are welcome to create an issue or submit a pull request.

## Installation

```bash
pip install pyit600
```

## Usage
 - Instantiate the IT600Gateway device with local ip address and EUID of your gateway. You can find EUID written down on the bottom of your gateway (eg. 001E5E0D32906128).
 - Status can be polled using the `poll_status()` command.
 - Callbacks to be notified of state updates can be added with the `add_climate_update_callback(method)` or `add_sensor_update_callback(method)` method.

### Basic example

```python
async with IT600Gateway(host=args.host, euid=args.euid) as gateway:
	await gateway.connect()
	await gateway.poll_status()

	climate_devices = gateway.get_climate_devices()

	print("All climate devices:")
	print(repr(climate_devices))

	for climate_device_id in climate_devices:
		print(f"Climate device {climate_device_id} status:")
		print(repr(climate_devices.get(climate_device_id)))

		print(f"Setting heating device {climate_device_id} temperature to 21 degrees celsius")
		await gateway.set_climate_device_temperature(climate_device_id, 21)
```

### Useful gateway methods

 - poll_status()
 - get_climate_devices()
 - get_climate_device(device_id)
 - set_climate_device_preset(device_id, preset)
 - set_climate_device_mode(device_id, mode)
 - set_climate_device_temperature(device_id, setpoint_celsius)
 - get_binary_sensor_devices()
 - get_binary_sensor_device(device_id)
 - get_switch_devices()
 - get_switch_device(device_id)
 - turn_on_switch_device(device_id)
 - turn_off_switch_device(device_id)
 - get_cover_devices()
 - get_cover_device(device_id)
 - set_cover_position(device_id, position)
 - open_cover(device_id)
 - close_cover(device_id)
 - get_sensor_devices()
 - get_sensor_device(device_id)
 - get_gateway_device()

### Supported devices

Thermostats:
* HTRP-RF(50)
* TS600
* VS10WRF/VS10BRF
* VS20WRF/VS20BRF
* SQ610RF
* FC600

Binary sensors:
* SW600
* WLS600
* OS600

Temperature sensors:
* PS600

Switch devices:
* SPE600
* RS600

Cover devices:
* RS600

### Unsupported devices

Buttons perform actions only in Salus Smart Home app:
* SB600
* CSB600

These binary sensors do not work yet:
* SD600

These switch devices do not work yet:
* SR600

### Untested devices

These thermostats devices have not been tested, but may work:
* SQ610

These switch devices have not been tested, but may work:
* SP600

These binary sensors have not been tested, but may work:
* MS600

### Troubleshooting

Check if you have "Local Wifi Mode" enabled:
* Open Smart Home app on your phone
* Sign in
* Double tap your Gateway to open info screen
* Press gear icon to enter configuration
* Scroll down a bit and check if "Disable Local WiFi Mode" is set to "No"
* Scroll all the way down and save settings
* Restart Gateway by unplugging/plugging USB power


### Contributing

If you want to help to get your device supported, open GitHub issue and add your device model number and output of `main.py` program. Be sure to run this program with --debug option.
