# Configuring the Home Assistant Energy Dashboard for Marstek Battery Integration

This guide explains how to configure the Home Assistant Energy Dashboard to work with your Marstek battery system. The integration provides all necessary sensors for comprehensive energy monitoring.

## 📊 Available Sensors

After installing this integration, the following sensors are available for each battery device:

### Power Sensors (Instant Measurements)
- **Charge Power** (`sensor.<device_name>_charge_power`) - Current charging power in Watts
- **Discharge Power** (`sensor.<device_name>_discharge_power`) - Current discharging power in Watts
- **Load** (`sensor.<device_name>_load`) - Current load power in Watts

### Energy Storage Sensors
- **State of Charge** (`sensor.<device_name>_state_of_charge`) - Battery charge level in %
- **Total Charge** (`sensor.<device_name>_total_charge`) - Current stored energy in kWh

### Aggregated Sensors (All Devices)
- **Total Power Across Devices** - Net power flow across all batteries (charge - discharge)
- **Total Charge Across Devices** - Total stored energy across all batteries in kWh

---

## ⚡ Step 1: Create Energy Tracking Helpers

The Energy Dashboard requires cumulative energy sensors (total kWh charged/discharged over time). Since the Marstek API provides instantaneous power values, we need to convert these to cumulative energy using Home Assistant's **Riemann Sum Integral** helper.

### Option A: Using the UI (Recommended)

1. Go to **Settings** → **Devices & Services** → **Helpers** tab
2. Click **+ CREATE HELPER** → **Integration - Riemann sum integral sensor**
3. Create the following helpers:

#### Helper 1: Battery Energy Charged
- **Name**: `Marstek Battery Energy Charged` (or customize per device)
- **Input sensor**: Select your `sensor.<device_name>_charge_power`
- **Integration method**: `Left Riemann sum`
- **Metric prefix**: `k` (kilo)
- **Time unit**: `Hours`
- Click **SUBMIT**

#### Helper 2: Battery Energy Discharged
- **Name**: `Marstek Battery Energy Discharged` (or customize per device)
- **Input sensor**: Select your `sensor.<device_name>_discharge_power`
- **Integration method**: `Left Riemann sum`
- **Metric prefix**: `k` (kilo)
- **Time unit**: `Hours`
- Click **SUBMIT**

#### Helper 3: Load Energy Consumed (Optional)
- **Name**: `Marstek Load Energy Consumed` (or customize per device)
- **Input sensor**: Select your `sensor.<device_name>_load`
- **Integration method**: `Left Riemann sum`
- **Metric prefix**: `k` (kilo)
- **Time unit**: `Hours`
- Click **SUBMIT**

> **Note:** If you have multiple battery devices, create separate helpers for each device, or use the aggregated "Total Power Across Devices" sensor.

### Option B: Using YAML Configuration

Add the following to your `configuration.yaml`:

```yaml
sensor:
  # Energy charged to battery
  - platform: integration
    source: sensor.<device_name>_charge_power
    name: "Marstek Battery Energy Charged"
    unique_id: marstek_battery_energy_charged
    unit_prefix: k
    unit_time: h
    method: left
    
  # Energy discharged from battery
  - platform: integration
    source: sensor.<device_name>_discharge_power
    name: "Marstek Battery Energy Discharged"
    unique_id: marstek_battery_energy_discharged
    unit_prefix: k
    unit_time: h
    method: left
    
  # Optional: Load energy consumed
  - platform: integration
    source: sensor.<device_name>_load
    name: "Marstek Load Energy Consumed"
    unique_id: marstek_load_energy_consumed
    unit_prefix: k
    unit_time: h
    method: left
```

Replace `<device_name>` with your actual device name (check in **Developer Tools** → **States**).

After adding this configuration, restart Home Assistant.

---

## 🔋 Step 2: Configure the Energy Dashboard

1. Go to **Settings** → **Dashboards** → **Energy**
2. Click **ADD CONSUMPTION** or the pencil icon to edit

### Add Battery System

1. In the Energy Dashboard configuration, look for the **Battery Systems** section
2. Click **ADD BATTERY SYSTEM**
3. Configure as follows:

   **Energy going in to the battery:**
   - Select `sensor.marstek_battery_energy_charged` (the Riemann sum helper you created)
   
   **Energy coming out of the battery:**
   - Select `sensor.marstek_battery_energy_discharged` (the Riemann sum helper you created)

4. Click **SAVE**

### Add Battery Storage (Optional but Recommended)

To track the actual energy stored in your battery:

1. Still in the Energy Dashboard configuration, find **Battery Systems** section
2. Look for an option to add battery storage capacity
3. Select `sensor.<device_name>_total_charge` or `sensor.total_charge_across_devices`

This will show you the current energy level stored in your battery on the energy distribution card.

### Monitor Individual Device Loads (Optional)

If you want to track energy consumed by connected loads:

1. In the **Individual Devices** section of the Energy Dashboard
2. Click **ADD DEVICE**
3. Select `sensor.marstek_load_energy_consumed` (the Riemann sum helper)
4. Give it a friendly name like "Battery Connected Loads"
5. Click **SAVE**

---

## 📈 Step 3: Verify and Monitor

After configuration, wait at least 2 hours for the Energy Dashboard to collect enough data. Then:

