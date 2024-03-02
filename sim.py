import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go  # Import Plotly's graph objects library
from plotly.subplots import make_subplots



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


def panel_output(PV, IR):
  #args:
  #PV = solar panel voltage, instantaneous.  The voltage the panel is now being driven at by the buck converter/capacitor.
  #IR = irradiance, instantaneous.  In watts / meter^2
  amps = 0

  #This calculates the output power from a PWM which hold the voltage below the MPP
  #The following equations are taken from this paper:  https://oa.upm.es/43747/1/PindadoRE20016.pdf
  if(PV > Vmp):
    amps = Isc * (1 - (1 - (Imp/Isc)) * (PV/Vmp)**(Imp/(Isc-Imp)))
  else: #TODO: add the second equation for estimating the other half of the curve
    amps = 0

  # now do linear scaling to adjust for irradiance.  This is an approximation, but good enough for our purposes IMO
  perc = IR / 1000  #1000 IR is perfect full sun, max blast, all systems go, given er all she's got scotty
  amps = perc * amps
  return amps



def capacitor_discharge(C, V, t1, t2, HPW, LPW):
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
  tau = C * V / HPW

  # Define time steps
  dt = 0.01  # Adjust as needed for accuracy
  time = np.arange(0, 3 * segmentTime, dt)

  # Initialize voltage
  voltage = V * np.ones_like(time)

  # Simulate discharge with response times and power modes
  for i in range(1, len(time)):
    if time[i] <= t1:
      # Discharge in high power mode
      voltage[i] = voltage[i - 1] - (HPW * dt) / (C * voltage[i - 1])
    #elif time[i] <= t1 + t2:
      # Transition from high to low power mode (linear ramp)
    #  power_draw = HPW - (HPW - LPW) * (time[i] - t1) / t2
    #  voltage[i] = voltage[i - 1] - (power_draw * dt) / (F * voltage[i - 1])
    else:
      # Discharge in low power mode
      voltage[i] = voltage[i - 1] - (LPW * dt) / (C * voltage[i - 1])

  return time, voltage

# Solar Panel Electrical Characteristics (per single panel)
numPanels = 1 # Number of panels used
Pmax = 540  # Maximum rated power in Watts at STC, 1000W/m^3 irradiance
Voc = 49.6  # Volts, Open Circuit Voltage
Vmp = 47.1  # Volts, Maximum Power Voltage
Isc = 13.86 # Amps, Short Circuit Current
Imp = 12.97 # Amps, Maximum Power Current

# Other system variables
DCDCeff = .87 # Efficiency of DC to DC converter.  85-95% is typically, depending on stepdown voltage (lower stepdown gives better efficiency)
C = 10  # Farads, capacitor size
V = 12  # Volts, nominal capacitor voltage (max)
vt1 = 1  # stage 1 power reduction voltage trigger
vt2 = 2  # High power response time (seconds)
HPW = 300  # High power draw (watts)
LPW = 5  # Low power draw (watts)

# Simulation variables
dt = 0.01  # Seconds per step in the simulation.  Adjust as needed for speed and accuracy
#Irradiance pattern.  It simply starts high for segmentTime, goes low for segmentTime, then back high for segmentTime
hiIRR = 1000   # Maximum irradiance, in watts / m^2
lowIRR = 0     # Minimum irradiance (0 = total solar eclipse, 200 typical overcast day)
segmentTime = 60   # amount of time to spend at lowIRR (in seconds)

# Other prepartory calculations:
#The following equations are taken from this paper:  https://oa.upm.es/43747/1/PindadoRE20016.pdf
eta1 = 1/0.11175 * (Isc/Imp) * (Voc/Vmp - 1)  # First estimate for Eta (greek letter)
eta2 = (Isc/Imp) * (Isc / (Isc-Imp)) * ((Voc-Vmp)/Voc)  # Second estimate for Eta (different method)
eta = eta1  #picking one of them.  Feel free to change this to eta2 or an average of the two: eta = (eta1+eta2)/2
print ("eta1 = " + str(eta1))
print ("eta2 = " + str(eta2))
Pmax = Vmp * Imp

# Create an empty NumPy array to store results
powerCurve = np.zeros(int((Voc / 0.1) + 1))
currentCurve = np.zeros(int((Voc / 0.1) + 1))
# Loop through voltages and call the function
for i, voltage in enumerate(np.arange(0, Voc + 0.1, 0.1)):
  currentCurve[i] = panel_output(voltage, 1000)
  powerCurve[i] = currentCurve[i] * voltage

print("-----------------")

# Read in the real solar data and process into irradiance data
data_file = str("data/West_roof.csv")  # Replace with the path to your CSV file
processed_data = process_solar_data(data_file)

# Example: Get the power output at 100 seconds
target_time = 100
irr_at_time = get_irr_at_time(processed_data, target_time)
print(f"Power output at {target_time} seconds: {irr_at_time:.2f}")





time, voltage = capacitor_discharge(C, V, vt1, vt2, HPW, LPW)


fig = make_subplots(rows=2, cols=2)
# Create the Plotly figure
#fig = go.Figure()

# Add the trace for the capacitor voltage
fig.add_trace(go.Scatter(x=processed_data['last_changed'], y=processed_data['state'], name="Real world irradiance data"), row=2, col=1)
fig.add_trace(go.Scatter(x=time, y=voltage, name="Capacitor Voltage"), row=1, col=2)
fig.add_trace(go.Scatter(x=np.arange(0, Voc + 0.1, 0.1), y=powerCurve, name="Panel Power Curve"), row=1, col=1)


# Set up the layout with labels, title, and grid
fig.update_layout(
    #xaxis_title="Time (s)",
    #yaxis_title="Voltage (V)",
    title="Capacitor Discharge Simulation with Response Times and Power Modes",
    showlegend=True
)

# Display the interactive chart
fig.show()