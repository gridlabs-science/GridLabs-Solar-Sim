import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import math
import plotly.graph_objects as go  # Import Plotly's graph objects library
from plotly.subplots import make_subplots

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from textwrap import dedent as d

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



def stress_test(solarPanel, Bitaxe, dt, highIRR, lowIRR, segmentTime):
  time = np.arange(0, 3 * segmentTime, dt)
  voltage =  np.ones_like(time)     # Initialize voltage
  panelPower = np.ones_like(time)
  ASICPower = np.ones_like(time)
  ASICState = np.ones_like(time)
  voltage[0] = Bitaxe.lastPanelVoltage  # really the capacitor voltage, but same thing
  panelPower[0] = voltage[0] * solarPanel.panel_output(voltage[0], highIRR)
  ASICPower[0] = Bitaxe.lastPower      # Initialize the ASIC power
  ASICState[0] = '3'
  print("voltage[0] = " + str(voltage[0]) + " /  panelPower[0] = " + str(panelPower[0]))
  for i in range(1, len(time)):        # Determine irradiance based on simulation time
    irr = 0
    if time[i] <= segmentTime:                                          # Segment 0, stabilize at full irr, full power
      irr = highIRR
    elif time[i] <= segmentTime*2:                                      # Segment 1, full power loss, min irr.  Begin discharge, ASIC should cycle into sleep mode.
      irr = lowIRR    
    else:                                                               # Segment 2, full power returns max irr, ASIC reboots, observe power ramp up.
      irr = highIRR
      
    # Based on the new irradiance, get the panel power output
    panelAmps = solarPanel.panel_output(voltage[i-1], irr)  #gets the current output (in amps)
    #print("panelAmps " + str(panelAmps))
    panelPower[i-1] = panelAmps * voltage[i-1]
    #print("panelPower " + str(panelPower[i-1]))

    # Use Panel output and ASIC last power setting and dt to run the sim forward one step and get the new capacitor/panel voltage
    deltaWatts = panelPower[i-1] - ASICPower[i-1]  # Find the power delta between what the panel is producing and what the ASIC is pulling
    #print("ASICPower[i] = " + str(ASICPower[i-1]))
    #print("deltaWatts " + str(deltaWatts))
    energyChange = abs(deltaWatts * dt)
    #print("energyChange " + str(energyChange))
    #voltage[i] = voltage[i-1] + np.sign(deltaWatts)*math.sqrt(2*energyChange/Bitaxe.capacitorSize)
    #voltage[i] = math.sqrt(voltage[i-1]**2 - np.sign(deltaWatts)*2*energyChange/Bitaxe.capacitorSize)
    voltage[i] = voltage[i-1] + (panelAmps - ASICPower[i-1]/voltage[i-1])/Bitaxe.capacitorSize * dt
    #print("voltage[" + str(i) + "] " + str(voltage[i]))

    # Now a small loop to shorten the time step and more accurately calculate the integral of the power flow into the capacitor, since the above calculation is mos def wronger.
    v0 = voltage[i-1]
    v1 = voltage[i]  # This is wrong, because we have assumed constant power output from the panel throughout the time step
    dV = v1-v0
    i0 = solarPanel.panel_output(v0, irr)  #starting panel current
    i1 = solarPanel.panel_output(v1, irr)  #ending panel current.  This will get tweaked and adjusted as we run through smaller time steps.  
    dI = i1-i0
    dt = dt  #just repeated here for my sanity
    p0 = v0 * i0 - ASICPower[i-1]
    p1 = v1 * i1 - ASICPower[i-1]
    # The first estimate for p1 is wrong, because v1 is wrong, because it assumes constant power from the panel.  So now we adjust...
    while(True):
      avgI = (i0+i1)/2  #panel voltage
      avgV = (v0+v1)/2  #panel voltage
      avgP = avgV*avgI - ASICPower[i-1]  #system power (panel power - ASIC power)
      dE   = abs(avgP*dt)  # Energy change in joules
      #NEWv1= v0 + np.sign(avgP)*math.sqrt(2*dE/Bitaxe.capacitorSize)  # The new guesstimate for v1, using average panel voltage and power output instead of starting power at v0
      #NEWv1= math.sqrt(v0**2 - np.sign(avgP)*2*dE/Bitaxe.capacitorSize)
      NEWv1 = v0 + (avgI - ASICPower[i-1]/voltage[i-1])/Bitaxe.capacitorSize * dt
      if(abs(NEWv1 - v1) < 0.00001):                                     # Finally got close enough for government work, so continue
        voltage[i] = NEWv1
        panelAmps = solarPanel.panel_output(voltage[i], irr)  #gets the current output (in amps)
        panelPower[i] = panelAmps * voltage[i]
        break
      else: 
        v1=NEWv1   # Not close enough yet, so store the new guess as the new v1, then loop to generate a new set of averages
    #print("NEW voltage[" + str(i) + "] " + str(voltage[i]))

    
    #voltage[i] = voltage[i - 1] - (-deltaWatts * dt) / (Bitaxe.capacitorSize * voltage[i - 1]) 
    #capPower = (0.5 * self.capacitorSize * (panelVoltage - self.lastPanelVoltage)**2) / dt
   
    # Now let the ASIC state machine update and calculate it's new power draw
    if(voltage[i] <= Bitaxe.minVoltage): 
      Bitaxe.brownout()  # If the voltage got too low, then cut power to the device and log it at a brownout.
      voltage[i] = Bitaxe.minVoltage
    ASICPower[i] = Bitaxe.get_power(voltage[i], dt, solarPanel)
    if Bitaxe.state == 'running': ASICState[i] = 3
    if Bitaxe.state == 'curtailing': ASICState[i] = 2
    if Bitaxe.state == 'booting': ASICState[i] = 1
    if Bitaxe.state == 'curtailed': ASICState[i] = 0
    if Bitaxe.state == 'crashed': ASICState[i] = -5

    #if ASICPower[i] > Bitaxe.maxPower: break
    #if i > 17/dt: break
    #break

  return time, voltage, panelPower, ASICPower, ASICState

