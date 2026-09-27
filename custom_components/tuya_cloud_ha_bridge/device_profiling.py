"""Device profiling — builds DeviceProfile from HA device/entity registry.

Collects all entity information for a device and constructs the
DeviceProfile needed by the pidspec inference engine.

Public API:
- async_build_device_profile(hass, device_id, rule_cache) → DeviceProfile
- async_build_all_device_profiles(hass, device_ids, rule_cache) → dict[device_id, DeviceProfile]
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .pidspec.entity_filter import INFERENCE_EXCLUDED_DOMAINS, should_include_entity
from .pidspec.features import discover_features
from .pidspec.components import discover_component
from .pidspec.models import (
    DeviceProfile,
    EntityProfile,
    FeatureRules,
    LocalBaselineComponentRules,
)
from .pidspec.rule_cache import LocalRuleCache
from .const import LOGGER


def _get_entity_state_attributes(
    hass: HomeAssistant, entity_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (state_dict, attributes_dict) for an entity."""
    state = hass.states.get(entity_id)
    if state is None:
        return {"state": ""}, {}
    return {"state": state.state}, dict(state.attributes)


def _entity_is_readable(domain: str) -> bool:
    """Most HA entities are readable (have state)."""
    return True


def _entity_is_writable(domain: str) -> bool:
    """Entities in these domains support service calls (commands)."""
    return domain in {
        "switch", "light", "fan", "climate", "cover",
        "humidifier", "vacuum", "water_heater", "media_player",
        "lock", "siren", "valve", "button", "number", "select",
    }


def _build_entity_profile(
    hass: HomeAssistant,
    entity_entry: er.RegistryEntry,
    feature_rules: FeatureRules,
    local_component_rules: LocalBaselineComponentRules | None,
) -> EntityProfile:
    """Construct an EntityProfile from an HA entity registry entry."""
    entity_id = entity_entry.entity_id
    domain = entity_entry.domain
    integration = entity_entry.platform or ""

    state = hass.states.get(entity_id)
    attributes: dict[str, Any] = dict(state.attributes) if state else {}
    state_value = state.state if state else ""

    # Extract supported_features int
    ha_features_int = attributes.get("supported_features")
    if not isinstance(ha_features_int, int):
        ha_features_int = None

    # Determine device_class, state_class, entity_category
    device_class = (
        entity_entry.device_class
        or entity_entry.original_device_class
        or attributes.get("device_class")
    )
    state_class = attributes.get("state_class")
    entity_category = (
        entity_entry.entity_category.value if entity_entry.entity_category else None
    )

    # Build initial profile (component will be filled in below)
    profile = EntityProfile(
        entity_id=entity_id,
        domain=domain,
        integration=integration,
        friendly_name=entity_entry.name or entity_entry.original_name or "",
        original_name=entity_entry.original_name or "",
        unique_id=entity_entry.unique_id or "",
        device_class=device_class,
        state_class=state_class,
        entity_category=entity_category,
        unit=attributes.get("unit_of_measurement"),
        state_type=type(state_value).__name__ if state_value else "",
        readable=_entity_is_readable(domain),
        writable=_entity_is_writable(domain),
        notifiable=True,
        attributes=attributes,
        ha_supported_features_int=ha_features_int,
        supported_features=set(),
        component="",
        component_source="",
    )

    # Discover features using rules
    profile.supported_features = discover_features(profile, feature_rules)

    # Discover component
    if local_component_rules is not None:
        component, component_source = discover_component(
            profile, local_component_rules
        )
        profile.component = component
        profile.component_source = component_source
    else:
        profile.component = f"entity:{entity_id}"
        profile.component_source = "entity_fallback"

    return profile


