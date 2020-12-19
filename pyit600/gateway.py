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
    SUPPORT_OPEN,
    SUPPORT_CLOSE,
    SUPPORT_SET_POSITION, STATE_UNKNOWN
)
from .encryptor import IT600Encryptor
from .exceptions import (
    IT600AuthenticationError,
    IT600CommandError,
    IT600ConnectionError,
)
from .models import ClimateDevice, BinarySensorDevice, SwitchDevice, CoverDevice, SensorDevice

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

        self._binary_sensor_devices: Dict[str, BinarySensorDevice] = {}
        self._binary_sensor_update_callbacks: List[Callable[[Any], Awaitable[None]]] = []

        self._switch_devices: Dict[str, SwitchDevice] = {}
        self._switch_update_callbacks: List[Callable[[Any], Awaitable[None]]] = []

        self._cover_devices: Dict[str, CoverDevice] = {}
        self._cover_update_callbacks: List[Callable[[Any], Awaitable[None]]] = []

        self._sensor_devices: Dict[str, SensorDevice] = {}
        self._sensor_update_callbacks: List[Callable[[Any], Awaitable[None]]] = []

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
            except Exception:
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

        try:
            climate_devices = list(
                filter(lambda x: "sIT600TH" in x, all_devices["id"])
            )

            await self._refresh_climate_devices(climate_devices, send_callback)
        except BaseException as e:
            _LOGGER.error("Failed to poll climate devices", exc_info=e)

        try:
            binary_sensors = list(
                filter(lambda x: "sIASZS" in x, all_devices["id"])
            )

            await self._refresh_binary_sensor_devices(binary_sensors, send_callback)
        except BaseException as e:
            _LOGGER.error("Failed to poll binary sensors", exc_info=e)

        try:
            sensors = list(
                filter(lambda x: "sTempS" in x, all_devices["id"])
            )

            await self._refresh_sensor_devices(sensors, send_callback)
        except BaseException as e:
            _LOGGER.error("Failed to poll sensors", exc_info=e)

        try:
            switches = list(
                filter(lambda x: "sOnOffS" in x, all_devices["id"])
            )

            await self._refresh_switch_devices(switches, send_callback)
        except BaseException as e:
            _LOGGER.error("Failed to poll switches", exc_info=e)

        try:
            covers = list(
                filter(lambda x: "sLevelS" in x, all_devices["id"])
            )

            await self._refresh_cover_devices(covers, send_callback)
        except BaseException as e:
            _LOGGER.error("Failed to poll covers", exc_info=e)

    async def _refresh_cover_devices(self, devices: List[Any], send_callback=False):
        local_devices = {}

        if devices:
            status = await self._make_encrypted_request(
                "read",
                {
                    "requestAttr": "deviceid",
                    "id": [{"data": device["data"]} for device in devices]
                }
            )

            for device_status in status["id"]:
                unique_id = device_status.get("data", {}).get("UniID", None)

                if unique_id is None:
                    continue

                try:
                    if device_status.get("sButtonS", {}).get("Mode", None) == 0:
                        continue  # Skip endpoints which are disabled

                    model: Optional[str] = device_status.get("DeviceL", {}).get("ModelIdentifier_i", None)

                    current_position = device_status.get("sLevelS", {}).get("CurrentLevel", None)

                    move_to_level_f = device_status.get("sLevelS", {}).get("MoveToLevel_f", None)

                    if move_to_level_f is not None and len(move_to_level_f) >= 2:
                        set_position = int(move_to_level_f[:2], 16)
                    else:
                        set_position = None

                    device = CoverDevice(
                        available=True if device_status.get("sZDOInfo", {}).get("OnlineStatus_i", 1) == 1 else False,
                        name=json.loads(device_status.get("sZDO", {}).get("DeviceName", '{"deviceName": "Unknown"}'))["deviceName"],
                        unique_id=unique_id,
                        current_cover_position=current_position,
                        is_opening=None if set_position is None else current_position < set_position,
                        is_closing=None if set_position is None else current_position > set_position,
                        is_closed=True if current_position == 0 else False,
                        supported_features=SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION,
                        device_class=None,
                        data=device_status["data"],
                        manufacturer=device_status.get("sBasicS", {}).get("ManufactureName", "SALUS"),
                        model=model,
                        sw_version=device_status.get("sZDO", {}).get("FirmwareVersion", None)
                    )

                    local_devices[device.unique_id] = device

                    if send_callback:
                        self._cover_devices[device.unique_id] = device
                        await self._send_cover_update_callback(device_id=device.unique_id)
                except BaseException as e:
                    _LOGGER.error(f"Failed to poll device {unique_id}", exc_info=e)

            self._cover_devices = local_devices
            _LOGGER.debug("Refreshed %s cover devices", len(self._cover_devices))

    async def _refresh_switch_devices(self, devices: List[Any], send_callback=False):
        local_devices = {}

        if devices:
            status = await self._make_encrypted_request(
                "read",
                {
                    "requestAttr": "deviceid",
                    "id": [{"data": device["data"]} for device in devices]
                }
            )

            for device_status in status["id"]:
                unique_id = device_status.get("data", {}).get("UniID", None)

                if unique_id is None:
                    continue
                else:
                    unique_id = unique_id + "_" + str(device_status["data"]["Endpoint"])  # Double switches have a different endpoint id, but the same device id

                try:
                    if device_status.get("sLevelS", None) is not None:
                        continue  # Skip roller shutter endpoint in combined roller shutter/relay device

                    if device_status.get("sButtonS", {}).get("Mode", None) == 0:
                        continue  # Skip endpoints which are disabled

                    is_on: Optional[bool] = device_status.get("sOnOffS", {}).get("OnOff", None)

                    if is_on is None:
                        continue

                    model: Optional[str] = device_status.get("DeviceL", {}).get("ModelIdentifier_i", None)

                    device = SwitchDevice(
                        available=True if device_status.get("sZDOInfo", {}).get("OnlineStatus_i", 1) == 1 else False,
                        name=json.loads(device_status.get("sZDO", {}).get("DeviceName", '{"deviceName": ' + json.dumps(unique_id) + '}'))["deviceName"],
                        unique_id=unique_id,
                        is_on=True if is_on == 1 else False,
                        device_class="outlet" if (model == "SP600" or model == "SPE600") else "switch",
                        data=device_status["data"],
                        manufacturer=device_status.get("sBasicS", {}).get("ManufactureName", "SALUS"),
                        model=model,
                        sw_version=device_status.get("sZDO", {}).get("FirmwareVersion", None)
                    )

                    local_devices[device.unique_id] = device

                    if send_callback:
                        self._switch_devices[device.unique_id] = device
                        await self._send_switch_update_callback(device_id=device.unique_id)
                except BaseException as e:
                    _LOGGER.error(f"Failed to poll device {unique_id}", exc_info=e)

            self._switch_devices = local_devices
            _LOGGER.debug("Refreshed %s sensor devices", len(self._switch_devices))

    async def _refresh_sensor_devices(self, devices: List[Any], send_callback=False):
        local_devices = {}

        if devices:
            status = await self._make_encrypted_request(
                "read",
                {
                    "requestAttr": "deviceid",
                    "id": [{"data": device["data"]} for device in devices]
                }
            )

            for device_status in status["id"]:
                unique_id = device_status.get("data", {}).get("UniID", None)

                if unique_id is None:
                    continue

                try:
                    temperature: Optional[int] = device_status.get("sTempS", {}).get("MeasuredValue_x100", None)

                    if temperature is None:
                        continue

                    unique_id = unique_id + "_temp"  # Some sensors also measure temperature besides their primary function (eg. SW600)

                    model: Optional[str] = device_status.get("DeviceL", {}).get("ModelIdentifier_i", None)

                    device = SensorDevice(
                        available=True if device_status.get("sZDOInfo", {}).get("OnlineStatus_i", 1) == 1 else False,
                        name=json.loads(device_status.get("sZDO", {}).get("DeviceName", '{"deviceName": "Unknown"}'))["deviceName"],
                        unique_id=unique_id,
                        state=(temperature / 100),
                        unit_of_measurement=TEMP_CELSIUS,
                        device_class="temperature",
                        data=device_status["data"],
                        manufacturer=device_status.get("sBasicS", {}).get("ManufactureName", "SALUS"),
                        model=model,
                        sw_version=device_status.get("sZDO", {}).get("FirmwareVersion", None)
                    )

                    local_devices[device.unique_id] = device

                    if send_callback:
                        self._sensor_devices[device.unique_id] = device
                        await self._send_sensor_update_callback(device_id=device.unique_id)
                except BaseException as e:
                    _LOGGER.error(f"Failed to poll device {unique_id}", exc_info=e)

            self._sensor_devices = local_devices
            _LOGGER.debug("Refreshed %s sensor devices", len(self._sensor_devices))

    async def _refresh_binary_sensor_devices(self, devices: List[Any], send_callback=False):
        local_devices = {}

        if devices:
            status = await self._make_encrypted_request(
                "read",
                {
                    "requestAttr": "deviceid",
                    "id": [{"data": device["data"]} for device in devices]
                }
            )

            for device_status in status["id"]:
                unique_id = device_status.get("data", {}).get("UniID", None)

                if unique_id is None:
                    continue

                try:
                    is_on: Optional[bool] = device_status.get("sIASZS", {}).get("ErrorIASZSAlarmed1", None)

                    if is_on is None:
                        continue

                    model: Optional[str] = device_status.get("DeviceL", {}).get("ModelIdentifier_i", None)

                    if model == "SB600":
                        continue  # Skip button

                    device = BinarySensorDevice(
                        available=True if device_status.get("sZDOInfo", {}).get("OnlineStatus_i", 1) == 1 else False,
                        name=json.loads(device_status.get("sZDO", {}).get("DeviceName", '{"deviceName": "Unknown"}'))["deviceName"],
                        unique_id=device_status["data"]["UniID"],
                        is_on=True if is_on == 1 else False,
                        device_class="window" if (model == "SW600" or model == "OS600") else
                            "moisture" if model == "WLS600" else
                            "smoke" if model == "SmokeSensor-EM" else
                            None,
                        data=device_status["data"],
                        manufacturer=device_status.get("sBasicS", {}).get("ManufactureName", "SALUS"),
                        model=model,
                        sw_version=device_status.get("sZDO", {}).get("FirmwareVersion", None)
                    )

                    local_devices[device.unique_id] = device

                    if send_callback:
                        self._binary_sensor_devices[device.unique_id] = device
                        await self._send_binary_sensor_update_callback(device_id=device.unique_id)
                except BaseException as e:
                    _LOGGER.error(f"Failed to poll device {unique_id}", exc_info=e)

            self._binary_sensor_devices = local_devices
            _LOGGER.debug("Refreshed %s binary sensor devices", len(self._binary_sensor_devices))

    async def _refresh_climate_devices(self, devices: List[Any], send_callback=False):
        local_devices = {}

        if devices:
            status = await self._make_encrypted_request(
                "read",
                {
                    "requestAttr": "deviceid",
                    "id": [{"data": device["data"]} for device in devices]
                }
            )

            for device_status in status["id"]:
                unique_id = device_status.get("data", {}).get("UniID", None)

                if unique_id is None:
                    continue

                try:
                    th = device_status.get("sIT600TH", None)

                    if th is None:
                        continue

                    device = ClimateDevice(
                        available=True if device_status.get("sZDOInfo", {}).get("OnlineStatus_i", 1) == 1 else False,
                        name=json.loads(device_status.get("sZDO", {}).get("DeviceName", '{"deviceName": "Unknown"}'))["deviceName"],
                        unique_id=unique_id,
                        temperature_unit=TEMP_CELSIUS,  # API always reports temperature as celsius
                        precision=0.5,
                        current_temperature=th["LocalTemperature_x100"] / 100,
                        target_temperature=th["HeatingSetpoint_x100"] / 100,
                        max_temp=th.get("MaxHeatSetpoint_x100", 3500) / 100,
                        min_temp=th.get("MinHeatSetpoint_x100", 500) / 100,
                        hvac_mode=HVAC_MODE_OFF if th["HoldType"] == 7 else HVAC_MODE_HEAT if th["HoldType"] == 2 else HVAC_MODE_AUTO,
                        hvac_action=CURRENT_HVAC_OFF if th["HoldType"] == 7 else CURRENT_HVAC_IDLE if th["RunningState"] % 2 == 0 else CURRENT_HVAC_HEAT,  # RunningState 0 or 128 => idle, 1 or 129 => heating
                        hvac_modes=[HVAC_MODE_OFF, HVAC_MODE_HEAT],
                        preset_mode=PRESET_OFF if th["HoldType"] == 7 else PRESET_PERMANENT_HOLD if th["HoldType"] == 2 else PRESET_FOLLOW_SCHEDULE,
                        preset_modes=[PRESET_FOLLOW_SCHEDULE, PRESET_PERMANENT_HOLD, PRESET_OFF],
                        supported_features=SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE,
                        device_class="temperature",
                        data=device_status["data"],
                        manufacturer=device_status.get("sBasicS", {}).get("ManufactureName", "SALUS"),
                        model=device_status.get("DeviceL", {}).get("ModelIdentifier_i", None),
                        sw_version=device_status.get("sZDO", {}).get("FirmwareVersion", None)
                    )

                    local_devices[device.unique_id] = device

                    if send_callback:
                        self._climate_devices[device.unique_id] = device
                        await self._send_climate_update_callback(device_id=device.unique_id)
                except BaseException as e:
                    _LOGGER.error(f"Failed to poll device {unique_id}", exc_info=e)

        self._climate_devices = local_devices
        _LOGGER.debug("Refreshed %s climate devices", len(self._climate_devices))

    async def _send_climate_update_callback(self, device_id: str) -> None:
        """Internal method to notify all update callback subscribers."""

        if self._climate_update_callbacks:
            for update_callback in self._climate_update_callbacks:
                await update_callback(device_id=device_id)
        else:
            _LOGGER.error("Callback for climate updates has not been set")

    async def _send_binary_sensor_update_callback(self, device_id: str) -> None:
        """Internal method to notify all update callback subscribers."""

        if self._binary_sensor_update_callbacks:
            for update_callback in self._binary_sensor_update_callbacks:
                await update_callback(device_id=device_id)
        else:
            _LOGGER.error("Callback for binary sensor updates has not been set")

    async def _send_switch_update_callback(self, device_id: str) -> None:
        """Internal method to notify all update callback subscribers."""

        if self._switch_update_callbacks:
            for update_callback in self._switch_update_callbacks:
                await update_callback(device_id=device_id)
        else:
            _LOGGER.error("Callback for switch updates has not been set")

    async def _send_cover_update_callback(self, device_id: str) -> None:
        """Internal method to notify all update callback subscribers."""

        if self._cover_update_callbacks:
            for update_callback in self._cover_update_callbacks:
                await update_callback(device_id=device_id)
        else:
            _LOGGER.error("Callback for cover updates has not been set")

    async def _send_sensor_update_callback(self, device_id: str) -> None:
        """Internal method to notify all update callback subscribers."""

        if self._sensor_update_callbacks:
            for update_callback in self._sensor_update_callbacks:
                await update_callback(device_id=device_id)
        else:
            _LOGGER.error("Callback for sensor updates has not been set")

    def get_climate_devices(self) -> Dict[str, ClimateDevice]:
        """Public method to return the state of all Salus IT600 climate devices."""

        return self._climate_devices

    def get_climate_device(self, device_id: str) -> Optional[ClimateDevice]:
        """Public method to return the state of the specified climate device."""

        return self._climate_devices.get(device_id)

    def get_binary_sensor_devices(self) -> Dict[str, BinarySensorDevice]:
        """Public method to return the state of all Salus IT600 binary sensor devices."""

        return self._binary_sensor_devices

    def get_binary_sensor_device(self, device_id: str) -> Optional[BinarySensorDevice]:
        """Public method to return the state of the specified binary sensor device."""

        return self._binary_sensor_devices.get(device_id)

    def get_switch_devices(self) -> Dict[str, SwitchDevice]:
        """Public method to return the state of all Salus IT600 switch devices."""

        return self._switch_devices

    def get_switch_device(self, device_id: str) -> Optional[SwitchDevice]:
        """Public method to return the state of the specified switch device."""

        return self._switch_devices.get(device_id)

    def get_cover_devices(self) -> Dict[str, CoverDevice]:
        """Public method to return the state of all Salus IT600 cover devices."""

        return self._cover_devices

    def get_cover_device(self, device_id: str) -> Optional[CoverDevice]:
        """Public method to return the state of the specified cover device."""

        return self._cover_devices.get(device_id)

    def get_sensor_devices(self) -> Dict[str, SensorDevice]:
        """Public method to return the state of all Salus IT600 sensor devices."""

        return self._sensor_devices

    def get_sensor_device(self, device_id: str) -> Optional[SensorDevice]:
        """Public method to return the state of the specified sensor device."""

        return self._sensor_devices.get(device_id)

    async def set_cover_position(self, device_id: str, position: int) -> None:
        """Public method to set position/level (where 0 means closed and 100 is fully open) on the specified cover device."""

        if position < 0 or position > 100:
            raise ValueError("position must be between 0 and 100 (both bounds inclusive)")

        device = self.get_cover_device(device_id)

        if device is None:
            _LOGGER.error("Cannot turn on: cover device not found with the specified id: %s", device_id)
            return

        await self._make_encrypted_request(
            "write",
            {
                "requestAttr": "write",
                "id": [
                    {
                        "data": device.data,
                        "sLevelS": {
                            "SetMoveToLevel": f"{format(position, '02x')}FFFF"
                        },
                    }
                ],
            },
        )

    async def open_cover(self, device_id: str) -> None:
        """Public method to open the specified cover device."""

        device = self.get_cover_device(device_id)

        if device is None:
            _LOGGER.error("Cannot turn on: cover device not found with the specified id: %s", device_id)
            return

        await self._make_encrypted_request(
            "write",
            {
                "requestAttr": "write",
                "id": [
                    {
                        "data": device.data,
                        "sLevelS": {
                            "SetMoveToLevel": f"{format(100, '02x')}FFFF"
                        },
                    }
                ],
            },
        )

    async def close_cover(self, device_id: str) -> None:
        """Public method to close the specified cover device."""

        device = self.get_cover_device(device_id)

        if device is None:
            _LOGGER.error("Cannot turn on: cover device not found with the specified id: %s", device_id)
            return

        await self._make_encrypted_request(
            "write",
            {
                "requestAttr": "write",
                "id": [
                    {
                        "data": device.data,
                        "sLevelS": {
                            "SetMoveToLevel": f"{format(0, '02x')}FFFF"
                        },
                    }
                ],
            },
        )

    async def turn_on_switch_device(self, device_id: str) -> None:
        """Public method to turn on the specified switch device."""

        device = self.get_switch_device(device_id)

        if device is None:
            _LOGGER.error("Cannot turn on: switch device not found with the specified id: %s", device_id)
            return

        await self._make_encrypted_request(
            "write",
            {
                "requestAttr": "write",
                "id": [
                    {
                        "data": device.data,
                        "sOnOffS": {
                            "SetOnOff": 1
                        },
                    }
                ],
            },
        )

    async def turn_off_switch_device(self, device_id: str) -> None:
        """Public method to turn off the specified switch device."""

        device = self.get_switch_device(device_id)

        if device is None:
            _LOGGER.error("Cannot turn off: switch device not found with the specified id: %s", device_id)
            return

        await self._make_encrypted_request(
            "write",
            {
                "requestAttr": "write",
                "id": [
                    {
                        "data": device.data,
                        "sOnOffS": {
                            "SetOnOff": 0
                        },
                    }
                ],
            },
        )

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

    async def add_binary_sensor_update_callback(self, method: Callable[[Any], Awaitable[None]]) -> None:
        """Public method to add a binary sensor callback subscriber."""

        self._binary_sensor_update_callbacks.append(method)

    async def add_switch_update_callback(self, method: Callable[[Any], Awaitable[None]]) -> None:
        """Public method to add a switch callback subscriber."""

        self._switch_update_callbacks.append(method)

    async def add_cover_update_callback(self, method: Callable[[Any], Awaitable[None]]) -> None:
        """Public method to add a cover callback subscriber."""

        self._cover_update_callbacks.append(method)

    async def add_sensor_update_callback(self, method: Callable[[Any], Awaitable[None]]) -> None:
        """Public method to add a sensor callback subscriber."""

        self._sensor_update_callbacks.append(method)

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