1. Go to your **Energy Dashboard**
2. You should see:
   - Battery charge/discharge flow in the energy distribution card
   - Battery storage level if configured
   - Historical graphs showing energy flow over time
   - Cost calculations (if you've configured energy pricing)

### What You'll See:

- **Energy Distribution Card**: Shows real-time energy flow
- **Battery Energy Card**: Shows energy charged/discharged over selected period
- **Energy Usage Graph**: Historical view of battery performance
- **Self-Sufficiency**: Percentage of energy needs met by battery (if solar is also configured)

---

## 🔍 Troubleshooting

### No Data Appearing in Energy Dashboard

1. **Check Sensor States**:
   - Go to **Developer Tools** → **States**
   - Search for your Marstek sensors
   - Verify they have values and are updating

2. **Verify Riemann Sum Helpers**:
   - Check that your `sensor.marstek_battery_energy_charged` and `sensor.marstek_battery_energy_discharged` sensors exist
   - Their values should increase over time (they're cumulative)

3. **Wait for Data Collection**:
   - The Energy Dashboard requires at least 2 hours of data
   - Be patient, especially after first setup

4. **Check Entity State Class**:
   - Go to **Developer Tools** → **States**
   - Click on a Marstek sensor
   - Under "Attributes", verify:
     - `device_class` is set (e.g., "power", "energy", "battery")
     - `state_class` is set to "measurement" or "total"

### Energy Values Seem Wrong

1. **Verify Battery Capacity**:
   - During integration setup, ensure you entered the correct battery capacity (default is 5.12 kWh)
   - To reconfigure: **Settings** → **Devices & Services** → **Marstek Cloud** → **CONFIGURE**

2. **Check Scan Interval**:
   - Very long scan intervals may cause inaccurate Riemann sum calculations
   - Recommended: 30-60 seconds for best accuracy

3. **Riemann Sum Method**:
   - Use `left` method for most accurate results with periodic sampling

### Sensors Not Showing Up

1. **Integration Loaded?**
   - Check **Settings** → **Devices & Services**
   - Verify "Marstek Cloud" integration is listed and shows devices

2. **Reload Integration**:
   - Click on the Marstek Cloud integration
   - Click the three dots → **Reload**

3. **Check Logs**:
   - Go to **Settings** → **System** → **Logs**
   - Look for errors related to "marstek_cloud"

---

## 💡 Tips for Best Results

1. **Multiple Batteries**: If you have multiple Marstek batteries, you can either:
   - Create separate Riemann sum helpers for each device and add them individually
   - Use the "Total Power Across Devices" sensors for aggregated tracking

2. **Solar Integration**: If you also have solar panels, configure them in the Energy Dashboard to see:
   - How much solar energy is stored in batteries
   - How much solar energy is used directly
   - Your energy independence percentage

3. **Grid Configuration**: Add grid import/export sensors to track:
   - Battery charging from grid
   - Battery discharging to grid (if applicable)
   - Overall energy independence

4. **Historical Data**: The Riemann sum sensors start from zero when created. Over time, you'll build a rich historical dataset for analysis.

5. **Backup Integration Settings**: Note down your battery capacities and scan intervals. If you need to reinstall the integration, you'll need to reconfigure these values.

---

## 📊 Example Energy Dashboard Configuration

Here's a complete example for a typical setup:

### Energy Dashboard Configuration:
- **Grid Consumption**: Your utility meter sensor (if available)
- **Solar Production**: Your solar inverter sensor (if available)  
- **Battery Systems**:
  - Energy In: `sensor.marstek_battery_energy_charged`
  - Energy Out: `sensor.marstek_battery_energy_discharged`  
- **Battery Storage**:
  - Current Storage: `sensor.total_charge_across_devices`

### Expected Behavior:
- When batteries charge: Energy flows from grid/solar → battery
- When batteries discharge: Energy flows from battery → home/grid
- The dashboard shows battery efficiency and storage levels over time

---

## 📝 Quick Reference: Sensor Mapping

| Energy Dashboard Field | Sensor to Use | Type |
|------------------------|---------------|------|
| Battery Energy In | `sensor.marstek_battery_energy_charged` | Riemann Sum Helper |
| Battery Energy Out | `sensor.marstek_battery_energy_discharged` | Riemann Sum Helper |
| Battery Storage Level | `sensor.<device>_total_charge` or `sensor.total_charge_across_devices` | Direct Sensor |
| Current Charge Power | `sensor.<device>_charge_power` | Direct Sensor (for automations) |
| Current Discharge Power | `sensor.<device>_discharge_power` | Direct Sensor (for automations) |
| Battery Percentage | `sensor.<device>_state_of_charge` | Direct Sensor (for conditional checks) |

---

## 🎯 Summary

1. **Install** the Marstek Cloud integration (already done ✓)
2. **Create** Riemann sum integral helpers to track cumulative energy
3. **Configure** the Energy Dashboard to use these helpers
4. **Wait** 2+ hours for data collection
5. **Enjoy** comprehensive energy monitoring!

Your Marstek battery system is now fully integrated with Home Assistant's Energy Dashboard, giving you complete visibility into your energy storage and usage patterns.

---

For questions or issues, please check the integration logs or open an issue on the GitHub repository.
