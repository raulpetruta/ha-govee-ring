<p align="center">
  <img src="custom_components/govee_ring/brand/icon@2x.png" alt="Govee Ring icon" width="160">
</p>

<h1 align="center">Govee Ring for Home Assistant</h1>

<p align="center">
  Control the <b>ring</b> of a Govee H60A4 ceiling light separately from its main panel, fully local.
</p>

<p align="center">
  <a href="https://github.com/raulpetruta/ha-govee-ring/releases"><img alt="Release" src="https://img.shields.io/github/v/release/raulpetruta/ha-govee-ring"></a>
  <a href="https://github.com/raulpetruta/ha-govee-ring/actions/workflows/validate.yml"><img alt="Validate" src="https://github.com/raulpetruta/ha-govee-ring/actions/workflows/validate.yml/badge.svg"></a>
  <a href="https://github.com/raulpetruta/ha-govee-ring/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/raulpetruta/ha-govee-ring/actions/workflows/tests.yml/badge.svg"></a>
  <a href="https://hacs.xyz"><img alt="HACS" src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg"></a>
</p>

---

The Govee H60A4 has a white main panel and an RGB ring around it. The Govee Home app can light the ring on its own, but Home Assistant's built-in **Govee Lights Local** and **Matter** integrations only see one light. Turning on a colour lights up the whole lamp.

This integration adds a **Ring** light next to the lamp's **Main light** on the same device, so you get two sliders:

| Entity | What it does |
|---|---|
| `light.<name>_ring` | The ring only, any colour and brightness. The panel stays dark. |
| `light.<name>_main_light` | The main light. It mirrors your existing Govee entity and brings back white after the ring was used. |

Everything runs on your local network. No Govee account and no cloud.

## Requirements

- A **Govee H60A4**. It was tested on BLE firmware 1.04.03 and Wi-Fi firmware 1.00.29. Other DreamView-capable ceiling lights may work but are untested. Open an issue if you try one.
- **LAN Control** turned on for the light in the Govee Home app: device → ⚙️ settings → LAN Control.
- A **fixed IP address** for the light. Set a DHCP reservation in your router.
- Home Assistant **2026.3 or newer**. It was tested on 2026.9 and 2026.10.
- Optional, but recommended: the built-in **Govee Lights Local** integration. Its entity becomes the Main light.

## Installation

The steps are the same on **Home Assistant OS**, **Supervised**, **Container (Docker)** and **Core**.

### HACS / Marketplace (recommended)

**HACS today:**

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/raulpetruta/ha-govee-ring` with the type **Integration**.
3. Search for **Govee Ring**, then select **Download**.
4. Restart Home Assistant.

**Home Assistant 2026.11+ with the built-in Marketplace:** HACS becomes part of Home Assistant Core as the Marketplace ([core PR #183502](https://github.com/home-assistant/core/pull/183502), [docs PR #48513](https://github.com/home-assistant/home-assistant.io/pull/48513)).

1. Settings → **Marketplace** → **Add from link**, and paste the repository URL. Once the integration is in the default catalog, search for it instead.
2. Restart Home Assistant.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=raulpetruta&repository=ha-govee-ring&category=integration)

### Manual

1. Download `govee_ring.zip` from the [latest release](https://github.com/raulpetruta/ha-govee-ring/releases/latest).
2. Unzip it into `config/custom_components/govee_ring/`:
   - **HAOS / Supervised:** use the *Samba share*, *Studio Code Server* or *File editor* add-on.
   - **Docker:** use the folder you mounted as `/config`, for example `~/docker/homeassistant/custom_components/govee_ring/`.
3. Restart Home Assistant.

> **Docker networking:** commands are sent to the light over UDP port 4003. Bridge networking works for that. The built-in Govee Lights Local integration needs `network_mode: host` for discovery, so if you use it you most likely already run in host mode.

## Setup

Settings → Devices & services → **Add integration** → **Govee Ring**, then fill in:

| Field | Example | Notes |
|---|---|---|
| IP address or hostname | `192.168.1.229` | The light's fixed address. |
| Name | `Living Room` | The device name. Entities become `light.living_room_ring` and `light.living_room_main_light`. |
| Main light entity | `light.h60a4_4` | Optional. Your existing light entity for this lamp. |

Add one entry per lamp.

To change things later:
- **New IP address:** ⋮ → **Reconfigure**.
- **Different or no Main light:** **Configure** (Options).

## Usage

Use the two lights like any other light: dashboards, voice, scenes, automations.

```yaml
# Ring only: a soft purple glow, with the panel off
action: light.turn_on
target:
  entity_id: light.living_room_ring
