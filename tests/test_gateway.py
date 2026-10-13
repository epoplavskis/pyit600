"""Tests for SQ610 floor sensor (S1/S2) temperature parsing in IT600Gateway."""

import unittest
from unittest.mock import AsyncMock, patch

from pyit600.gateway import IT600Gateway


def _sq610_device_status(unique_id: str, status_d, out_sensor_probe: int = 1, model: str = "SQ610NH") -> dict:
    """Build a minimal, synthetic sIT600TH device status as returned by the
    gateway's "readall"/"deviceid" endpoints, structurally identical to real
    captured responses but with anonymized identifiers."""
    return {
        "data": {"DeviceType": 100, "Endpoint": 9, "UniID": unique_id},
        "DeviceL": {"ModelIdentifier_i": model},
        "sBasicS": {"ManufactureName": "SALUS", "ModelIdentifier": model},
        "sZDO": {
            "DeviceName": '{"deviceName": "Test Thermostat"}',
            "FirmwareVersion": "00000056",
        },
        "sZDOInfo": {"OnlineStatus_i": 1},
        "sIT600TH": {
            "LocalTemperature_x100": 1853,
            "HeatingSetpoint_x100": 2000,
            "MaxHeatSetpoint_x100": 3500,
            "MinHeatSetpoint_x100": 500,
            "HoldType": 2,
            "RunningState": 1,
            "SunnySetpoint_x100": 71,
            "OUTSensorProbe": out_sensor_probe,
            "OUTSensorType": 0,
            "Status_d": status_d,
        },
    }


def _sthers_device_status(unique_id: str) -> dict:
    """Minimal sTherS (non-SQ610) thermostat status, which has no floor
    sensor support and must remain unaffected by the SQ610-only parsing."""
    return {
        "data": {"DeviceType": 100, "Endpoint": 9, "UniID": unique_id},
        "DeviceL": {"ModelIdentifier_i": "VS10WRF"},
        "sBasicS": {"ManufactureName": "SALUS", "ModelIdentifier": "VS10WRF"},
        "sZDO": {
            "DeviceName": '{"deviceName": "Other Thermostat"}',
            "FirmwareVersion": "1.0",
        },
        "sZDOInfo": {"OnlineStatus_i": 1},
        "sTherS": {
            "LocalTemperature_x100": 2000,
            "HeatingSetpoint_x100": 2100,
            "CoolingSetpoint_x100": 2400,
            "SystemMode": 4,
            "RunningState": 0,
        },
        "sComm": {"HoldType": 0},
        "sFanS": {"FanMode": 5},
    }


class TestSQ610FloorTemperature(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.gateway = IT600Gateway(host="127.0.0.1", euid="0000000000000000")

    async def asyncTearDown(self):
        await self.gateway.close()

    async def _refresh(self, device_status: dict):
        with patch.object(
            self.gateway,
            "_make_encrypted_request",
            new=AsyncMock(return_value={"id": [device_status]}),
        ):
            await self.gateway._refresh_climate_devices(
                [{"data": device_status["data"]}]
            )

        return self.gateway.get_climate_devices()["test-uid"]

    async def test_floor_temperature_read_when_probe_connected(self):
        # Real captured Status_d has LocalTemperature (1853) at [8:12] and
        # floor temperature (2138 => 21.38C) at [12:16].
        status_d = "71b30d0218532138012000210024000404013030303000007104"
        device = _sq610_device_status("test-uid", status_d)
        result = await self._refresh(device)

        self.assertEqual(result.current_floor_temperature, 21.38)
        self.assertEqual(result.current_temperature, 18.53)
        self.assertEqual(result.current_humidity, 71)

    async def test_floor_temperature_none_when_probe_not_connected(self):
        status_d = "71b30d0218532138012000210024000404013030303000007104"
        device = _sq610_device_status("test-uid", status_d, out_sensor_probe=0)

        result = await self._refresh(device)

        self.assertIsNone(result.current_floor_temperature)

    async def test_floor_temperature_none_on_sentinel_value(self):
        # Non-decimal hex digits (e.g. 0xFFFF "not connected" sentinel) at
        # the floor temperature offset must not be parsed as a reading.
        status_d = "71b30d02185ffff012000210024000404013030303000007104"
        device = _sq610_device_status("test-uid", status_d)

        result = await self._refresh(device)

        self.assertIsNone(result.current_floor_temperature)

    async def test_floor_temperature_none_when_status_d_missing(self):
        device = _sq610_device_status("test-uid", status_d="")

        result = await self._refresh(device)

        self.assertIsNone(result.current_floor_temperature)

    async def test_floor_temperature_none_when_status_d_too_short(self):
        device = _sq610_device_status("test-uid", status_d="71b30d0218")

        result = await self._refresh(device)

        self.assertIsNone(result.current_floor_temperature)

    async def test_floor_temperature_none_when_status_d_not_a_string(self):
        # A null/non-string Status_d must not raise and drop the thermostat.
        device = _sq610_device_status("test-uid", status_d=None)

        result = await self._refresh(device)

        self.assertIsNone(result.current_floor_temperature)
        self.assertEqual(result.current_temperature, 18.53)

    async def test_non_sq610_sit600th_model_unaffected(self):
        """Other sIT600TH thermostats share the code path with SQ610 but
        must not get floor temperature or humidity parsed, even if they
        happen to report the same fields."""
        status_d = "71b30d0218532138012000210024000404013030303000007104"
        device = _sq610_device_status("test-uid", status_d, model="VS20WRF")

        result = await self._refresh(device)

        self.assertIsNone(result.current_floor_temperature)
        self.assertIsNone(result.current_humidity)
        self.assertEqual(result.current_temperature, 18.53)
        self.assertEqual(result.target_temperature, 20.0)

    async def test_other_thermostat_model_unaffected(self):
        """sTherS-based thermostats never had floor temperature parsing and
        must keep returning None without touching unrelated fields."""
        device = _sthers_device_status("test-uid")

        result = await self._refresh(device)

        self.assertIsNone(result.current_floor_temperature)
        self.assertEqual(result.current_temperature, 20.0)


if __name__ == "__main__":
    unittest.main()
