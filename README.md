# ha-dashboard-rotator

Home Assistant custom integration that rotates Lovelace dashboard views on a timed interval.

Current version: `0.1.25`

Chinese manual / 中文使用說明：[`README.zh-TW.md`](./README.zh-TW.md)

## What it does

- Rotates dashboard tabs/views by configured seconds
- Uses a frontend controller loaded globally by the integration
- Supports per-view intervals
- Pauses when the page is hidden
- Pauses temporarily after manual interaction
- Exposes HA entities, services, and an optional status card
- Includes built-in Traditional Chinese (`zh-Hant`) translations for config/options flows
- Status card auto-localizes common labels when HA is using Traditional Chinese

## Current MVP scope

This first implementation supports **one config entry / one dashboard profile**.

That profile contains:

- dashboard base path
- enabled switch
- default interval
- pause-after-interaction seconds
- start delay
- target client picker
- client management UI
- client details view
- client aliases JSON fallback
- views GUI editor
- views JSON fallback (advanced)

Both the initial setup flow and the post-install options flow now use the same GUI-style editor.

The options flow also includes a client-management step for choosing or clearing the target client, inspecting client details, editing or clearing per-client aliases, and reading clearer presence / last-seen hints without touching raw JSON.

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

Optional profile fields:

- `target_client_id`: if set, only that specific browser client/tab will auto-rotate
- `client_aliases_json`: optional `{ client_id: alias }` map for friendly labels

You can discover active client IDs from the runtime sensor attributes or the optional status card.

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
- `dashboard_rotator.set_client_alias`

All command services support an optional `target_client_id` field.

Example:

```yaml
service: dashboard_rotator.pause
data:
  target_client_id: dr-abc12345
```

Set or clear an alias:

```yaml
service: dashboard_rotator.set_client_alias
data:
  client_id: dr-abc12345
  alias: lobby-tablet
```

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

Optional explicit enabled switch override:

```yaml
type: custom:dashboard-rotator-status
entity: sensor.uninus_dashboard_rotator_test_runtime
enabled_entity: switch.uninus_dashboard_rotator_test_enabled
```

The status card shows:

- rotator enabled/disabled state
- inline HA-style rotator switch toggle
- current browser client ID (for matching this card to a kiosk/browser)
- one-click "Add to targets" and "Clear targets" buttons on the status card
- per-client status-card buttons to add/remove each client from targets directly
- multi-target profile support (target multiple clients at once)
- General settings now clearly labels the field as a single-target override; multi-target editing lives in Client management
- status card client tiles now use stable sorting (not heartbeat `updated_at`) so buttons stop jumping around while you try to click them
- status card now shows target/current/active as badges/chips instead of relying on position or inline emoji suffixes
- status card client tiles are now collapsible, reducing visual density while keeping per-client actions available when expanded
- collapsed client tiles now still show the client ID in the summary row for easier scanning
- options flow client management can now add/remove individual target clients
- target client
- active client / alias
- all recent clients
- quick alias editing buttons

The options flow client-management step shows:

- known clients summary
- target-client chooser / clear target action
- per-client alias editor / clear alias action
- per-client details (status, presence, last seen, views, visibility, last update)

## How rotation works

1. The integration loads a frontend module on HA pages.
2. The controller looks for the runtime sensor.
3. When the browser is on the configured dashboard path, it starts a timer.
4. When the timer expires, it navigates to the next configured view.
5. Manual interaction pauses rotation for the configured number of seconds.
6. Hidden/background pages pause when `only_when_visible` is enabled.

## Known MVP limitations

- single profile only
- aliases are still stored as JSON under the hood, but normal editing can now happen through the client-management UI

## Planned next steps

- multi-profile support
- richer client management UI (bulk actions)
- richer drag-and-drop / table-style views editor
- schedules
- random / ping-pong rotation modes

## License

MIT
