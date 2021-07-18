"""Salus iT600 smart device models."""

from typing import List, NamedTuple, Optional, Any


class GatewayDevice(NamedTuple):
    name: str
    unique_id: str
    data: dict
    manufacturer: str
    model: Optional[str]
    sw_version: Optional[str]


class ClimateDevice(NamedTuple):
    available: bool
    name: str
    unique_id: str
    temperature_unit: str
    precision: float
    current_temperature: float
    target_temperature: float
    max_temp: float
    min_temp: float
    current_humidity: Optional[float]
    hvac_mode: str
    hvac_action: str
    hvac_modes: List[str]
    preset_mode: str
    preset_modes: List[str]
    supported_features: int
    device_class: str
    data: dict
    manufacturer: str
    model: Optional[str]
    sw_version: Optional[str]

class FanCoilDevice(NamedTuple):
    available: bool
    name: str
    unique_id: str
    temperature_unit: str
    precision: float
    current_temperature: float
    target_cooling_temperature: float
    target_heating_temperature: float
    min_cooling_temp: float
    min_heating_temp: float
    max_cooling_temp: float
    max_heating_temp: float
    fan_speed: str
    hvac_mode: str
    hvac_action: str
    hvac_modes: List[str]
    preset_mode: str
    preset_modes: List[str]
    supported_features: int
    locked: bool
    device_class: str
    data: dict
    manufacturer: str
    model: Optional[str]
    sw_version: Optional[str]

class BinarySensorDevice(NamedTuple):
    available: bool
    name: str
    unique_id: str
    is_on: bool
    device_class: str
    data: dict
    manufacturer: str
    model: Optional[str]
    sw_version: Optional[str]


class SwitchDevice(NamedTuple):
    available: bool
    name: str
    unique_id: str
    is_on: bool
    device_class: str
    data: dict
    manufacturer: str
    model: Optional[str]
    sw_version: Optional[str]


class CoverDevice(NamedTuple):
    available: bool
    name: str
    unique_id: str
    current_cover_position: Optional[int]
    is_opening: Optional[bool]
    is_closing: Optional[bool]
    is_closed: bool
    supported_features: int
    device_class: Optional[str]
    data: dict
    manufacturer: str
    model: Optional[str]
    sw_version: Optional[str]


class SensorDevice(NamedTuple):
    available: bool
    name: str
    unique_id: str
    state: Any
    unit_of_measurement: str
    device_class: str
    data: dict
    manufacturer: str
    model: Optional[str]
    sw_version: Optional[str]