def async_build_device_profile(
    hass: HomeAssistant,
    device_id: str,
    rule_cache: LocalRuleCache,
    local_component_rules: LocalBaselineComponentRules | None = None,
) -> DeviceProfile | None:
    """Build a DeviceProfile for a single HA device.

    Returns None if the device doesn't exist or has no entities.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    device = device_registry.async_get(device_id)
    if device is None:
        return None

    entity_entries = er.async_entries_for_device(entity_registry, device_id)
    if not entity_entries:
        return None

    entity_profiles: list[EntityProfile] = []
    domains: set[str] = set()

    for entry in entity_entries:
        if entry.disabled_by is not None:
            continue

        # Build a temporary EntityProfile (without features/component yet)
        # so we can run the global inclusion filter before doing extra work.
        temp_profile = EntityProfile(
            entity_id=entry.entity_id,
            domain=entry.domain,
            integration=entry.platform or "",
            friendly_name=entry.name or entry.original_name or "",
            original_name=entry.original_name or "",
            unique_id=entry.unique_id or "",
            # entry.device_class 是用户覆盖值，集成默认的 device_class 在
            # original_device_class；diagnostic 白名单依赖真实 device_class，
            # 必须 fallback，否则 battery/tamper 等实体会被当作 None 过滤掉。
            device_class=entry.device_class or entry.original_device_class,
            state_class=None,
            entity_category=(
                entry.entity_category.value if entry.entity_category else None
            ),
            unit=None,
            state_type="",
            readable=True,
            writable=entry.domain in {
                "switch", "light", "fan", "climate", "cover",
                "humidifier", "vacuum", "water_heater", "media_player",
                "lock", "siren", "valve", "button", "number", "select",
            },
            notifiable=True,
            attributes={},
            ha_supported_features_int=None,
            supported_features=set(),
            component="",
            component_source="",
        )

        # Global filter: EXCLUDED_DOMAINS / EXCLUDED_CATEGORIES /
        # CONDITIONAL_DOMAINS (default-excluded).
        # NOTE: At construction time we don't know which PidSpec will match,
        # so CONDITIONAL_DOMAINS is excluded unconditionally here. The report
        # serialization layer applies the same filter on the way out as a
        # safety net.
        if not should_include_entity(temp_profile):
            continue

        profile = _build_entity_profile(
            hass, entry, rule_cache.feature_rules, local_component_rules
        )
        entity_profiles.append(profile)
        # Inference-excluded domains (e.g. button) are kept in the profile so a
        # matched spec's DPs can still route to them, but MUST stay out of
        # domain_set so they never influence PID inference / scoring.
        if entry.domain not in INFERENCE_EXCLUDED_DOMAINS:
            domains.add(entry.domain)

    if not entity_profiles:
        return None

    return DeviceProfile(
        device_id=device_id,
        name=device.name_by_user or device.name or device_id,
        model=device.model or "",
        manufacturer=device.manufacturer or "",
        entity_profiles=entity_profiles,
        domain_set=frozenset(domains),
    )


# Attributes that merely duplicate a dedicated top-level key above (or are UI
# noise) and are therefore dropped from the raw ``attributes`` dump.
_DUMP_SKIPPED_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "friendly_name",
        "icon",
        "entity_picture",
        "attribution",
        "supported_features",
    }
)

# Chinese, self-documenting legend shipped inside every dump (``field_notes``)
# so a copied definition list stays readable long after it was exported.
# Keys are dotted paths; ``entities[]`` prefixes entity-level fields.
_DEFINITION_FIELD_NOTES: dict[str, str] = {
    "device_id": "HA 设备注册表 ID（device registry 的唯一 id）",
    "name": "设备显示名（用户在 HA 里重命名后的名字优先）",
    "name_by_user": "用户在 HA 中的重命名；未重命名为 null",
    "model": "设备型号（集成上报的 model）",
    "manufacturer": "设备厂商",
    "integrations": "提供该设备实体的集成（platform），如 xiaomi_home",
    "domains": "设备包含的实体 domain 集合，对应 pidspec.required_domains / optional_domains 的判断依据",
    "entity_count": "实体总数（包含已禁用实体）",
    "entities": "实体定义列表（包含已禁用实体，便于排查“为什么规则看不到某实体”）",
    "field_notes": "本说明本身：清单各字段含义对照表",
    "entities[].entity_id": "实体 ID（domain.object_id），DP 路由最终绑定的对象",
    "entities[].domain": "HA domain（switch/select/sensor/number/fan…），对应 candidate_targets.domain",
    "entities[].integration": "提供该实体的集成（platform）",
    "entities[].name": "实体名（用户重命名优先）",
    "entities[].original_name": "集成给出的原始名，常含厂商语义，写 match_hints 关键词时重点参考",
    "entities[].unique_id": "该实体在集成内的唯一 ID",
    "entities[].device_class": "HA 设备类别（如 temperature / humidity / pm25），特性识别与 match_hints 的参考",
    "entities[].original_device_class": "集成原始 device_class（未被用户覆盖的值）",
    "entities[].state_class": "统计类别（measurement / total 等），一般仅统计用途",
    "entities[].entity_category": "实体分类；diagnostic / config 默认会被引擎过滤",
    "entities[].disabled_by": "禁用来源；非 null 表示实体已禁用，通常不参与路由",
    "entities[].unit_of_measurement": "状态单位（°C、μg/m³ 等）",
    "entities[].supported_features_int": "HA 原始 supported_features 位掩码（集成声明的能力位）",
    "entities[].state": "当前状态值（判断 select 选项、number 范围、开关状态等）",
    "entities[].attributes": "当前全部属性（含 options / min / max / step / fan_modes 等，写 value_map 时重点参考）；已移除 friendly_name、icon、entity_picture、attribution、supported_features 这些重复或噪音字段",
    "entities[].features": "规则引擎解析出的语义特性（如 onoff / fan_mode / air_quality），candidate_targets.features 用它匹配",
    "entities[].component": "组件标识，用于 component_hint 与多通道（channel_x）区分",
    "entities[].component_source": "component 的来源；entity_fallback 表示未命中 component_rules，带 component_hint 的 DP 不会绑到它",
    "entities[].writable": "是否可写，决定该实体能否作为下发（控制）类 DP 的载体",
    "entities[].included": "是否通过全局实体过滤；false 表示引擎完全不会考虑该实体",
}


def _dump_entity_definition(
    hass: HomeAssistant,
    entry: er.RegistryEntry,
    feature_rules: FeatureRules | None,
) -> dict[str, Any]:
    """Build one entity's definition entry for the device dump.

    Includes both the raw registry/state data and — when *feature_rules* is
    available — the derived values the rule engine actually matches on
    (semantic ``features``, ``component`` and whether the entity survives the
    global inclusion filter).
    """
    state = hass.states.get(entry.entity_id)
    attributes: dict[str, Any] = dict(state.attributes) if state else {}
    supported_features_int = attributes.get("supported_features")

    item: dict[str, Any] = {
        "entity_id": entry.entity_id,
        "domain": entry.domain,
        "integration": entry.platform or "",
        "name": entry.name,
        "original_name": entry.original_name,
        "unique_id": entry.unique_id,
        "device_class": entry.device_class or entry.original_device_class,
        "original_device_class": entry.original_device_class,
        "state_class": attributes.get("state_class"),
        "entity_category": (
            entry.entity_category.value if entry.entity_category else None
        ),
        "disabled_by": entry.disabled_by.value if entry.disabled_by else None,
        "unit_of_measurement": attributes.get("unit_of_measurement"),
        "supported_features_int": (
            supported_features_int if isinstance(supported_features_int, int) else None
        ),
        "state": state.state if state else None,
        "attributes": {
            key: value
            for key, value in attributes.items()
            if key not in _DUMP_SKIPPED_ATTRIBUTES
        },
    }

    if feature_rules is not None:
        profile = _build_entity_profile(hass, entry, feature_rules, None)
        item["features"] = sorted(profile.supported_features)
        item["component"] = profile.component
        item["component_source"] = profile.component_source
        item["writable"] = profile.writable
        item["included"] = should_include_entity(profile)

    return item


def device_definition_field_notes_text() -> str:
    """Return the dump field legend as Markdown for the options-flow help page."""
    lines = ["| 字段 | 含义 |", "| --- | --- |"]
    lines.extend(
        f"| `{key}` | {note} |" for key, note in _DEFINITION_FIELD_NOTES.items()
    )
    return "\n".join(lines)


def build_device_definition_dump(
    hass: HomeAssistant,
    device_id: str,
    rule_cache: LocalRuleCache | None = None,
) -> dict[str, Any] | None:
    """Build a raw + derived entity definition dump for a single device.

    Backs the options-flow "device definitions" viewer: the user picks a device
    and copies the returned JSON so rule authors can see exactly what HA
    exposes (entity ids, domains, feature flags, components, current states)
    without reading the raw registry.

    Returns None when the device does not exist or exposes no entities.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    device = device_registry.async_get(device_id)
    if device is None:
        return None

    entity_entries = sorted(
        er.async_entries_for_device(
            entity_registry, device_id, include_disabled_entities=True
        ),
        key=lambda entry: entry.entity_id,
    )
    if not entity_entries:
        return None

    feature_rules = rule_cache.feature_rules if rule_cache is not None else None
    entities = [
        _dump_entity_definition(hass, entry, feature_rules)
        for entry in entity_entries
    ]

    return {
        "device_id": device_id,
        "name": device.name_by_user or device.name or device_id,
        "name_by_user": device.name_by_user,
        "model": device.model or "",
        "manufacturer": device.manufacturer or "",
        "integrations": sorted(
            {entry.platform for entry in entity_entries if entry.platform}
        ),
        "domains": sorted({entry.domain for entry in entity_entries}),
        "entity_count": len(entities),
        "entities": entities,
        "field_notes": dict(_DEFINITION_FIELD_NOTES),
    }


def async_build_all_device_profiles(
    hass: HomeAssistant,
    device_ids: list[str],
    rule_cache: LocalRuleCache,
    local_component_rules: LocalBaselineComponentRules | None = None,
) -> dict[str, DeviceProfile]:
    """Build DeviceProfiles for multiple devices.

    Returns a dict keyed by device_id (only includes devices with profiles).
    """
    profiles: dict[str, DeviceProfile] = {}

    for device_id in device_ids:
        profile = async_build_device_profile(
            hass, device_id, rule_cache, local_component_rules
        )
        if profile is not None:
            profiles[device_id] = profile

    return profiles
