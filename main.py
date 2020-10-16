#!/usr/bin/env python
import argparse
import asyncio
import logging
import sys

from pyit600.exceptions import IT600AuthenticationError, IT600ConnectionError
from pyit600.gateway import IT600Gateway


def help():
    print("pyit600 demo app")
    print("syntax: main.py [options]")
    print("options:")
    print("   --host <gateway_ip>     ... network address of your Salus UG600 universal gateway")
    print("   --euid <gateway_euid>   ... EUID which is specified on the bottom of your gateway")
    print("   --debug                 ... use this if you want to print requests/responses")
    print()
    print("examples:")
    print("    main.py --host 192.168.0.125 --euid 001E5E0D32906128 --debug")


async def my_climate_callback(device_id):
    print("Got callback for climate device id: " + device_id)


async def my_sensor_callback(device_id):
    print("Got callback for sensor device id: " + device_id)


async def my_switch_callback(device_id):
    print("Got callback for switch device id: " + device_id)


async def my_cover_callback(device_id):
    print("Got callback for cover device id: " + device_id)


async def main():
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(description="Commands: mode fan temp")
    parser.add_argument(
        "--host",
        type=str,
        dest="host",
        help="network address of your Salus UG600 universal gateway",
        metavar="HOST",
        default=None,
    )
    parser.add_argument(
        "--euid",
        type=str,
        dest="euid",
        help="EUID which is specified on the bottom of your gateway",
        metavar="EUID",
        default=None,
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        help="Debug mode which prints requests/responses",
        action="store_true",
    )
    args = parser.parse_args()

    if (not args.host) or (not args.euid):
        help()
        sys.exit(0)

    async with IT600Gateway(host=args.host, euid=args.euid, debug=args.debug) as gateway:
        try:
            await gateway.connect()
        except IT600ConnectionError:
            print("Connection error: check if you have specified gateway's IP address correctly.", file=sys.stderr)
            sys.exit(1)
        except IT600AuthenticationError:
            print("Authentication error: check if you have specified gateway's EUID correctly.", file=sys.stderr)
            sys.exit(2)

        await gateway.add_climate_update_callback(my_climate_callback)
        await gateway.add_binary_sensor_update_callback(my_sensor_callback)
        await gateway.add_switch_update_callback(my_switch_callback)
        await gateway.add_cover_update_callback(my_cover_callback)

        await gateway.poll_status(send_callback=True)

        climate_devices = gateway.get_climate_devices()

        if not climate_devices:
            print(
                """Warning: no climate devices found. Ensure that you have paired your thermostat(s) with gateway and you can see it in the official Salus app. If it works there, your thermostat might not be supported. If you want to help to get it supported, open GitHub issue and add your thermostat model number and output of this program. Be sure to run this program with --debug option.\n""")
        else:
            print("All climate devices:")
            print(repr(climate_devices))

            for climate_device_id in climate_devices:
                print(f"Climate device {climate_device_id} status:")
                print(repr(climate_devices.get(climate_device_id)))

                print(f"Setting heating device {climate_device_id} temperature to 21 degrees celsius")
                await gateway.set_climate_device_temperature(climate_device_id, 21)

        binary_sensor_devices = gateway.get_binary_sensor_devices()

        if not binary_sensor_devices:
            print(
                """Warning: no binary sensor devices found. Ensure that you have paired your binary sensor(s) with gateway and you can see it in the official Salus app. If it works there, your sensor might not be supported. If you want to help to get it supported, open GitHub issue and add your binary sensor model number and output of this program. Be sure to run this program with --debug option.\n""")
        else:
            print("All binary sensor devices:")
            print(repr(binary_sensor_devices))

            for binary_sensor_device_id in binary_sensor_devices:
                print(f"Binary sensor device {binary_sensor_device_id} status:")
                device = binary_sensor_devices.get(binary_sensor_device_id)
                print(repr(device))

                print(f"'{device.name}' is on: {device.is_on}")

        switch_devices = gateway.get_switch_devices()

        if not switch_devices:
            print(
                """Warning: no switch devices found. Ensure that you have paired your switch(es) with gateway and you can see it in the official Salus app. If it works there, your switch might not be supported. If you want to help to get it supported, open GitHub issue and add your switch model number and output of this program. Be sure to run this program with --debug option.\n""")
        else:
            print("All switch devices:")
            print(repr(switch_devices))

            for switch_device_id in switch_devices:
                print(f"Switch device {switch_device_id} status:")
                device = switch_devices.get(switch_device_id)
                print(repr(device))

                print(f"Toggling device {switch_device_id}")
                if device.is_on:
                    await gateway.turn_off_switch_device(switch_device_id)
                else:
                    await gateway.turn_on_switch_device(switch_device_id)

        cover_devices = gateway.get_cover_devices()

        if not cover_devices:
            print(
                """Warning: no cover devices found. Ensure that you have paired your cover(s) with gateway and you can see it in the official Salus app. If it works there, your cover might not be supported. If you want to help to get it supported, open GitHub issue and add your cover model number and output of this program. Be sure to run this program with --debug option.\n""")
        else:
            print("All cover devices:")
            print(repr(cover_devices))

            for sensor_device_id in cover_devices:
                print(f"Switch device {sensor_device_id} status:")
                device = switch_devices.get(sensor_device_id)
                print(repr(device))

                print(f"Setting {sensor_device_id} to 25%")
                await gateway.set_cover_position(sensor_device_id, 25)

        sensor_devices = gateway.get_sensor_devices()

        if not sensor_devices:
            print(
                """Warning: no sensor devices found. Ensure that you have paired your sensor(s) with gateway and you can see it in the official Salus app. If it works there, your cover might not be supported. If you want to help to get it supported, open GitHub issue and add your sensor model number and output of this program. Be sure to run this program with --debug option.\n""")
        else:
            print("All sensor devices:")
            print(repr(sensor_devices))

            for sensor_device_id in sensor_devices:
                print(f"Sensor device {sensor_device_id} status:")
                device = sensor_devices.get(sensor_device_id)
                print(repr(device))


if __name__ == "__main__":
    asyncio.run(main())
