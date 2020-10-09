"""Salus iT600 smart device models."""

from typing import List, NamedTuple


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
    hvac_mode: str
    hvac_action: str
    hvac_modes: List[str]
    preset_mode: str
    preset_modes: List[str]
    supported_features: int
    device_class: str
    data: dict


class BinarySensorDevice(NamedTuple):
    available: bool
    name: str
    unique_id: str
    is_on: bool
    device_class: str
    data: dict
