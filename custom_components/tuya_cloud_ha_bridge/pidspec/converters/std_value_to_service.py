"""std:value_to_service / std:enum_command converters.

Maps Tuya enum values to specific HA service calls.
Used for devices like vacuum where each command maps to a distinct service.

converter_config options (std:value_to_service):
- value_map: {tuya_enum_value: "domain.service"} (e.g. {"start": "vacuum.start"})
- state_map: {"ha_state": "tuya_value"} reverse mapping for to_tuya
"""

from __future__ import annotations

from typing import Any


class StdValueToService:

    def to_ha_service(
        self,
        tuya_value: Any,
        config: dict[str, Any],
        entity_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if tuya_value is None:
            return None

        value_map = config.get("value_map", {})
        service_ref = value_map.get(str(tuya_value))
        if not service_ref:
            return None

        parts = service_ref.split(".", 1)
        if len(parts) != 2:
            return None

        domain, service = parts
        return {
            "domain": domain,
            "service": service,
            "service_data": {"entity_id": entity_id},
        }

    def to_tuya_value(
        self,
        ha_state: dict[str, Any],
        ha_attributes: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        state_map = config.get("state_map")
        if state_map:
            state = ha_state.get("state", "")
            return state_map.get(state)

        # Auto-reverse from value_map: find which tuya value maps to a
        # service matching the current HA state
        value_map = config.get("value_map", {})
        state = ha_state.get("state", "")
        for tuya_val, service_ref in value_map.items():
            if service_ref.endswith(f".{state}") or tuya_val == state:
                return tuya_val

        return None


class StdEnumCommand:
    """std:enum_command converter.

    Maps a Tuya enum value to a COMPLETE HA service call, including arguments.
    ``std:value_to_service`` only picks a service (its ``service_data`` carries
    just ``entity_id``) and ``std:enum_passthrough`` maps a Tuya value to a
    service NAME while passing the value through verbatim — neither can express
    "value A → service with these args, value B → same service with other args".
    That is what a fan folding its speed steps into one mode enum needs, e.g.
    自动 → ``fan.turn_on`` {preset_mode: 自动} vs 一档 → ``fan.turn_on``
    {preset_mode: 挡位, percentage: 33}.

    converter_config options:
    - service: HA service called for every mapped value (default "turn_on").
      The target domain is derived from the bound entity_id.
    - forward: {tuya_value: {key: value, ...}} — extra ``service_data`` merged
      into the call. A Tuya value absent from the map dispatches nothing.
    - reverse_attr: entity attribute read for the reverse mapping
      (default "preset_mode").
    - reverse: {ha_value: tuya_value} — exact reverse mapping on ``reverse_attr``.
    - gear: {"preset": <ha_value>, "attr": "percentage",
             "levels": [[tuya_value, target], ...]} — fallback used when
      ``reverse_attr`` equals ``preset``: report the tuya value whose target is
      closest to the current ``attr`` value.
    - fallback: {"range": [...]} — declares the enum range to the cloud (Tuya
      rejects values outside it); also feeds the bind-time default.
    - default: default Tuya value when no reverse rule matches.
    """

    def to_ha_service(
        self,
        tuya_value: Any,
        config: dict[str, Any],
        entity_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if tuya_value is None:
            return None

        forward = config.get("forward")
        if not isinstance(forward, dict):
            return None

        data = forward.get(str(tuya_value))
        if not isinstance(data, dict):
            return None

        service = config.get("service", "turn_on")
        if not service:
            return None

        domain = entity_id.split(".")[0] if "." in entity_id else "switch"
        service_data: dict[str, Any] = {"entity_id": entity_id}
        service_data.update(data)
        return {"domain": domain, "service": service, "service_data": service_data}

    def to_tuya_value(
        self,
        ha_state: dict[str, Any],
        ha_attributes: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        attr = config.get("reverse_attr", "preset_mode")
        current = ha_attributes.get(attr)

        reverse = config.get("reverse")
        if isinstance(reverse, dict) and current is not None:
            if str(current) in reverse:
                return reverse[str(current)]

        gear = config.get("gear")
        if (
            isinstance(gear, dict)
            and current is not None
            and str(current) == str(gear.get("preset"))
        ):
            gear_attr = gear.get("attr", "percentage")
            levels = gear.get("levels") or []
            value = _as_number(ha_attributes.get(gear_attr))
            if value is None:
                return config.get("default")
            best_value: Any = None
            best_distance: float | None = None
            for item in levels:
                try:
                    tuya_value, target = item
                except (TypeError, ValueError):
                    continue
                target_num = _as_number(target)
                if target_num is None:
                    continue
                distance = abs(value - target_num)
                if best_distance is None or distance < best_distance:
                    best_value, best_distance = tuya_value, distance
            return best_value if best_value is not None else config.get("default")

        return config.get("default")


def _as_number(value: Any) -> float | None:
    """Return *value* as a float, or None when absent/not numeric."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
