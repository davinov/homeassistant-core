"""Tests for the Freebox sensors."""

from copy import deepcopy
from unittest.mock import Mock

from freebox_api.exceptions import HttpRequestError
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant.common import async_fire_time_changed

from homeassistant.components.freebox import SCAN_INTERVAL
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant

from .common import setup_platform
from .const import (
    DATA_CONNECTION_GET_STATUS,
    DATA_HOME_GET_NODES,
    DATA_STORAGE_GET_DISKS,
    DATA_SWITCH_GET_PORT_STATS,
)


async def test_switch_port(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test switch port traffic sensors."""
    await setup_platform(hass, SENSOR_DOMAIN)

    assert hass.states.get(
        "sensor.freebox_server_r2_ethernet_1_receive_rate"
    ).state == ("12.345")
    assert hass.states.get(
        "sensor.freebox_server_r2_ethernet_1_transmit_rate"
    ).state == ("67.89")
    assert hass.states.get("sensor.freebox_server_r2_sfp_lan_receive_rate")

    # Simulate a changed rate
    data_switch_get_port_stats_changed = deepcopy(DATA_SWITCH_GET_PORT_STATS)
    data_switch_get_port_stats_changed["rx_bytes_rate"] = 1000
    router().switch.get_port_stats.return_value = data_switch_get_port_stats_changed
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(
        "sensor.freebox_server_r2_ethernet_1_receive_rate"
    ).state == ("1.0")


async def test_switch_port_not_supported(hass: HomeAssistant, router: Mock) -> None:
    """Test no switch port sensor when the API does not support it."""
    router().switch.get_status.side_effect = HttpRequestError("Request failed")
    await setup_platform(hass, SENSOR_DOMAIN)

    assert hass.states.get("sensor.freebox_server_r2_ethernet_1_receive_rate") is None


async def test_network_speed(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test missed call sensor."""
    await setup_platform(hass, SENSOR_DOMAIN)

    assert hass.states.get("sensor.freebox_server_r2_download_speed").state == "198.9"
    assert hass.states.get("sensor.freebox_server_r2_upload_speed").state == "1440.0"

    # Simulate a changed speed
    data_connection_get_status_changed = deepcopy(DATA_CONNECTION_GET_STATUS)
    data_connection_get_status_changed["rate_down"] = 123400
    data_connection_get_status_changed["rate_up"] = 432100
    router().connection.get_status.return_value = data_connection_get_status_changed
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    # To execute the save
    await hass.async_block_till_done()
    assert hass.states.get("sensor.freebox_server_r2_download_speed").state == "123.4"
    assert hass.states.get("sensor.freebox_server_r2_upload_speed").state == "432.1"


async def test_call(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test missed call sensor."""
    await setup_platform(hass, SENSOR_DOMAIN)

    assert hass.states.get("sensor.freebox_server_r2_missed_calls").state == "3"

    # Simulate we marked calls as read
    data_call_get_calls_marked_as_read = []
    router().call.get_calls_log.return_value = data_call_get_calls_marked_as_read
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    # To execute the save
    await hass.async_block_till_done()
    assert hass.states.get("sensor.freebox_server_r2_missed_calls").state == "0"


async def test_disk(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test disk sensor."""
    await setup_platform(hass, SENSOR_DOMAIN)

    # Initial state
    assert (
        router().storage.get_disks.return_value[2]["partitions"][0]["total_bytes"]
        == 1960000000000
    )

    assert (
        router().storage.get_disks.return_value[2]["partitions"][0]["free_bytes"]
        == 1730000000000
    )

    assert hass.states.get("sensor.disk_3000_freebox_free_space").state == "88.27"

    # Simulate a changed storage size
    data_storage_get_disks_changed = deepcopy(DATA_STORAGE_GET_DISKS)
    data_storage_get_disks_changed[2]["partitions"][0]["free_bytes"] = 880000000000
    router().storage.get_disks.return_value = data_storage_get_disks_changed
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    # To execute the save
    await hass.async_block_till_done()
    assert hass.states.get("sensor.disk_3000_freebox_free_space").state == "44.9"


async def test_temperature(hass: HomeAssistant, router: Mock) -> None:
    """Test temperature sensors expose API names and values."""
    await setup_platform(hass, SENSOR_DOMAIN)

    assert hass.states.get("sensor.freebox_server_r2_disque_dur").state == "40"
    assert hass.states.get("sensor.freebox_server_r2_temperature_switch").state == "50"
    assert hass.states.get("sensor.freebox_server_r2_temperature_cpu_m").state == "60"
    assert hass.states.get("sensor.freebox_server_r2_temperature_cpu_b").state == "56"


async def test_fan(hass: HomeAssistant, router: Mock) -> None:
    """Test fan speed sensors expose API names and values."""
    await setup_platform(hass, SENSOR_DOMAIN)

    assert hass.states.get("sensor.freebox_server_r2_ventilateur_1").state == "2130"


async def test_battery(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test battery sensor."""
    await setup_platform(hass, SENSOR_DOMAIN)

    assert hass.states.get("sensor.telecommande_battery").state == "100"
    assert hass.states.get("sensor.ouverture_porte_battery").state == "100"
    assert hass.states.get("sensor.detecteur_battery").state == "100"

    # Simulate a changed battery
    data_home_get_nodes_changed = deepcopy(DATA_HOME_GET_NODES)
    data_home_get_nodes_changed[2]["show_endpoints"][3]["value"] = 25
    data_home_get_nodes_changed[3]["show_endpoints"][4]["value"] = 50
    data_home_get_nodes_changed[4]["show_endpoints"][5]["value"] = 75
    router().home.get_home_nodes.return_value = data_home_get_nodes_changed
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    # To execute the save
    await hass.async_block_till_done()
    assert hass.states.get("sensor.telecommande_battery").state == "25"
    assert hass.states.get("sensor.ouverture_porte_battery").state == "50"
    assert hass.states.get("sensor.detecteur_battery").state == "75"
