import panel

class dynamicLoad:
    #pwrScaleUpSpeed = 100 #Watts per minute.  Speed at which it can increase power consumption
    #pwrScaleDownSpeed = 100 
    #curtailDelay = 1 #in seconds.  The delay between being given the command to switch to standby/low power mode, and the time power use is actually reduced.


    def __init__(self, pwrScaleUpSpeed, pwrScaleDownSpeed, curtailDelay, bootDelay, maxPower, minPower, capacitorSize, initialPanelVoltage, targetDecrement):
        #system constants
        self.pwrScaleUpSpeed = pwrScaleUpSpeed
        self.pwrScaleDownSpeed = pwrScaleDownSpeed
        self.curtailDelay = curtailDelay
        self.bootDelay = bootDelay
        self.maxPower = maxPower
        self.minPower = minPower
        self.capacitorSize = capacitorSize # the size of the capacitor in Farads
        self.targetDecrement = targetDecrement
        #variables for initialization.  ALL of these should be updated each time "get_power()" is called
        self.target = maxPower
        self.state = 'running' # also 'curtailed', 'curtailing', and 'booting' (given delay between command and power reduction)
        self.curtailTime = 0 # the time since the "curtail" command was given.  Used for the curtail delay logic
        self.lastPanelVoltage = initialPanelVoltage
        #self.lastCapVoltage = initialCapVoltage
        self.lastPower = self.target
        

    def get_power(self, panelVoltage, dt, solarPanel):
        #First, calculate the amps to/from the cap based on the delta in capacitor voltage
        # Increasing voltage means capacitor is charging.  Positive values of 'capAmps' indicate panel power is greater than load power
        capAmps = (panelVoltage - self.lastPanelVoltage) / (self.capacitorSize * dt)

        #Next, calculate the average power coming from the panel
        avgCapVolts = (panelVoltage + self.lastPanelVoltage)/2
        avgPanelPower = self.lastPower + capAmps * avgCapVolts

        #Calculate panel irradiance based on its power output and panel voltage
        avgPanelCurrent = avgPanelPower / avgCapVolts
        irr = solarPanel.get_irradiance(avgPanelCurrent, avgCapVolts)  #returns an estimate for the panel irradiance.  Max is 1000 W/m^2
        
        #Calculate the max power available, if panel was at MPP, given current irradiance:
        powerAvailable = solarPanel.panel_output(solarPanel.Vmp, irr)

        #Update target power to equal the incoming panel power, adjusted for buffer decrement.  1.0 = MPPT.  < 1 gives a buffer to deal with reaction delays.
        self.target = powerAvailable * self.targetDecrement

        # State machine logic
        if self.state == 'curtailing':  # So we already began the process of shutting down
            self.curtailTime = self.curtailTime + dt
            if self.curtailTime >= self.curtailDelay:  #We've waited the requisite delay time, so chip is now in standby mode
                self.curtailTime = 0
                self.state = 'curtailed'
                self.lastPower = 0
        if self.state == 'booting':
            self.curtailTime = self.curtailTime + dt
            if self.curtailTime >= self.bootDelay:  #We've fully booted, so start the ASIC at min power
                self.curtailTime = 0
                self.state = 'running'
                self.lastPower = self.minPower

        if self.target < self.minPower: #Curtail, because we can't run slow enough
            self.state = 'curtailing'
            self.curtailTime = 0
        if self.target > self.minPower:
            self.target = self.target



        return self.lastPower





