"""
This component provides HA sensor for Netgear Arlo IP cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.arlo/
"""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (ATTR_ATTRIBUTION,
                                 CONF_MONITORED_CONDITIONS,
                                 DEVICE_CLASS_HUMIDITY,
                                 DEVICE_CLASS_TEMPERATURE,
                                 TEMP_CELSIUS)
from homeassistant.core import callback
from homeassistant.helpers.config_validation import (PLATFORM_SCHEMA)
from homeassistant.helpers.entity import (Entity)
from homeassistant.helpers.icon import icon_for_battery_level
from . import CONF_ATTRIBUTION, DATA_ARLO, DEFAULT_BRAND

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['aarlo']

# sensor_type [ description, unit, icon ]
SENSOR_TYPES = {
    'last_capture': ['Last', None, 'run-fast', 'lastCapture'],
    'total_cameras': ['Arlo Cameras', None, 'video', 'totalCameras'],
    'recent_activity': ['Recent Activity', None, 'run-fast', 'recentActivity'],
    'captured_today': ['Captured Today', None, 'file-video', 'capturedToday'],
    'battery_level': ['Battery Level', '%', 'battery-50', 'batteryLevel'],
    'signal_strength': ['Signal Strength', None, 'signal', 'signalStrength'],
    'temperature': ['Temperature', TEMP_CELSIUS, 'thermometer', 'temperature'],
    'humidity': ['Humidity', '%', 'water-percent', 'humidity'],
    'air_quality': ['Air Quality', 'ppm', 'biohazard', 'airQuality']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


async def async_setup_platform(hass, config, async_add_entities, _discovery_info=None):
    """Set up an Arlo IP sensor."""
    arlo = hass.data.get(DATA_ARLO)
    if not arlo:
        return

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        if sensor_type == 'total_cameras':
            sensors.append(ArloSensor(arlo, None, sensor_type))
        else:
            for camera in arlo.cameras:
                if camera.has_capability(sensor_type):
                    sensors.append(ArloSensor(arlo, camera, sensor_type))
            for doorbell in arlo.doorbells:
                if doorbell.has_capability(sensor_type):
                    sensors.append(ArloSensor(arlo, doorbell, sensor_type))
            for light in arlo.lights:
                if light.has_capability(sensor_type):
                    sensors.append(ArloSensor(arlo, light, sensor_type))

    async_add_entities(sensors, True)


class ArloSensor(Entity):
    """An implementation of a Netgear Arlo IP sensor."""

    def __init__(self, arlo, device, sensor_type):
        """Initialize an Arlo sensor."""

        sensor_details = SENSOR_TYPES[sensor_type]

        if device is None:
            self._name = sensor_details[0]
            self._unique_id = sensor_type
            self._device = arlo
        else:
            self._name = '{0} {1}'.format(sensor_details[0], device.name)
            self._unique_id = '{0}_{1}'.format(sensor_details[0], device.entity_id).lower().replace(" ", "_")
            self._device = device

        self._sensor_type = sensor_type
        self._icon = 'mdi:{}'.format(sensor_details[2])
        self._state = None
        self._attr = sensor_details[3]
        _LOGGER.info('ArloSensor: %s created', self._name)

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_device, attr, value):
            _LOGGER.debug('callback:' + attr + ':' + str(value)[:80])
            self._state = value
            self.async_schedule_update_ha_state()

        if self._attr is not None:
            self._state = self._device.attribute(self._attr)
            self._device.add_attr_callback(self._attr, update_state)

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self._sensor_type == 'battery_level' and self._state is not None:
            return icon_for_battery_level(battery_level=int(self._state), charging=False)
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return SENSOR_TYPES.get(self._sensor_type)[1]

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        if self._sensor_type == 'temperature':
            return DEVICE_CLASS_TEMPERATURE
        if self._sensor_type == 'humidity':
            return DEVICE_CLASS_HUMIDITY
        return None

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        attrs = {
            ATTR_ATTRIBUTION: CONF_ATTRIBUTION,
            'brand': DEFAULT_BRAND,
            'friendly_name': self._name,

            'device_id': self._device.device_id,
            'model': self._device.model_id,
        }
        return attrs
