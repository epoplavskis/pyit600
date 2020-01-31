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
    print()
    print("examples:")
    print("    main.py --host 192.168.0.125 --euid 001E5E0D32906128")


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
    args = parser.parse_args()

    if (not args.host) or (not args.euid):
        help()
        sys.exit(0)

    async with IT600Gateway(host=args.host, euid=args.euid) as gateway:
        try:
            await gateway.connect()
        except IT600ConnectionError as ce:
            print("Connection error: check if you have specified gateway's IP address correctly.", file=sys.stderr)
            sys.exit(1)
        except IT600AuthenticationError as ae:
            print("Authentication error: check if you have specified gateway's EUID correctly.", file=sys.stderr)
            sys.exit(2)

        print("All climate devices:")
        print(repr(gateway.get_climate_devices()))

        climate_devices = gateway.get_climate_devices()

        for climate_device_id in climate_devices:
            print(f"Climate device {climate_device_id} status:")
            print(repr(climate_devices.get(climate_device_id)))

            print(f"Setting heating device {climate_device_id} temperature to 21 degrees celsius")
            await gateway.set_climate_device_temperature(climate_device_id, 21)


if __name__ == "__main__":
    asyncio.run(main())
