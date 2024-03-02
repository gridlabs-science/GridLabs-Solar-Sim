import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go  # Import Plotly's graph objects library
from plotly.subplots import make_subplots

import panel
import dynamicLoad


def process_solar_data(file_path):
  """
  This function reads a CSV file containing solar panel power data, performs initial
  calculations, and returns a modified DataFrame.

  Args:
      file_path: The path to the CSV file.

  Returns:
      A pandas DataFrame containing the processed data.
  """

  # Read the CSV data into a DataFrame
  df = pd.read_csv(file_path)

  # Find the maximum value in the "state" column
  df['state'] = pd.to_numeric(df['state'], errors='coerce')
  max_watts = df['state'].max()

  # Scale the "state" values between 0 and 1000
  df['state'] = df['state'] / max_watts * 1000

  # Convert the "last_changed" column to datetime format
  df["last_changed"] = pd.to_datetime(df["last_changed"])

  # Calculate the difference between each timestamp and the first timestamp
  first_timestamp = df["last_changed"].min()
  df["time_delta_seconds"] = (df["last_changed"] - first_timestamp) / pd.Timedelta(seconds=1)

  # Drop the "entity_id" column
  df = df.drop("entity_id", axis=1)

  return df


def get_irr_at_time(df, target_time):
  """
  This function takes a DataFrame containing processed solar panel data and a target
  time in seconds, and returns the scaled power output closest to, but before, the target time.

  Args:
      df: The DataFrame containing the processed data.
      target_time: The target time in seconds.

  Returns:
      The scaled power output closest to, but before, the target time.
  """

  # Find the index of the timestamp closest to, but before, the target time
  closest_index = df[df["time_delta_seconds"] <= target_time]["time_delta_seconds"].idxmax()

  # Return the corresponding scaled power output
  return df.loc[closest_index, "state"]



def stress_test(C, V, t1, t2, HPW, LPW):
  """
  Simulates the discharge of a capacitor powering a computer with high and low power modes and response times.

  Args:
      F: Capacitor size in Farads.
      V: Initial capacitor voltage.
      t1: Low power response time in seconds.
      t2: High power response time in seconds.
      HPW: High power draw of the computer in watts.
      LPW: Low power draw of the computer in watts.

  Returns:
      A tuple containing:
          time: A list of time points in seconds.
          voltage: A list of capacitor voltages at each time point.
  """

  # Calculate time constant
  #tau = C * V / HPW

  # Define time steps
  dt = 0.01  # Adjust as needed for accuracy
  time = np.arange(0, 3 * segmentTime, dt)

  # Initialize voltage
  voltage = V * np.ones_like(time)

  # Simulate discharge with response times and power modes
  for i in range(1, len(time)):
    if time[i] <= segmentTime:
      # Discharge in high power mode
      voltage[i] = voltage[i - 1] - (HPW * dt) / (C * voltage[i - 1])
    #elif time[i] <= segmentTime*2:
      # Transition from high to low power mode (linear ramp)
    #  power_draw = HPW - (HPW - LPW) * (time[i] - t1) / t2
    #  voltage[i] = voltage[i - 1] - (power_draw * dt) / (F * voltage[i - 1])
    else:
      # Discharge in low power mode
      voltage[i] = voltage[i - 1] - (LPW * dt) / (C * voltage[i - 1])

  return time, voltage

# Other system variables
DCDCeff = .87 # Efficiency of DC to DC converter.  85-95% is typically, depending on stepdown voltage (lower stepdown gives better efficiency)
C = 10.0  # Farads, capacitor size
V = 12.0  # Volts, nominal capacitor voltage (max)
vt1 = 1.0  # stage 1 power reduction voltage trigger
vt2 = 2.0  # High power response time (seconds)
HPW = 300.0  # High power draw (watts)
LPW = 5.0 # Low power draw (watts)

# Simulation variables
dt = 0.01  # Seconds per step in the simulation.  Adjust as needed for speed and accuracy
#Stress Test irradiance pattern.  It simply starts high for segmentTime, goes low for segmentTime, then back high for segmentTime
hiIRR = 1000   # Maximum irradiance, in watts / m^2
lowIRR = 0     # Minimum irradiance (0 = total solar eclipse, 200 typical overcast day)
segmentTime = 60   # amount of time to spend at lowIRR (in seconds)

# Solar Panel Electrical Characteristics 
solarPanel = panel.panel(Voc=49.6, Vmp=41.64, Isc=13.86, Imp=12.97, maxPower=540.0)

# Calculate the panel's current/voltage curves
powerCurve = np.zeros(int((solarPanel.Voc / 0.01) + 1))
currentCurve = np.zeros(int((solarPanel.Voc / 0.01) + 1))
# Loop through voltages and call the function
for i, voltage in enumerate(np.arange(0, solarPanel.Voc + 0.01, 0.01)):
  currentCurve[i] = solarPanel.panel_output(voltage, 1000)
  powerCurve[i] = currentCurve[i] * voltage

# Read in the real solar data and process into irradiance data
data_file = str("data/West_roof.csv")  # Replace with the path to your CSV file
processed_data = process_solar_data(data_file)

# Example: Get the power output at 100 seconds
target_time = 100
irr_at_time = get_irr_at_time(processed_data, target_time)

time, voltage = stress_test(C, V, vt1, vt2, HPW, LPW)

fig = make_subplots(rows=2, cols=2, specs=[[{"secondary_y": True}, {}], [{},{}]])
# Create the Plotly figure
#fig = go.Figure()

# Add the trace for the capacitor voltage
fig.add_trace(go.Scatter(x=processed_data['last_changed'], y=processed_data['state'], name="Real world irradiance data"), row=2, col=1)
fig.add_trace(go.Scatter(x=time, y=voltage, name="Capacitor Voltage"), row=1, col=2)
fig.add_trace(go.Scatter(x=np.arange(0, solarPanel.Voc + 0.01, 0.01), y=powerCurve, name="Panel Power Curve"), row=1, col=1, secondary_y=False)
fig.add_trace(go.Scatter(x=np.arange(0, solarPanel.Voc + 0.01, 0.01), y=currentCurve, name="Panel Current Curve"), row=1, col=1, secondary_y=True)


# Set up the layout with labels, title, and grid
fig.update_layout(
    #xaxis_title="Time (s)",
    #yaxis_title="Voltage (V)",
    title="Grid Labs Solar Sim",
    showlegend=True
)

# Display the interactive chart
fig.show()