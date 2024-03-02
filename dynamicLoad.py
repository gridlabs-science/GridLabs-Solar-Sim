class dynamicLoad:
    #pwrScaleUpSpeed = 100 #Watts per minute.  Speed at which it can increase power consumption
    #pwrScaleDownSpeed = 100 
    #curtailDelay = 1 #in seconds.  The delay between being given the command to switch to standby/low power mode, and the time power use is actually reduced.


    def __init__(self, pwrScaleUpSpeed, pwrScaleDownSpeed, curtailDelay, maxPower, minPower, capacitorSize, initialPanelVoltage, initialCapVoltage):
        self.pwrScaleUpSpeed = pwrScaleUpSpeed
        self.pwrScaleDownSpeed = pwrScaleDownSpeed
        self.curtailDelay = curtailDelay
        self.maxPower = maxPower
        self.target = maxPower
        self.minPower = minPower
        self.state = 'running' # also 'curtailed', 'curtailing' (given delay between command and power reduction)
        self.curtailTime = 0 # the time since the "curtail" command was given.  Used for the curtail delay logic
        self.capacitorSize = capacitorSize # the size of the capacitor in Farads
        self.lastPanelVoltage = initialPanelVoltage
        self.lastCapVoltage = initialCapVoltage
        self.lastPower = self.target

    def get_power(self, panelVoltage, capacitorVoltage, dt):
        #First, calculate the amps to/from the cap based on the delta in capacitor voltage
        # Increasing voltage means capacitor is charging.  Positive values of 'capAmps' indicate panel power is greater than load power
        capAmps = (capacitorVoltage - self.lastCapVoltage) / (self.capacitorSize * dt)

        #Next, calculate the average power coming from the panel
        panelPower = self.lastPower + capAmps * (capacitorVoltage + self.lastCapVoltage)/2

        return 15





