"""Salus iT600 gateway API."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable

import aiohttp
import async_timeout

from .const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_FOLLOW_SCHEDULE,
    PRESET_OFF,
    PRESET_PERMANENT_HOLD,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    TEMP_CELSIUS,
)
from .encryptor import IT600Encryptor
from .exceptions import (
    IT600AuthenticationError,
    IT600CommandError,
    IT600ConnectionError,
)
from .models import ClimateDevice

_LOGGER = logging.getLogger("pyit600")


class IT600Gateway:
    def __init__(
            self,
            euid: str,
            host: str,
            port: int = 80,
            request_timeout: int = 5,
            session: aiohttp.client.ClientSession = None,
            debug: bool = False,
    ):
        self._encryptor = IT600Encryptor(euid)
        self._host = host
        self._port = port
        self._request_timeout = request_timeout
        self._debug = debug

        """Initialize connection with the iT600 gateway."""
        self._session = session
        self._close_session = False

        self._climate_devices: Dict[str, ClimateDevice] = {}
        self._climate_update_callbacks: List[Callable[[Any], Awaitable[None]]] = []

    async def connect(self) -> str:
        """Public method for connecting to Salus universal gateway.
           On successful connection, returns gateway's mac address"""

        _LOGGER.debug("Trying to connect to gateway at %s", self._host)

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._close_session = True

        try:
            all_devices = await self._make_encrypted_request(
                "read",
                {
                    "requestAttr": "readall"
                }
            )

            gateway = next(
                filter(lambda x: len(x.get("sGateway", {}).get("NetworkLANMAC", "")) > 0, all_devices["id"]),
                None
            )

            if gateway is None:
                raise IT600CommandError(
                    "Error occurred while communicating with iT600 gateway: "
                    "response did not contain gateway information"
                )

            return gateway["sGateway"]["NetworkLANMAC"]
        except IT600ConnectionError as ae:
            try:
                with async_timeout.timeout(self._request_timeout):
                    await self._session.get(f"http://{self._host}:{self._port}/")
            except Exception as e:
                raise IT600ConnectionError(
                    "Error occurred while communicating with iT600 gateway: "
                    "check if you have specified host/IP address correctly"
                ) from ae

            raise IT600AuthenticationError(
                "Error occurred while communicating with iT600 gateway: "
                "check if you have specified EUID correctly"
            ) from ae

    async def poll_status(self, send_callback=False) -> None:
        """Public method for polling the state of Salus iT600 devices."""

        all_devices = await self._make_encrypted_request(
            "read",
            {
                "requestAttr": "readall"
            }
        )

        thermostats = list(
            filter(lambda x: x.get("sBasicS", {}).get("ModelIdentifier", "").startswith("it600ThermHW"), all_devices["id"])
        )

        status = await self._make_encrypted_request(
            "read",
            {
                "requestAttr": "deviceid",
                "id": [{"data": thermostat["data"]} for thermostat in thermostats]
            }
        )

        local_thermostats = {}

        for thermostat_status in status["id"]:
            th = thermostat_status.get("sIT600TH", None)

            if th is None:
                continue

            thermostat = ClimateDevice(
                available=True if thermostat_status.get("sZDOInfo", {}).get("OnlineStatus_i", 1) == 1 else False,
                name=json.loads(thermostat_status.get("sZDO", {}).get("DeviceName", '{"deviceName": "Unknown"}'))["deviceName"],
                unique_id=thermostat_status["data"]["UniID"],
                temperature_unit=TEMP_CELSIUS,  # API always reports temperature as celsius
                precision=0.5,
                current_temperature=th["LocalTemperature_x100"] / 100,
                target_temperature=th["HeatingSetpoint_x100"] / 100,
                max_temp=th["MaxHeatSetpoint_x100"] / 100,
                min_temp=th["MinHeatSetpoint_x100"] / 100,
                hvac_mode=HVAC_MODE_OFF if th["HoldType"] == 7 else HVAC_MODE_HEAT,
                hvac_action=CURRENT_HVAC_OFF if th["HoldType"] == 7 else CURRENT_HVAC_HEAT if th["RunningState"] == 1 else CURRENT_HVAC_IDLE,
                hvac_modes=[HVAC_MODE_OFF, HVAC_MODE_HEAT],
                preset_mode=PRESET_OFF if th["HoldType"] == 7 else PRESET_PERMANENT_HOLD if th["HoldType"] == 2 else PRESET_FOLLOW_SCHEDULE,
                preset_modes=[PRESET_FOLLOW_SCHEDULE, PRESET_PERMANENT_HOLD, PRESET_OFF],
                supported_features=SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE,
                device_class="temperature",
                data=thermostat_status["data"]
            )

            local_thermostats[thermostat.unique_id] = thermostat

            if send_callback:
                self._climate_devices[thermostat.unique_id] = thermostat
                await self._send_climate_update_callback(device_id=thermostat.unique_id)

        self._climate_devices = local_thermostats
        _LOGGER.debug("Refreshed %s climate devices", len(self._climate_devices))

    async def _send_climate_update_callback(self, device_id: str) -> None:
        """Internal method to notify all update callback subscribers."""

        if self._climate_update_callbacks:
            for climate_callback in self._climate_update_callbacks:
                await climate_callback(device_id=device_id)
        else:
            _LOGGER.error("Callback for climate updates has not been set")

    def get_climate_devices(self) -> Dict[str, ClimateDevice]:
        """Public method to return the state of all Salus IT600 devices."""

        return self._climate_devices

    def get_climate_device(self, device_id: str) -> Optional[ClimateDevice]:
        """Public method to return the state of the specified device."""

        return self._climate_devices.get(device_id)

    async def set_climate_device_preset(self, device_id: str, preset: str) -> None:
        """Public method for setting the hvac preset."""

        device = self.get_climate_device(device_id)

        if device is None:
            _LOGGER.error("Cannot set mode: climate device not found with the specified id: %s", device_id)
            return

        await self._make_encrypted_request(
            "write",
            {
                "requestAttr": "write",
                "id": [
                    {
                        "data": device.data,
                        "sIT600TH": {
                            "SetHoldType": 7 if preset == PRESET_OFF else 2 if preset == PRESET_PERMANENT_HOLD else 0
                        },
                    }
                ],
            },
        )

    async def set_climate_device_mode(self, device_id: str, mode: str) -> None:
        """Public method for setting the hvac mode."""

        device = self.get_climate_device(device_id)

        if device is None:
            _LOGGER.error("Cannot set mode: device not found with the specified id: %s", device_id)
            return

        await self._make_encrypted_request(
            "write",
            {
                "requestAttr": "write",
                "id": [
                    {
                        "data": device.data,
                        "sIT600TH": {"SetHoldType": 7 if mode == HVAC_MODE_OFF else 0},
                    }
                ],
            },
        )

    async def set_climate_device_temperature(self, device_id: str, setpoint_celsius: float) -> None:
        """Public method for setting the temperature."""

        device = self.get_climate_device(device_id)

        if device is None:
            _LOGGER.error("Cannot set mode: climate device not found with the specified id: %s", device_id)
            return

        await self._make_encrypted_request(
            "write",
            {
                "requestAttr": "write",
                "id": [
                    {
                        "data": device.data,
                        "sIT600TH": {"SetHeatingSetpoint_x100": int(self.round_to_half(setpoint_celsius) * 100)},
                    }
                ],
            },
        )

    @staticmethod
    def round_to_half(number: float) -> float:
        """Rounds number to half of the integer (eg. 1.01 -> 1, 1.4 -> 1.5, 1.8 -> 2)"""

        return round(number * 2) / 2

    async def add_climate_update_callback(self, method: Callable[[Any], Awaitable[None]]) -> None:
        """Public method to add a climate callback subscriber."""

        self._climate_update_callbacks.append(method)

    async def _make_encrypted_request(self, command: str, request_body: dict) -> Any:
        """Makes encrypted Salus iT600 json request, decrypts and returns response."""

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._close_session = True

        try:
            request_url = f"http://{self._host}:{self._port}/deviceid/{command}"
            request_body_json = json.dumps(request_body)

            if self._debug:
                _LOGGER.debug("Gateway request: POST %s\n%s\n", request_url, request_body_json)

            with async_timeout.timeout(self._request_timeout):
                resp = await self._session.post(
                    request_url,
                    data=self._encryptor.encrypt(request_body_json),
                    headers={"content-type": "application/json"},
                )
                response_bytes = await resp.read()
                response_json_string = self._encryptor.decrypt(response_bytes)

                if self._debug:
                    _LOGGER.debug("Gateway response:\n%s\n", response_json_string)

                response_json = json.loads(response_json_string)

                if not response_json["status"] == "success":
                    repr_request_body = repr(request_body)

                    _LOGGER.error("%s failed: %s", command, repr_request_body)
                    raise IT600CommandError(
                        f"iT600 gateway rejected '{command}' command with content '{repr_request_body}'"
                    )

                return response_json
        except asyncio.TimeoutError as e:
            _LOGGER.error("Timeout while connecting to gateway: %s", e)
            raise IT600ConnectionError(
                "Error occurred while communicating with iT600 gateway: timeout"
            ) from e
        except Exception as e:
            _LOGGER.error("Exception. %s / %s", type(e), repr(e.args), e)
            raise IT600CommandError(
                "Unknown error occurred while communicating with iT600 gateway"
            ) from e

    async def close(self) -> None:
        """Close open client session."""

        if self._session and self._close_session:
            await self._session.close()

    async def __aenter__(self) -> "IT600Gateway":
        """Async enter."""

        return self

    async def __aexit__(self, *exc_info) -> None:
        """Async exit."""

        await self.close()
