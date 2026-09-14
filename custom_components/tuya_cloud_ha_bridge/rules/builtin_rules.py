"""Project-bundled baseline and override rules.

These rules are shipped with the project so matching can work before any cloud
bundle has been fetched. Cloud bundles can still extend them later.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_BUILTIN_FEATURE_RULES: dict[str, Any] = {
    "attribute_presence": {
        "brightness": "brightness",
        "color_temp": "color_temp",
        "color_temp_kelvin": "color_temp",
        "current_humidity": "humidity_sensor",
        "current_position": "position",
        "current_temperature": "temperature_sensor",
        "direction": "direction",
        "fan_modes": "fan_mode",
        "fan_speed": "fan_mode",
        "fan_speed_list": "fan_mode",
        "hs_color": "color",
        "hvac_modes": "hvac_mode",
        "operation_list": "operation_mode",
        "oscillating": "oscillating",
        "percentage": "percentage",
        "preset_modes": "preset_mode",
        "rgb_color": "color",
        "swing_modes": "swing_mode",
    },
    "device_class_features": {
        "battery": "battery_sensor",
        "co2": "air_quality",
        "energy": "energy_monitor",
        "humidity": "humidity_sensor",
        "pm10": "air_quality",
        "pm25": "air_quality",
        "power": "power_monitor",
        "temperature": "temperature_sensor",
    },
    "domain_attr_features": {
        "climate": {
            "fan_modes": "fan_mode",
            "hvac_modes": "hvac_mode",
            "preset_modes": "preset_mode",
            "swing_modes": "swing_mode",
        },
        "cover": {
            "current_position": "position",
        },
        "fan": {
            "direction": "direction",
            "oscillating": "oscillating",
            "percentage": "percentage",
            "preset_modes": "preset_mode",
        },
        "light": {
            "brightness": "brightness",
            "color_temp_kelvin": "color_temp",
            "hs_color": "color",
        },
    },
    "domain_features": {
        "climate": ["onoff"],
        "cover": ["onoff"],
        "fan": ["onoff"],
        "humidifier": ["onoff"],
        "light": ["onoff"],
        "number": ["numeric_control"],
        "select": ["enum_state"],
        "sensor": [],
        "switch": ["onoff"],
        "vacuum": ["start"],
        "water_heater": ["onoff"],
    },
    "unit_features": [],
    "state_type_features": [],
}

_BUILTIN_COMPONENT_RULES: list[dict[str, Any]] = [
    {"component": "channel_1", "keywords": ["_1", "channel_1", "left"]},
    {"component": "channel_2", "keywords": ["_2", "channel_2", "right"]},
    {"component": "channel_3", "keywords": ["_3", "channel_3"]},
    {"component": "main_brush", "keywords": ["main_brush", "主刷"]},
    {"component": "side_brush", "keywords": ["side_brush", "边刷"]},
    {"component": "filter", "keywords": ["filter", "滤网"]},
    {"component": "battery", "keywords": ["battery", "电量"]},
]

_BUILTIN_PIDSPECS: list[dict[str, Any]] = [
    {
        # Override the generic purifier rule with a fan-centric mapping that
        # matches Xiaomi purifier integrations exposing mode/speed on the fan
        # entity itself.
        "product_id": "wesu2cmngvsc6baa",
        "category_code": "wf_kj",
        "required_domains": ["fan"],
        "optional_domains": ["sensor"],
        "required_any_features": [
            {"domain": "fan", "features": ["onoff"]},
        ],
        "required_dps": ["switch", "mode"],
        "optional_dps": [
            "fan_speed",
            "pm25",
            "humidity",
            "temp_num",
            "filter_life",
            "fault_1",
            "air_quality_1",
        ],
        "ignore_domains": ["switch", "select", "number"],
        "min_domain_coverage": 0.5,
        "disambiguate": {
            "name_keywords": [
                "mi空气",
                "xiaomi.airp",
                "xiaomi.airp.ma6",
                "airp.ma6",
                "净化器",
                "空气净化器",
                "空净",
                "purifier",
                "air purifier",
                "air cleaner",
            ],
            "positive_attrs": ["pm25", "pm10", "preset_modes", "percentage"],
            "negative_attrs": ["direction", "oscillating"],
            "weight": 8,
        },
        "candidate_targets": {
            "switch": [
                {
                    "domain": "fan",
                    "converter": "std:bool_switch",
                    "features": ["onoff"],
                    "converter_config": {},
                    "priority": 100,
                }
            ],
            "mode": [
                {
                    "domain": "fan",
                    "converter": "std:enum_passthrough",
                    "features": ["preset_mode"],
                    "converter_config": {
                        "ha_attr": "preset_mode",
                        "range_attr": "preset_modes",
                        "service": "set_preset_mode",
                        "service_data_key": "preset_mode",
                    },
                    "priority": 100,
                }
            ],
            "fan_speed": [
                {
                    "domain": "fan",
                    "converter": "std:numeric_scale",
                    "features": ["percentage"],
                    "converter_config": {
                        "ha_attr": "percentage",
                        "scale": 1,
                        "fallback": {"min": 0, "max": 100},
                        "service": "set_percentage",
                        "service_data_key": "percentage",
                    },
                    "priority": 100,
                }
            ],
            "pm25": [
                {
                    "domain": "sensor",
                    "converter": "std:numeric_scale",
                    "features": ["air_quality"],
                    "converter_config": {
                        "state_attr": "state",
                        "scale": 1,
                        "default": 0,
                        "round_digits": 0,
                    },
                    "priority": 100,
                }
            ],
            "humidity": [
                {
                    "domain": "sensor",
                    "converter": "std:numeric_scale",
                    "features": ["humidity_sensor"],
                    "converter_config": {
                        "state_attr": "state",
                        "scale": 1,
                        "default": 0,
                        "round_digits": 0,
                    },
                    "priority": 100,
                }
            ],
            "temp_num": [
                {
                    "domain": "sensor",
                    "converter": "std:numeric_scale",
                    "features": ["temperature_sensor"],
                    "converter_config": {
                        "state_attr": "state",
                        "scale": 10,
                        "round_digits": 0,
                    },
                    "priority": 100,
                }
            ],
            "filter_life": [
                {
                    "domain": "sensor",
                    "converter": "std:numeric_scale",
                    "features": [],
                    "converter_config": {
                        "state_attr": "state",
                        "scale": 1,
                        "default": 0,
                        "round_digits": 0,
                    },
                    "priority": 100,
                }
            ],
            "fault_1": [
                {
                    "domain": "sensor",
                    "converter": "std:enum_passthrough",
                    "features": [],
                    "converter_config": {"state_attr": "state"},
                    "priority": 100,
                }
            ],
            "air_quality_1": [
                {
                    "domain": "sensor",
                    "converter": "std:enum_passthrough",
                    "features": [],
                    "converter_config": {"state_attr": "state"},
                    "priority": 100,
                }
            ],
        },
        "dp_definitions": [
            {"dpcode": "switch", "rw": "rw", "type": "bool"},
            {"dpcode": "mode", "rw": "rw", "type": "enum"},
            {"dpcode": "fan_speed", "rw": "rw", "type": "value"},
            {"dpcode": "pm25", "rw": "ro", "type": "value"},
            {"dpcode": "humidity", "rw": "ro", "type": "value"},
            {"dpcode": "temp_num", "rw": "ro", "type": "value"},
            {
                "dpcode": "filter_life",
                "rw": "ro",
                "type": "value",
                "match_hints": {
                    "preferred_keywords": ["filter_life", "剩余寿命"],
                    "excluded_keywords": ["used_time", "已使用", "left_time", "剩余时间"],
                },
            },
            {
                "dpcode": "fault_1",
                "rw": "ro",
                "type": "string",
                "match_hints": {
                    "preferred_keywords": ["fault", "故障"],
                    "excluded_keywords": ["air_quality", "空气质量"],
                },
            },
            {
                "dpcode": "air_quality_1",
                "rw": "ro",
                "type": "string",
                "match_hints": {
                    "preferred_keywords": ["air_quality", "空气质量"],
                    "excluded_keywords": ["fault", "故障", "pm"],
                },
            },
        ],
    },
    {
        # Override the BLE purifier rule so fan-centric Xiaomi purifiers do not
        # tie with the generic switch+select variant during disambiguation.
        "product_id": "wyjyiyywcfdhflde",
        "category_code": "wf_ble_kj",
        "required_domains": ["switch"],
        "optional_domains": ["select", "sensor"],
        "required_any_features": [
            {"domain": "switch", "features": ["onoff"]},
            {"domain": "sensor", "features": ["air_quality"]},
        ],
        "required_dps": ["switch", "mode_1"],
        "optional_dps": [
            "pm25",
            "filter_life",
            "humidity",
            "filter_days",
            "temp_num",
            "temp_unit",
            "fault_1",
            "air_quality_1",
        ],
        "ignore_domains": ["number", "button", "event"],
        "disambiguate": {
            "name_keywords": [
                "空气净化器",
                "净化器",
                "空净",
                "purifier",
                "air purifier",
                "air cleaner",
            ],
            "positive_attrs": [],
            "negative_attrs": ["preset_modes", "percentage"],
            "weight": -2,
        },
        "candidate_targets": {
            "switch": [
                {
                    "domain": "switch",
                    "converter": "std:bool_switch",
                    "features": ["onoff"],
                    "converter_config": {},
                    "priority": 100,
                }
            ],
            "mode_1": [
                {
                    "domain": "select",
                    "converter": "std:enum_passthrough",
                    "features": [],
                    "converter_config": {
                        "range_attr": "options",
                        "service": "select_option",
                        "service_data_key": "option",
                        "state_attr": "state",
                    },
                    "priority": 100,
                }
            ],
            "pm25": [
                {
                    "domain": "sensor",
                    "converter": "std:numeric_scale",
                    "features": ["air_quality"],
                    "converter_config": {
                        "state_attr": "state",
                        "scale": 1,
                        "default": 0,
                        "round_digits": 0,
                    },
                    "priority": 100,
                }
            ],
            "filter_life": [
                {
                    "domain": "sensor",
                    "converter": "std:numeric_scale",
                    "features": [],
                    "converter_config": {
                        "state_attr": "state",
                        "scale": 1,
                        "default": 0,
                        "round_digits": 0,
                    },
                    "priority": 100,
                }
            ],
            "humidity": [
                {
                    "domain": "sensor",
                    "converter": "std:numeric_scale",
                    "features": ["humidity_sensor"],
                    "converter_config": {
                        "state_attr": "state",
                        "scale": 1,
                        "default": 0,
                        "round_digits": 0,
                    },
                    "priority": 100,
                }
            ],
            "filter_days": [
                {
                    "domain": "sensor",
                    "converter": "std:numeric_scale",
                    "features": [],
                    "converter_config": {
                        "state_attr": "state",
                        "scale": 1,
                        "default": 0,
                        "round_digits": 0,
                    },
                    "priority": 100,
                }
            ],
            "temp_num": [
                {
                    "domain": "sensor",
                    "converter": "std:numeric_scale",
                    "features": ["temperature_sensor"],
                    "converter_config": {
                        "state_attr": "state",
                        "scale": 10,
                        "round_digits": 0,
                    },
                    "priority": 100,
                }
            ],
            "temp_unit": [
                {
                    "domain": "sensor",
                    "converter": "std:enum_passthrough",
                    "features": ["temperature_sensor"],
                    "converter_config": {
                        "ha_attr": "unit_of_measurement",
                        "value_map": {"c": "°C", "f": "°F"},
                    },
                    "priority": 100,
                }
            ],
            "fault_1": [
                {
                    "domain": "sensor",
                    "converter": "std:enum_passthrough",
                    "features": [],
                    "converter_config": {"state_attr": "state"},
                    "priority": 100,
                }
            ],
            "air_quality_1": [
                {
                    "domain": "sensor",
                    "converter": "std:enum_passthrough",
                    "features": [],
                    "converter_config": {"state_attr": "state"},
                    "priority": 100,
                }
            ],
        },
        "dp_definitions": [
            {
                "dpcode": "switch",
                "rw": "rw",
                "type": "bool",
                "match_hints": {
                    "preferred_keywords": ["开关", "_on_"],
                    "excluded_keywords": [
                        "提示音",
                        "alarm",
                        "童锁",
                        "物理控制",
                        "physical_controls_locked",
                    ],
                },
            },
            {
                "dpcode": "mode_1",
                "rw": "rw",
                "type": "string",
                "match_hints": {
                    "preferred_keywords": ["mode", "模式", "工作模式"],
                    "excluded_keywords": ["亮度", "brightness", "显示屏", "风机", "档位", "fan_level"],
                },
            },
            {"dpcode": "pm25", "rw": "ro", "type": "value"},
            {
                "dpcode": "filter_life",
                "rw": "ro",
                "type": "value",
                "match_hints": {
                    "preferred_keywords": ["filter_life", "剩余寿命"],
                    "excluded_keywords": ["已使用", "used", "剩余时间", "left_time"],
                },
            },
            {"dpcode": "humidity", "rw": "ro", "type": "value"},
            {
                "dpcode": "filter_days",
                "rw": "ro",
                "type": "value",
                "match_hints": {
                    "preferred_keywords": ["filter_left", "剩余时间"],
                    "excluded_keywords": ["寿命", "life", "已使用", "used_time"],
                },
            },
            {"dpcode": "temp_num", "rw": "ro", "type": "value"},
            {"dpcode": "temp_unit", "rw": "ro", "type": "enum"},
            {
                "dpcode": "fault_1",
                "rw": "ro",
                "type": "string",
                "match_hints": {
                    "preferred_keywords": ["fault", "故障"],
                    "excluded_keywords": ["air_quality", "空气质量"],
                },
            },
            {
                "dpcode": "air_quality_1",
                "rw": "ro",
                "type": "string",
                "match_hints": {
                    "preferred_keywords": ["air_quality", "空气质量"],
                    "excluded_keywords": ["fault", "故障", "pm"],
                },
            },
        ],
    },
]


def get_builtin_bundle() -> dict[str, Any]:
    """Return the project-bundled baseline bundle."""
    return {
        "rule_version": 0,
        "pidspecs": deepcopy(_BUILTIN_PIDSPECS),
        "feature_rules": deepcopy(_BUILTIN_FEATURE_RULES),
        "component_rules": deepcopy(_BUILTIN_COMPONENT_RULES),
    }


def merge_with_builtin_bundle(bundle: dict[str, Any] | None) -> dict[str, Any]:
    """Merge a cloud/local bundle with the project-bundled baseline rules.

    Built-in pidspecs override matching cloud/local entries keyed by
    ``(product_id, category_code)`` so targeted local fixes win deterministically.
    """
    merged = get_builtin_bundle()
    if not isinstance(bundle, dict):
        return merged

    merged["rule_version"] = bundle.get("rule_version", 0)

    raw_fr = bundle.get("feature_rules")
    if isinstance(raw_fr, dict):
        merged_fr = merged["feature_rules"]
        for key in (
            "attribute_presence",
            "device_class_features",
            "domain_features",
            "domain_attr_features",
        ):
            value = raw_fr.get(key)
            if isinstance(value, dict):
                merged_fr[key].update(value)
        for key in ("unit_features", "state_type_features"):
            value = raw_fr.get(key)
            if isinstance(value, list) and value:
                merged_fr[key] = value

    seen_components: set[tuple[str, tuple[str, ...]]] = set()
    component_rules: list[dict[str, Any]] = []
    for item in list(merged["component_rules"]) + list(bundle.get("component_rules") or []):
        if not isinstance(item, dict):
            continue
        component = str(item.get("component", ""))
        keywords = tuple(str(keyword) for keyword in item.get("keywords") or [])
        key = (component, keywords)
        if not component or key in seen_components:
            continue
        seen_components.add(key)
        component_rules.append(deepcopy(item))
    merged["component_rules"] = component_rules

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for item in bundle.get("pidspecs") or []:
        if not isinstance(item, dict):
            continue
        key = (str(item.get("product_id", "")), str(item.get("category_code", "")))
        by_key[key] = deepcopy(item)
    for item in _BUILTIN_PIDSPECS:
        key = (item["product_id"], item["category_code"])
        by_key[key] = deepcopy(item)
    merged["pidspecs"] = list(by_key.values())

    return merged
