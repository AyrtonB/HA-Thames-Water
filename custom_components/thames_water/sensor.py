"""Platform for sensor integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from thameswaterclient import MeterUsage, ThamesWater, meter_usage_lines_to_timeseries

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SELENIUM_TIMEOUT = 60
UPDATE_HOURS = [12, 0]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> bool:
    """Set up the Thames Water sensor platform."""
    username = entry.data["username"]
    password = entry.data["password"]
    account_number = entry.data["account_number"]
    meter_id = entry.data["meter_id"]

    unique_id = get_unique_id(meter_id)

    _LOGGER.debug(
        "Configured with username: %s, account_number: %s, meter_id: %s",
        username,
        account_number,
        meter_id,
    )

    name = entry.data.get(CONF_NAME, "Thames Water Sensor")

    sensor = ThamesWaterSensor(
        hass,
        name,
        username,
        password,
        account_number,
        meter_id,
        unique_id,
    )
    async_add_entities([sensor], update_before_add=True)

    # Schedule the sensor to update every day at 12:00 PM.
    async_track_time_change(
        hass,
        sensor.async_update_callback,
        hour=UPDATE_HOURS,
        minute=0,
        second=0,
    )
    return True


def get_unique_id(meter_id: str) -> str:
    """Return a unique ID for the sensor."""
    return f"water_usage_{meter_id}"



def _generate_statistics_from_meter_usage(start: date, meter_usage: MeterUsage) -> list[StatisticData]:
    """Convert a list of (datetime, reading) entries into StatisticData entries."""
    return [
        StatisticData(
            start=measurement.hour_start,
            state=measurement.usage,
            sum=measurement.total,
        )
        for measurement
        in meter_usage_lines_to_timeseries(start, meter_usage.Lines)
    ]


class ThamesWaterSensor(SensorEntity):
    """Thames Water Sensor class."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        username: str,
        password: str,
        account_number: str,
        meter_id: str,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._name = name
        self._state: float | None = None

        self._username = username
        self._password = password
        self._account_number = account_number
        self._meter_id = meter_id

        self._unique_id = unique_id
        self._attr_should_poll = False

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self) -> float | None:
        """Return the sensor state (latest hourly consumption in Liters)."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement (Liters)."""
        return UnitOfVolume.LITERS

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the consumption sensor."""
        return DeviceInfo(
            identifiers={(DOMAIN, "thames_water")},
            manufacturer="Thames Water",
            model="Thames Water",
            name="Thames Water Meter",
        )

    @callback
    async def async_update_callback(self, ts) -> None:
        """Callback triggered by time change to update the sensor and inject statistics."""
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        """Fetch data, build hourly statistics, and inject external statistics."""
        stat_id = f"{DOMAIN}:thameswater_consumption"

        end_dt = datetime.now() - timedelta(days=3)
        start_dt = end_dt - timedelta(days=3)
        # readings holds all hourly data for the entire period.

        thames_water = ThamesWater(email=self._username, password=self._password, account_number=self._account_number)
        meter_usage = thames_water.get_meter_usage(self._meter_id, start_dt, end_dt)
        _LOGGER.info("Fetched %d historical entries", len(meter_usage.Lines))

        if len(meter_usage.Lines) == 0:
            return

        # Generate new StatisticData entries using the previous cumulative sum.
        stats = _generate_statistics_from_meter_usage(start_dt, meter_usage)
        self._state = meter_usage.Lines[-1].Read  # most recent total usage on meter

        # Build per-hour statistics from each reading.
        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="Thames Water Consumption",
            source=DOMAIN,
            statistic_id=stat_id,
            unit_of_measurement=UnitOfVolume.LITERS,
        )
        async_add_external_statistics(self._hass, metadata, stats)
