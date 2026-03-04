# Configuring the Home Assistant Energy Dashboard for Marstek Battery Integration

This guide explains how to configure the Home Assistant Energy Dashboard to work with your Marstek battery system. The integration automatically provides all necessary sensors for comprehensive energy monitoring, including cumulative energy sensors that are ready to use with the Energy Dashboard out of the box.

## 📊 Available Sensors

After installing this integration, the following sensors are automatically created for each battery device:

### Power Sensors (Instant Measurements)
- **Charge Power** (`sensor.<device_name>_charge_power`) - Current charging power in Watts
- **Discharge Power** (`sensor.<device_name>_discharge_power`) - Current discharging power in Watts
- **Load** (`sensor.<device_name>_load`) - Current load power in Watts

### Energy Sensors (Cumulative - Ready for Energy Dashboard!)
- **Energy Charged** (`sensor.<device_name>_energy_charged`) - Total energy charged to battery in kWh ✨
- **Energy Discharged** (`sensor.<device_name>_energy_discharged`) - Total energy discharged from battery in kWh ✨
- **Load Energy Consumed** (`sensor.<device_name>_energy_load`) - Total energy consumed by connected loads in kWh ✨

### Energy Storage Sensors
- **State of Charge** (`sensor.<device_name>_state_of_charge`) - Battery charge level in %
- **Total Charge** (`sensor.<device_name>_total_charge`) - Current stored energy in kWh

### Aggregated Sensors (All Devices)
- **Total Power Across Devices** - Net power flow across all batteries (charge - discharge)
- **Total Charge Across Devices** - Total stored energy across all batteries in kWh

> **✨ New!** The cumulative energy sensors (Energy Charged, Energy Discharged, Load Energy Consumed) are automatically created by the integration and are immediately compatible with the Energy Dashboard. No manual helper configuration needed!

---

## 🔋 Quick Setup: Configure the Energy Dashboard

Setting up the Energy Dashboard is now extremely simple since all required sensors are automatically created!

### Step 1: Open Energy Dashboard Configuration

1. Go to **Settings** → **Dashboards** → **Energy**
2. Click **ADD CONSUMPTION** or the pencil icon to edit

### Step 2: Add Battery System

1. In the Energy Dashboard configuration, look for the **Battery Systems** section
2. Click **ADD BATTERY SYSTEM**
3. Configure as follows:

   **Energy going in to the battery:**
   - Select `sensor.<device_name>_energy_charged`
   
   **Energy coming out of the battery:**
   - Select `sensor.<device_name>_energy_discharged`

4. Click **SAVE**

### Step 3: Add Battery Storage Level (Optional but Recommended)

To track the actual energy stored in your battery:

1. Still in the Energy Dashboard configuration, find **Battery Systems** section
2. Look for an option to add battery storage capacity
3. Select `sensor.<device_name>_total_charge` or `sensor.total_charge_across_devices`

This will display the current energy level stored in your battery on the energy distribution card.

### Step 4: Monitor Individual Device Loads (Optional)

If you want to track energy consumed by connected loads:

1. In the **Individual Devices** section of the Energy Dashboard
2. Click **ADD DEVICE**
3. Select `sensor.<device_name>_energy_load`
4. Give it a friendly name like "Battery Connected Loads"
5. Click **SAVE**

---

## 📈 Verify and Monitor

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

## ⚙️ How It Works (Technical Details)

The integration automatically creates cumulative energy sensors using the **Riemann sum integral method** (left method) to calculate energy from power:

- **Monitors instantaneous power** from the Marstek API (charge, discharge, load)
- **Calculates energy** by integrating power over time: `Energy (kWh) = Power (kW) × Time (hours)`
- **Accumulates the total** as a continuously increasing value
- **Persists across restarts** - your cumulative energy values are preserved when Home Assistant restarts
- **Updates automatically** with each coordinator refresh (based on your scan interval)

This means:
- ✅ No manual Riemann sum helper configuration needed
- ✅ Works out of the box with Energy Dashboard
- ✅ Accurate energy tracking based on your scan interval
- ✅ State preserved across Home Assistant restarts
- ✅ All sensors have proper device classes and state classes

---

## 🔍 Troubleshooting

### No Data Appearing in Energy Dashboard

1. **Check Sensor States**:
   - Go to **Developer Tools** → **States**
   - Search for `energy_charged` or `energy_discharged`
   - Verify they have values and are increasing over time

