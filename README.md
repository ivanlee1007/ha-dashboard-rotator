# ha-dashboard-rotator

Home Assistant custom integration that rotates Lovelace dashboard views on a timed interval.

## What it does

- Rotates dashboard tabs/views by configured seconds
- Uses a frontend controller loaded globally by the integration
- Supports per-view intervals
- Pauses when the page is hidden
- Pauses temporarily after manual interaction
- Exposes HA entities, services, and an optional status card

## Current MVP scope

This first implementation supports **one config entry / one dashboard profile**.

That profile contains:

- dashboard base path
- enabled switch
- default interval
- pause-after-interaction seconds
- start delay
- views JSON list

## Why this is an integration + frontend controller

Dashboard tab switching is a **browser UI action**, not a pure backend action.

So the architecture is:

- **Backend integration**: stores config, exposes services/entities
- **Frontend controller JS**: watches the current route and navigates between configured views
- **Optional status card**: shows current runtime state and manual controls

## Installation

### Manual

Copy this folder into:

```text
config/custom_components/dashboard_rotator
```

Restart Home Assistant.

Then add the integration from **Settings → Devices & Services**.

## Configuration

The profile uses a JSON array for views.

Example:

```json
[
  {
    "path": "/lovelace-uninus/home",
    "seconds": 10,
    "title": "Home"
  },
  {
    "path": "/lovelace-uninus/weather",
    "seconds": 20,
    "title": "Weather"
  },
  {
    "path": "/lovelace-uninus/power",
    "seconds": 15,
    "title": "Power"
  }
]
```

Rules:

- every view `path` must start with the configured `dashboard_path`
- `seconds` must be > 0
- at least one view must be enabled

## Entities

- `sensor.dashboard_rotator_runtime`
- `switch.dashboard_rotator_enabled`
- `button.dashboard_rotator_pause`
- `button.dashboard_rotator_resume`
- `button.dashboard_rotator_next_view`
- `button.dashboard_rotator_previous_view`

> Actual entity IDs include the config entry slug created by Home Assistant.

## Services

- `dashboard_rotator.pause`
- `dashboard_rotator.resume`
- `dashboard_rotator.next_view`
- `dashboard_rotator.previous_view`
- `dashboard_rotator.jump_to_view`

## Optional status card

Because the integration registers a global frontend module, it also exposes this card:

```yaml
type: custom:dashboard-rotator-status
```

Optional explicit entity:

```yaml
type: custom:dashboard-rotator-status
entity: sensor.dashboard_rotator_runtime
```

## How rotation works

1. The integration loads a frontend module on HA pages.
2. The controller looks for the runtime sensor.
3. When the browser is on the configured dashboard path, it starts a timer.
4. When the timer expires, it navigates to the next configured view.
5. Manual interaction pauses rotation for the configured number of seconds.
6. Hidden/background pages pause when `only_when_visible` is enabled.

## Known MVP limitations

- single profile only
- last client wins for the runtime heartbeat sensor attributes
- no per-client targeting yet
- no visual config editor for the views list yet; it is JSON-based for now

## Planned next steps

- multi-profile support
- cleaner views editor UI
- per-client target mode (kiosk/tablet specific)
- schedules
- random / ping-pong rotation modes

## License

MIT
