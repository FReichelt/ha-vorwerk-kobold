# Vorwerk Kobold for Home Assistant

[![HACS Validation](https://github.com/FReichelt/ha-vorwerk-kobold/actions/workflows/hacs-validate.yaml/badge.svg)](https://github.com/FReichelt/ha-vorwerk-kobold/actions/workflows/hacs-validate.yaml)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

Custom integration for Vorwerk Kobold robot vacuums (VR300/VR220) using the MyKobold cloud API.

## Installation via HACS (recommended)

1. Make sure [HACS](https://hacs.xyz) is installed in your Home Assistant.
2. Go to **HACS → Integrations → ⋮ (top right) → Custom repositories**.
3. Add `https://github.com/FReichelt/ha-vorwerk-kobold` and select category **Integration**.
4. Click **Add**, then find **Vorwerk Kobold** in the list and install it.
5. Restart Home Assistant.

### One-click install

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FReichelt&repository=ha-vorwerk-kobold&category=integration)

## Manual installation

Copy `custom_components/kobold/` into your HA config directory:
```
/config/custom_components/kobold/
```
Restart Home Assistant.

## Configuration

After installation go to **Settings → Devices & Services → Add Integration** and search for **Kobold**.

Authentication uses the MyKobold passwordless email OTP flow — no password needed:
1. Enter your MyKobold account e-mail address.
2. Enter the one-time code sent to that address.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `vacuum.<name>` | Vacuum | Main vacuum entity — start, pause, stop, dock, locate, spot clean |
| `sensor.<name>_battery` | Sensor | Battery level (%) |
| `switch.<name>_schedule` | Switch | Enable / disable the cleaning schedule |
| `camera.<name>_cleaning_map` | Camera | Last cleaning map image |
| `button.<name>_find_me` | Button | Play locator sound |
| `button.<name>_dismiss_alert` | Button | Dismiss active robot alert |

## Services

### `kobold.custom_cleaning`
Start a cleaning run with explicit mode, navigation, and map options.

| Field | Description |
|-------|-------------|
| `cleaning_mode` | `Eco` or `Turbo` (default: Turbo) |
| `navigation_mode` | `Normal`, `Extra Care`, or `Deep` (default: Normal) |
| `category` | `2` = non-persistent map, `4` = persistent map |
| `boundary_id` | Zone boundary ID from a persistent map |
| `map_id` | Persistent map ID |

### `kobold.set_schedule`
Replace the robot's entire cleaning schedule.

```yaml
service: kobold.set_schedule
target:
  entity_id: switch.fifi_cleaning_schedule
data:
  events:
    - day: 1        # Monday
      mode: Turbo
      start_time: "08:00"
    - day: 5        # Friday
      mode: Eco
      start_time: "10:30"
```
Pass `events: []` to clear all scheduled cleanings.

### `kobold.add_schedule_event`
Add or overwrite the event for one specific day.

```yaml
service: kobold.add_schedule_event
target:
  entity_id: switch.fifi_cleaning_schedule
data:
  day: 3          # Wednesday
  mode: Turbo
  start_time: "09:00"
```

### `kobold.remove_schedule_event`
Remove the event for one specific day.

```yaml
service: kobold.remove_schedule_event
target:
  entity_id: switch.fifi_cleaning_schedule
data:
  day: 3          # Wednesday
```

Day numbering: `0` = Sunday, `1` = Monday … `6` = Saturday.

### `vacuum.send_command`
Send a raw command to the robot (for advanced use and testing).

```yaml
service: vacuum.send_command
target:
  entity_id: vacuum.fifi
data:
  command: driveManual
  params:
    velocity: 0.2     # m/s, range -0.3 to 0.3
    twist: 0.0        # rad/s, range -1.0 to 1.0
    brakeOnStop: false
```

## Schedule attributes

The schedule switch exposes current events as state attributes:

```yaml
schedule_events:
  - day: Friday
    day_number: 5
    mode: Eco
    start_time: "21:41"
```

## Author

**Florian Reichelt** — [github@florian-reichelt.de](mailto:github@florian-reichelt.de) · [@FReichelt](https://github.com/FReichelt)

Licensed under the [MIT License](LICENSE.md).