2. **Verify Cumulative Sensors Exist**:
   - Check that `sensor.<device_name>_energy_charged` and `sensor.<device_name>_energy_discharged` exist
   - Their values should continuously increase (they're cumulative totals)
   - If they don't exist, try reloading the integration

3. **Wait for Data Collection**:
   - The Energy Dashboard requires at least 2 hours of data
   - The cumulative sensors start from zero when first created
   - Be patient, especially after first setup

4. **Check Entity Attributes**:
   - Go to **Developer Tools** → **States**
   - Click on a cumulative energy sensor
   - Under "Attributes", verify:
     - `device_class` is "energy"
     - `state_class` is "total_increasing"
     - `unit_of_measurement` is "kWh"

### Energy Values Seem Wrong

1. **Verify Battery Capacity**:
   - During integration setup, ensure you entered the correct battery capacity (default is 5.12 kWh)
   - To reconfigure: **Settings** → **Devices & Services** → **Marstek Cloud** → **CONFIGURE**

2. **Check Scan Interval**:
   - Very long scan intervals may cause less accurate energy calculations
   - Recommended: 30-60 seconds for best accuracy
   - Very short intervals (< 10 seconds) might create unnecessary API load

3. **Cumulative Values Reset to Zero**:
   - This should not happen as the state is persisted
   - If it does, check your Home Assistant logs for errors
   - The sensor will start accumulating again from zero

4. **Power Values Not Updating**:
   - Check if the base power sensors (charge_power, discharge_power) are updating
   - Verify your Marstek API credentials are still valid
   - Check integration logs for API errors

### Sensors Not Showing Up

1. **Integration Loaded?**
   - Check **Settings** → **Devices & Services**
   - Verify "Marstek Cloud" integration is listed and shows devices

2. **Reload Integration**:
   - Click on the Marstek Cloud integration
   - Click the three dots → **Reload**
   - This will recreate all sensors including the new cumulative ones

3. **Check Logs**:
   - Go to **Settings** → **System** → **Logs**
   - Look for errors related to "marstek_cloud"
   - Check for messages about sensor restoration

4. **Verify Device Data**:
   - Go to **Developer Tools** → **States**
   - Check if the base sensors exist (charge_power, discharge_power)
   - If base sensors don't exist, the cumulative sensors won't be created

---

## 💡 Tips for Best Results

1. **Multiple Batteries**: If you have multiple Marstek batteries:
   - Each device gets its own set of cumulative energy sensors
   - You can add each device's sensors separately to the Energy Dashboard
   - Or track them individually to see per-battery performance

2. **Solar Integration**: If you also have solar panels, configure them in the Energy Dashboard to see:
   - How much solar energy is stored in batteries
   - How much solar energy is used directly
   - Your energy independence percentage

3. **Grid Configuration**: Add grid import/export sensors to track:
   - Battery charging from grid
   - Battery discharging to grid (if applicable)
   - Overall energy independence

4. **Historical Data**: The cumulative sensors start from zero when first created and continuously accumulate:
   - Over time, you'll build a rich historical dataset
   - Values persist across Home Assistant restarts
   - Long-term trends become visible after days/weeks of operation

5. **Backup Integration Settings**: Note down your battery capacities and scan intervals:
   - If you need to reinstall the integration, you'll need these values
   - The cumulative energy sensors will start from zero again after reinstallation

6. **Scan Interval Optimization**:
   - Balance between accuracy and API load
   - 30-60 seconds is ideal for most users
   - Shorter intervals = more accurate energy calculations but more API calls
   - Longer intervals = less API load but slightly less accurate

---

## 📊 Example Energy Dashboard Configuration

Here's a complete example for a typical setup:

### Energy Dashboard Configuration:
- **Grid Consumption**: Your utility meter sensor (if available)
- **Solar Production**: Your solar inverter sensor (if available)  
- **Battery Systems**:
  - Energy In: `sensor.<device_name>_energy_charged`
  - Energy Out: `sensor.<device_name>_energy_discharged`  
- **Battery Storage**:
  - Current Storage: `sensor.<device_name>_total_charge`
- **Individual Devices** (optional):
  - `sensor.<device_name>_energy_load` - Track connected loads

### Expected Behavior:
- When batteries charge: Energy flows from grid/solar → battery, `energy_charged` increases
- When batteries discharge: Energy flows from battery → home/grid, `energy_discharged` increases
- The dashboard shows battery efficiency and storage levels over time
- Cumulative values continuously increase and never reset (unless integration is reinstalled)

---

## 📝 Quick Reference: Sensor Mapping

| Energy Dashboard Field | Sensor to Use | Notes |
|------------------------|---------------|-------|
| Battery Energy In | `sensor.<device>_energy_charged` | Auto-created, ready to use ✨ |
| Battery Energy Out | `sensor.<device>_energy_discharged` | Auto-created, ready to use ✨ |
| Battery Storage Level | `sensor.<device>_total_charge` | Current kWh stored |
| Individual Device Load | `sensor.<device>_energy_load` | Auto-created, optional ✨ |
| Current Charge Power | `sensor.<device>_charge_power` | For automations/cards |
| Current Discharge Power | `sensor.<device>_discharge_power` | For automations/cards |
| Battery Percentage | `sensor.<device>_state_of_charge` | For conditional checks |

**Note**: Replace `<device>` with your actual device name from the integration.

---

## 🎯 Summary

1. **Install** the Marstek Cloud integration ✓
2. **Configure** with your credentials and preferences ✓
3. **Automatic sensors** are created including cumulative energy sensors ✓
4. **Set up** the Energy Dashboard using the auto-created energy sensors
5. **Wait** 2+ hours for initial data collection
6. **Enjoy** comprehensive energy monitoring without manual helper configuration!

**No manual Riemann sum helpers needed!** Everything works automatically out of the box. The integration calculates cumulative energy internally and provides sensors that are immediately compatible with Home Assistant's Energy Dashboard.

---

For questions or issues, please check the integration logs or open an issue on the GitHub repository.
