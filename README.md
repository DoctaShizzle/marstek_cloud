# Marstek Cloud Battery – Home Assistant Custom Integration

This custom integration connects your Marstek battery system (via the Marstek cloud API) to Home Assistant, pulling live data and exposing it as sensor entities.

---

## ✨ Features

- **Automatic login & token refresh**  
  Logs in to the Marstek cloud API using your credentials, hashes your password (MD5) before sending, and automatically refreshes the token if it expires.
  
- **Configurable scan interval**  
  Set how often the integration polls the API (10–3600 seconds) during initial setup or later via the Options menu.

- **Battery metrics exposed as sensors**  
  - `soc` – State of charge (%) with battery device class
  - `charge` – Charge power (W) with power device class
  - `discharge` – Discharge power (W) with power device class
  - `load` – Load power (W) with power device class
  - `profit` – Profit (€) with monetary device class
  - `version` – Firmware version
  - `sn` – Serial number
  - `report_time` – Timestamp of last report
  - `total_charge` – Total charge per device (kWh) with energy storage device class

- **Cumulative energy sensors for Energy Dashboard (auto-created!)**  
  - `energy_charged` – Total energy charged to battery (kWh), cumulative
  - `energy_discharged` – Total energy discharged from battery (kWh), cumulative
  - `energy_load` – Total energy consumed by loads (kWh), cumulative
  - All use the Riemann sum integral method to calculate energy from power over time
  - State persists across Home Assistant restarts
  - Ready to use with Energy Dashboard, no manual helper configuration needed!

- **Cross-device total charge sensor**  
  - `total_charge_all_devices` – Sum of total charges across all batteries (kWh).

- **Diagnostic sensors**  
  - `last_update` – Time of last successful update
  - `api_latency` – API call duration in milliseconds
  - `connection_status` – Online/offline status

- **Device registry integration**  
  Each battery appears as a device in HA with model, serial number, firmware version, and manufacturer.

- **Editable battery capacity**  
  Configure the default capacity (in kWh) for each battery during setup or later via the Options menu.

- **Smart device filtering**  
  Automatically filters out non-compatible or irrelevant device types (e.g., "HME-3") from the device list.

- **Energy Dashboard compatible**  
  All power and energy sensors include proper device classes and state classes for seamless integration with Home Assistant's Energy Dashboard.

---

## ⚡ Energy Dashboard Configuration

This integration is fully compatible with Home Assistant's Energy Dashboard with **automatic cumulative energy sensors!**

No manual Riemann sum helper configuration is needed - the integration automatically creates cumulative energy sensors that track total kWh charged, discharged, and consumed. These sensors are immediately ready to use with the Energy Dashboard.

📖 **[Read the complete Energy Dashboard setup guide](ENERGY_DASHBOARD.md)**

The guide covers:
- Using the auto-created cumulative energy sensors (no helpers needed!)
- Configuring the Energy Dashboard with your battery sensors
- Troubleshooting tips and best practices
- Example configurations for different setups

---

## 🛠 Installation

1. Copy the `marstek_cloud` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Marstek Cloud Battery**.
4. Enter your Marstek cloud email, password, and desired scan interval.

---

## ⚙ Configuration

- **Scan interval** can be set during initial setup and changed later via the integration’s **Configure** option.
- **Default battery capacity** (in kWh) can be set for each battery during setup or via the **Options** menu.
- Default capacity is 5.12 kWh.
- Minimum scan interval is 10 seconds, maximum is 3600 seconds.

---

## 🔍 Logic Flow

Here’s how the integration works internally:

### 1. **Setup**
- `config_flow.py` collects your email, password, scan interval, and default battery capacities.
- These are stored securely in HA’s config entries.

### 2. **Coordinator & API**
- `__init__.py` creates:
  - An `aiohttp` session for async HTTP calls.
  - A `MarstekAPI` instance for talking to the cloud API.
  - A `MarstekCoordinator` (subclass of `DataUpdateCoordinator`) that schedules periodic updates.

### 3. **Login & Token Handling**
- On first run, `MarstekAPI._get_token()`:
  - MD5‑hashes your password.
  - Sends a POST request to `https://eu.hamedata.com/app/Solar/v2_get_device.php`.
  - Stores the returned `token`.
- On each update, `MarstekAPI.get_devices()`:
  - Calls `https://eu.hamedata.com/ems/api/v1/getDeviceList` with the token.
  - If the API responds with an invalid/expired token, it refreshes and retries once.
  - If the API responds with error code `8` (no access permission), it clears the cached token and logs the error. A new token will be obtained automatically on the next update cycle.

### 4. **Data Fetching**
- The coordinator's `_async_update_data()`:
  - Records the start time.
  - Calls `api.get_devices()` to fetch the latest battery list.
  - Filters out ignored device types (e.g., "HME-3").
  - Calculates API latency in milliseconds.
  - Returns the filtered list of devices to all entities.

### 5. **Entity Creation**
- `sensor.py`:  
  - For each device in the API response, creates:  
    - One `MarstekSensor` per metric in `SENSOR_TYPES`.  
    - One `MarstekDiagnosticSensor` per metric in `DIAGNOSTIC_SENSORS`.  
    - One `MarstekDeviceTotalChargeSensor` for the total charge per device.  
  - Creates a `MarstekTotalChargeSensor` for the cross-device total charge.  
  - Each entity has:  
    - A unique ID (`devid_fieldname`).  
    - Device info (name, model, serial, firmware, manufacturer).

### 6. **Updates**
- HA calls `async_update()` on entities when needed.
- Entities pull their latest value from the coordinator’s cached data.
- The coordinator refreshes data on the configured interval or when manually triggered.

---

## 📡 API Endpoints Used

- **Login**:  
  `POST https://eu.hamedata.com/app/Solar/v2_get_device.php?pwd=<MD5_PASSWORD>&mailbox=<EMAIL>`

- **Get Devices**:  
  `GET https://eu.hamedata.com/ems/api/v1/getDeviceList?token=<TOKEN>`

---

## 📊 Sequence Diagram

```mermaid
sequenceDiagram
    participant HA as Home Assistant
    participant CF as Config Flow
    participant CO as Coordinator
    participant API as Marstek API
    participant ENT as Sensor Entities

    HA->>CF: User enters email, password, scan interval, capacities
    CF-->>HA: Store credentials, scan interval, capacities
    HA->>CO: Create coordinator with API client
    CO->>API: POST login (MD5 password)
    API-->>CO: Return token
    loop Every scan_interval seconds
        CO->>API: GET device list (token)
        alt Token expired
            API-->>CO: Error (invalid token)
            CO->>API: POST login (refresh token)
            API-->>CO: Return new token
            CO->>API: GET device list (retry)
        end
        API-->>CO: Return device data
        CO-->>ENT: Update all sensor values
        ENT-->>HA: Display updated metrics
    end
```