data:
  rgb_color: [160, 0, 255]
  brightness_pct: 60
```

### Action: `govee_ring.set_segments`

The ring has **19 zones (0 to 18)**. Neighbouring zones blend into each other.

```yaml
# A red-to-blue gradient across the whole ring
action: govee_ring.set_segments
target:
  entity_id: light.living_room_ring
data:
  gradient: [[255, 0, 0], [0, 0, 255]]

# Only zones 0 to 4 in green, at half brightness
action: govee_ring.set_segments
target:
  entity_id: light.living_room_ring
data:
  segments: [0, 1, 2, 3, 4]
  rgb_color: [0, 255, 0]
  brightness_pct: 50
```

## How it works

The H60A4 supports Govee's **DreamView** ("razer") streaming mode on the LAN API. When the Ring turns on, the integration:

1. Puts the lamp in black RGB mode, which switches the white panel LEDs off. Then it powers the lamp on. Doing it in this order avoids a flash.
2. Enables streaming and sends a 20-zone frame. Zones 0 to 18 are the ring. Zone 19 drives the panel and is always sent black.
3. Re-sends the frame every 25 seconds. The lamp leaves streaming mode about 60 seconds after the last frame.

When the Main light turns on after a ring session, the integration ends streaming and restores the last white colour temperature. The light never reports streaming state back, so the Ring is an *assumed state* entity.

## Known limitations

<img src="docs/ring-gap.jpg" alt="The ring lit blue with a short dark section at the top" width="360" align="right">

- **A short section at the top of the ring stays dark.** The lamp's firmware wires that bit of the ring to zone 19, the same zone as the centre panel. So it can't be lit without also lighting the panel, at least over the local API. The photo shows it. Ideas for fixing it are welcome. The Govee cloud API has a per-segment command that might, at the cost of going through the cloud.
- **State is assumed.** If the Govee app or another controller changes the lamp, the Ring entity doesn't notice.
- **One controller at a time.** Don't stream from the Govee app's DreamView or another DreamView source at the same time.
- No connection test during setup. The light answers on UDP port 4002, which the Govee Lights Local integration already uses.

<br clear="right">

## Troubleshooting

- **Nothing happens:** check that LAN Control is on and the IP address is right. Also check that Home Assistant can reach the light (`ping <ip>` from the host).
- **The panel lights up with the ring:** turn the Ring off and on again. If it keeps happening, open an issue with a short video.
- **Diagnostics:** Settings → Devices & services → Govee Ring → ⋮ → **Download diagnostics**. The IP address is redacted.
- **Debug logs:**
  ```yaml
  logger:
    logs:
      custom_components.govee_ring: debug
  ```

## The story: "just film it"

I asked Claude to make the ring controllable from Home Assistant. It couldn't see my ceiling, so it did the next best thing. It sent test patterns to the lamp and asked me to **record a video**. It extracted frames from each clip, worked out which zone was which, and kept refining the protocol until the ring lit by itself.

<p align="center">
  <img src="docs/debug-frames.jpg" alt="Frames from the debugging videos: a red test marker, a single zone lit, zone 19 lighting the panel and the top of the ring in green, and the full ring in purple" width="100%">
  <br>
  <sub>Frames from my phone videos. From left: the red "recording starts here" marker, one zone lit during the zone sweep, zone 19 lighting the panel together with the top of the ring, and the finished ring.</sub>
</p>

It even asked for a **5-second red flash at the start** of each test, so it could line up its commands with my recording. I was honestly amazed. I didn't write a packet dump or open a debugger. I pointed my phone at the ceiling and sent the clip back.

I think we're entering a new paradigm: **you record the problem, and the agent reverse-engineers it for you.**

## Built with

- **[Claude Code](https://claude.com/claude-code)**. Each step was **planned with Claude Opus 5.5** and **implemented with Claude Sonnet 5.5**: protocol research, test design, the integration, this release.
- **[REA](https://github.com/morluto/rea)**, a reverse-engineering toolkit with a CLI and MCP server. Claude used it to dig into the Govee Android app package and look for how the app talks to the lamp.
- The protocol notes from the [SignalRGB](https://signalrgb.com) Govee plugin and the [OpenRGB](https://openrgb.org) community were the hint that the H60A4 supports DreamView streaming.

## Disclaimer

This project is not affiliated with, endorsed by, or connected to Govee. "Govee" and product names are trademarks of their owners. The LAN protocol was worked out by observing the lamp's behaviour, and no Govee code or assets are included. Use at your own risk.

## License

[MIT](LICENSE)
