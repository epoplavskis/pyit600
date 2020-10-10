# Python: Asynchronous client for Salus iT600 devices

## About

This package allows you to control and monitor your Salus iT600 smart home devices locally through Salus UG600 universal gateway. Currently only heating thermostats and some sensors are supported. You have any other devices and would like to contribute - you are welcome to create an issue or submit a pull request.

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

### Supported devices

These thermostats have been tested:
* HTRP-RF(50)
* TS600
* VS10WRF/VS10BRF
* VS20WRF/VS20BRF
* SQ610RF

These sensors have been tested:
* SW600

These sensors have not been tested, but may work:
* WLS600
* OS600
* SD600

### Contributing

If you want to help to get your device supported, open GitHub issue and add your device model number and output of `main.py` program. Be sure to run this program with --debug option.