# Other system variables
#DCDCeff = .87 # Efficiency of DC to DC converter.  85-95% is typically, depending on stepdown voltage (lower stepdown gives better efficiency)
#C = 10.0  # Farads, capacitor size
#V = 12.0  # Volts, nominal capacitor voltage (max)
#vt1 = 1.0  # stage 1 power reduction voltage trigger
#vt2 = 2.0  # High power response time (seconds)
#HPW = 300.0  # High power draw (watts)
#LPW = 5.0 # Low power draw (watts)

# Solar Panel Electrical Characteristics 
#solarPanel = panel.panel(Voc=49.6, Vmp=41.64, Isc=13.86, Imp=12.97, maxPower=540.0)   # My big panels
solarPanel = panel.panel(Voc=21.6, Vmp=18.0, Isc=220.32, Imp=201.6, maxPower=3600.0)    # Ben's small 100W one

# Create the load object
# def __init__(self, pwrScaleUpSpeed, pwrScaleDownSpeed, curtailDelay, bootDelay, maxPower, minPower, capacitorSize, initialPanelVoltage, targetDecrement):
#pwrScaleSpeeds are in W/sec
Bitaxe = dynamicLoad.dynamicLoad(minVoltage=11, pwrScaleUpSpeed=5, pwrScaleDownSpeed=5, curtailDelay=1, bootDelay=10, maxPower=3000, minPower=180, capacitorSize=180, initialPanelVoltage=solarPanel.Vmp, targetDecrement=0.9)

# Calculate the panel's current/voltage curves
powerCurve = np.zeros(int((solarPanel.Voc / 0.01) + 1))
currentCurve = np.zeros(int((solarPanel.Voc / 0.01) + 1))
# Loop through voltages and call the function
for i, voltage in enumerate(np.arange(0, solarPanel.Voc + 0.0, 0.01)):
  currentCurve[i] = solarPanel.panel_output(voltage, 1000)
  powerCurve[i] = currentCurve[i] * voltage

# Run the short "stress test" of full on / full off power to observe basic system response
    # Simulation variables
dt = 0.1  # Seconds per step in the simulation.  Adjust as needed for speed and accuracy
    # Stress Test irradiance pattern.  It simply starts high for segmentTime, goes low for segmentTime, then back high for segmentTime
highIRR = 1000   # Maximum irradiance, in watts / m^2
lowIRR = 0     # Minimum irradiance (0 = total solar eclipse, 200 typical overcast day)
segmentTime = 15   # amount of time to spend at lowIRR (in seconds)
time, voltage, panelPower, ASICPower, ASICState = stress_test(solarPanel, Bitaxe, dt, highIRR, lowIRR, segmentTime)

#exit()

# Read in the real solar data and process into irradiance data
data_file = str("data/West_roof.csv")  # Replace with the path to your CSV file
processed_data = process_solar_data(data_file)

# Example: Get the power output at 100 seconds
target_time = 100
irr_at_time = get_irr_at_time(processed_data, target_time)



fig = make_subplots(rows=2, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": True}], [{"secondary_y": True},{"secondary_y": True}]])
# Create the Plotly figure
#fig = go.Figure()

# Add the trace for the capacitor voltage
fig.add_trace(go.Scatter(x=processed_data['last_changed'], y=processed_data['state'], name="Real world irradiance data"), row=2, col=1)

fig.add_trace(go.Scatter(x=time, y=voltage, name="Capacitor/Panel Voltage"), row=1, col=2, secondary_y=False)
fig.add_trace(go.Scatter(x=time, y=panelPower, name="Solar Power"), row=1, col=2, secondary_y=True)
fig.add_trace(go.Scatter(x=time, y=ASICPower, name="ASIC Power"), row=1, col=2, secondary_y=True)
fig.add_trace(go.Scatter(x=time, y=ASICState, name="ASIC state"), row=1, col=2, secondary_y=True)
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
#fig.show()

app = dash.Dash(__name__)
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}
app.layout = html.Div([
    dcc.Graph(id="interactive-plots", figure=fig),
    html.Div(className='row', children=[
        html.Div([
            dcc.Markdown(d("""
              Click on points in the garph.
            """)),
            html.Pre(id='hover-data', style=styles['pre']),
        ], className='three columns'),
    ])
])

# Callback function to update subplot based on hover data
@app.callback(
    Output("interactive-plots", "figure"),
    Input("interactive-plots", "hoverData")
)
def update_figure(hover_data):
    # Check if hover data is available
    if hover_data is None:
        return fig

    # Extract hovered voltage value
    hovered_voltage = hover_data["points"][0]["y"]

    # Update figure with a vertical line in the top left plot
    fig.update_traces(
        selector={"type": "scatter", "row": 1, "col": 1},
        x=[hovered_voltage] * len(powerCurve),
        mode="lines",
        line={"width": 2, "color": "red", "dash": "dash"}
    )

    # Clear temporary line on hover out (optional)
    # fig.data[2]["x"] = []  # This line would clear the red line on hover out

    return fig

# Run the app
if __name__ == "__main__":
    app.run_server(port = 8070, dev_tools_ui=True,
          dev_tools_hot_reload =True, threaded=True)