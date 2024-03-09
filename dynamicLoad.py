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
        self.bootTime = 0    # the time since the "boot" command was given.  Used for the boot delay logic, i.e. time between boot and power on hashing.
        self.lastPanelVoltage = initialPanelVoltage
        #self.lastCapVoltage = initialCapVoltage
        self.lastPower = self.target
        

    def get_power(self, panelVoltage, dt, solarPanel):
        #First, calculate the amps to/from the cap based on the delta in capacitor voltage
        # Increasing voltage means capacitor is charging.  Positive values of 'capAmps' indicate panel power is greater than load power
        #capAmps = (panelVoltage - self.lastPanelVoltage) / (self.capacitorSize * dt)

        #Next, calculate the average power coming from the panel
        #avgCapVolts = (panelVoltage + self.lastPanelVoltage)/2
        #avgPanelPower = capAmps * avgCapVolts + self.lastPower
        dV = panelVoltage - self.lastPanelVoltage
        capPower = (0.5 * self.capacitorSize * (dV)**2) / dt
        if dV < 0: capPower = -1 * capPower
        avgPanelPower = self.lastPower + capPower

        #Calculate panel irradiance based on its power output and panel voltage
        #avgPanelCurrent = avgPanelPower / panelVoltage #panelVoltage  # or avgCapVolts?  or lastPanelVolts?
        avgPanelCurrent = self.capacitorSize * dV / dt
        irr = solarPanel.get_irradiance(avgPanelCurrent, self.lastPanelVoltage)  #returns an estimate for the panel irradiance.  Max is 1000 W/m^2
        
        #Calculate the max power available, if panel was at MPP, given current irradiance:
        powerAvailable = solarPanel.Vmp * solarPanel.panel_output(solarPanel.Vmp, irr)
        print("power available = " + str(powerAvailable) + "  /  irr = " + str(irr) + " / avgI = " + str(avgPanelCurrent) + " / avgPanelPower = " + str(avgPanelPower) + " | capPower = " + str(capPower))
        #print("             capAmps " + str(capAmps) + " | capPower " + str(capPower))

        #Update target power to equal the incoming panel power, adjusted for buffer decrement.  1.0 = MPPT.  < 1 gives a buffer to deal with reaction delays.
        self.target = powerAvailable * self.targetDecrement
        if(self.target > self.maxPower): self.target = self.maxPower

        # State machine logic
        if self.state == 'curtailing':  # So we already began the process of shutting down
            self.curtailTime = self.curtailTime + dt
            if self.curtailTime >= self.curtailDelay:  #We've waited the requisite delay time, so chip is now in standby mode
                self.curtailTime = 0
                self.state = 'curtailed'
                self.lastPower = 0
        elif self.state == 'booting':
            self.bootTime = self.bootTime + dt
            if self.bootTime >= self.bootDelay:  #We've fully booted, so start the ASIC at min power
                self.bootTime = 0
                self.state = 'running'
                self.lastPower = self.minPower
        elif self.state == 'curtailed':
            if self.target > self.minPower and panelVoltage > solarPanel.Vmp:  #Panel is now producing more than min power. Wait until the capacitor is charged enough to push the panel to the right side of Vmp
                self.state = 'booting'
                self.bootTime = 0
            self.lastPower = 0
        else: #We must be running
            if self.target < self.minPower: #Curtail, because we can't run slow enough
                self.state = 'curtailing'
                self.curtailTime = 0
            #Logic for slowly scaling the power to chase the target
            newPower = self.lastPower
            if self.target <= self.lastPower:  #Target is lower than current power, so scale it back
                newPower = self.lastPower - self.pwrScaleDownSpeed * dt
            else:                              # Otherwise, target is higher than current power, so push it up!
                newPower = self.lastPower + self.pwrScaleUpSpeed * dt
            self.lastPower = newPower

        # Reset all the "last recent value of X" numbers
        self.lastPanelVoltage = panelVoltage

        return self.lastPower   # Finally, return whatever the latest and greatest power draw is.





