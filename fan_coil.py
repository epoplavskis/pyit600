#!/usr/bin/env python
import argparse
import asyncio
import logging
import sys

from pyit600.exceptions import IT600AuthenticationError, IT600ConnectionError
from pyit600.gateway_singleton import IT600GatewaySingleton


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


async def my_fan_coil_callback(device_id):
    print("Got callback for fan coil device id: " + device_id)


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

    async with IT600GatewaySingleton.get_instance(host=args.host, euid=args.euid, debug=args.debug) as gateway:
        try:
            await gateway.connect()
        except IT600ConnectionError:
            print("Connection error: check if you have specified gateway's IP address correctly.", file=sys.stderr)
            sys.exit(1)
        except IT600AuthenticationError:
            print("Authentication error: check if you have specified gateway's EUID correctly.", file=sys.stderr)
            sys.exit(2)

        await gateway.add_fan_coil_update_callback(my_fan_coil_callback)

        await gateway.poll_status(send_callback=True)

        fan_coil_devices = gateway.get_fan_coil_devices()

        if not fan_coil_devices:
            print(
                """Warning: no fan coil devices found. Ensure that you have paired your thermostat(s) with gateway and you can see it in the official Salus app. If it works there, your thermostat might not be supported. If you want to help to get it supported, open GitHub issue and add your thermostat model number and output of this program. Be sure to run this program with --debug option.\n""")
        # else:
            # fan_coil_device_id = "001e5e090238d108"
            # print(f"Fan coil device {fan_coil_device_id} status:")
            # print(repr(fan_coil_devices.get(fan_coil_device_id)))

if __name__ == "__main__":
    asyncio.run(main())
