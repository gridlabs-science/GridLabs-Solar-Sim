import panel

class dynamicLoad:
    #pwrScaleUpSpeed = 100 #Watts per minute.  Speed at which it can increase power consumption
    #pwrScaleDownSpeed = 100 
    #curtailDelay = 1 #in seconds.  The delay between being given the command to switch to standby/low power mode, and the time power use is actually reduced.


    def __init__(self, pwrScaleUpSpeed, pwrScaleDownSpeed, curtailDelay, maxPower, minPower, capacitorSize, initialPanelVoltage, initialCapVoltage):
        #system constants
        self.pwrScaleUpSpeed = pwrScaleUpSpeed
        self.pwrScaleDownSpeed = pwrScaleDownSpeed
        self.curtailDelay = curtailDelay
        self.maxPower = maxPower
        self.minPower = minPower
        self.capacitorSize = capacitorSize # the size of the capacitor in Farads
        #variables for initialization.  ALL of these should be updated each time "get_power()" is called
        self.target = maxPower
        self.state = 'running' # also 'curtailed', 'curtailing' (given delay between command and power reduction)
        self.curtailTime = 0 # the time since the "curtail" command was given.  Used for the curtail delay logic
        self.lastPanelVoltage = initialPanelVoltage
        self.lastCapVoltage = initialCapVoltage
        self.lastPower = self.target

    def get_power(self, panelVoltage, capacitorVoltage, dt, solarPanel):
        #First, calculate the amps to/from the cap based on the delta in capacitor voltage
        # Increasing voltage means capacitor is charging.  Positive values of 'capAmps' indicate panel power is greater than load power
        capAmps = (capacitorVoltage - self.lastCapVoltage) / (self.capacitorSize * dt)

        #Next, calculate the average power coming from the panel
        avgCapVolts = (capacitorVoltage + self.lastCapVoltage)/2
        avgPanelPower = self.lastPower + capAmps * avgCapVolts

        #Calculate panel irradiance based on its power output and panel voltage
        avgPanelVolts = (self.lastPanelVoltage + panelVoltage) / 2
        avgPanelCurrent = avgPanelPower / avgPanelVolts
        irr = solarPanel.get_irradiance(avgPanelCurrent, avgPanelVolts)  #returns an estimate for the panel irradiance.  Max is 1000 W/m^2
        
        #Calculate the max power available, if panel was at MPP, given current irradiance:
        powerAvailable = solarPanel.panel_output(solarPanel.Vmp, irr)

        #Update target power to equal the incoming panel power, adjusted for buffer decrement
        self.target = powerAvailable * 0.75

        #if self.target < self.minPower:
            #Curtail, because we can't run slow enough


        return 15





