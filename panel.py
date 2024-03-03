class panel:
    def __init__(self, Voc, Vmp, Isc, Imp, maxPower):
        self.Voc = Voc
        self.Vmp = Vmp
        self.Isc = Isc
        self.Imp = Imp
        self.maxPower = maxPower
        # Other prepartory calculations:
        #The following equations are taken from this paper:  https://oa.upm.es/43747/1/PindadoRE20016.pdf
        #eta = (1.0/0.11175) * (Isc/Imp) * (Voc/Vmp - 1.0)  # First estimate for Eta (greek letter)
        self.eta = (Isc/Imp) * (Isc / (Isc-Imp)) * ((Voc-Vmp)/Voc)  # Second estimate for Eta (different method)

    def panel_output(self, PV, IR):
        #args:
        #PV = solar panel voltage, instantaneous.  The voltage the panel is now being driven at by the buck converter/capacitor.
        #IR = irradiance, instantaneous.  In watts / meter^2.  1000 is max blast, full solar power.
        amps = 0

        #The following equations are taken from this paper:  https://oa.upm.es/43747/1/PindadoRE20016.pdf
        if(PV < self.Vmp):
            amps = self.Isc * (1 - (1 - (self.Imp/self.Isc)) * (PV/self.Vmp)**(self.Imp/(self.Isc-self.Imp)))
        else:
            amps = self.Imp * (self.Vmp/PV) * (1 - ((PV-self.Vmp) / (self.Voc-self.Vmp))**self.eta) 

        # now do linear scaling to adjust for irradiance.  This is an approximation, but good enough for our purposes IMO
            # also this assumes even illumination.  With partial shading/occlusion the power curve can get really wacked out and impossible to model
        perc = IR / 1000  #1000 IR is perfect full sun, max blast, all systems go, given er all she's got scotty
        amps = perc * amps
        if amps < 0:
            return 0
        else:
            return amps
    
    def get_irradiance(self, V, I):
        maxCurrent = self.panel_output(V, 1000) #what should the current be IF the irradiance were perfect 1000
        irr = 1000
        #Now do the reverse algebra of the equations in 'panel_output'
        #TODO: this math...

        return irr