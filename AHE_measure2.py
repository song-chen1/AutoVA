"""
This script is used to control the keithley 2450 to apply one gate voltage to 
the sample. the ramp rate can be chosen to reach the gate voltage wanted.
 
 written by Song

Two things should be taken into consideration before using:
1. Address and model of the keithley should be taken care of: @line47 and @line52
2. the address where the results can be exported: @line 266

AutoVA_1.0.1, Features:
1. add the time estimator for the measurment

AutoVA_1.0.2, Features:
1. add the interval between the E-field application and the AHE measurement

07.12.2023: test sucessfully


"""


import logging
import sys  
from time import sleep
import numpy as np
import time
import pyvisa
import os
import matplotlib.animation as animation
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from threading import Thread

from pymeasure.instruments.keithley import Keithley2000, Keithley2400, Keithley2450
from pymeasure.display.Qt import QtGui, QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.display.windows.managed_dock_window import ManagedDockWindow
from pymeasure.display.manager import ExperimentQueue
from pymeasure.experiment import (
    Procedure, FloatParameter, IntegerParameter, unique_filename, Results, Worker
)
# from mkidplotter.gui.workers import Worker
from pymeasure.display.widgets import TableWidget, LogWidget, SequencerWidget
import pymeasure.display.manager as manager
from pymeasure.display.listeners import Monitor
from pymeasure.display.widgets import directory_widget

log = logging.getLogger('')
log.addHandler(logging.NullHandler())



class IVProcedure(Procedure):
    AHE_field = FloatParameter('Maximum current sent to coil (A)', units='A', default=4.0)
    AHE_field_step = FloatParameter('Step (A)', units='A', default=0.1)
    AHE_waiting_time = FloatParameter('Waiting Time (s)', units='s', default=0.2)
    AHE_bias_current = FloatParameter('Bias Current (A)', units='A', default=400e-6)
    CurrentData = []
    HallVData = []
   
    

    DATA_COLUMNS = ['FieldCurrent (A)', 'Hall Voltage (V)']

  


    def startup(self):
        log.info("Setting up, Connecting and configuring instruments")

        rm = pyvisa.highlevel.ResourceManager()
        try:
            self.kepcosource = rm.open_resource("GPIB0::4::INSTR", read_termination="\n",write_termination="\n")
            # print(self.kepcosource.query("*IDN?"))
        except pyvisa.errors.VisaIOError:
            log.info("The KEPCO is OFF!")
            pass
            
            
        
        self.kepcosource.write("*RST")
        self.kepcosource.write("FUNC:MODE CURR")
        self.kepcosource.write("VOLT 20.0")
        self.kepcosource.write("OUTPUT ON; CURR 0.0")
        
       

        self.ahe_source = Keithley2400("GPIB0::24::INSTR")
        self.ahe_source.reset()
        self.ahe_source.write("*CLS")
        self.ahe_source.wires = 4
        self.ahe_source.use_front_terminals()
        self.ahe_source.apply_current()
        self.ahe_source.compliance_voltage = 5  
        self.ahe_source.measure_voltage()
        self.ahe_source.enable_source()                # Enables the source output

        

        sleep(2)

    def Bias_Current(self):
        self.ahe_source.source_current = self.AHE_bias_current
        
    def AHE_loop(self):
        #AHE transport
        AHE_step1 = np.arange(0, self.AHE_field, self.AHE_field_step)
        AHE_step2 = np.arange(self.AHE_field, -self.AHE_field, -self.AHE_field_step)
        AHE_step3 = np.arange(-self.AHE_field, self.AHE_field + self.AHE_field_step, self.AHE_field_step)
        steps = np.concatenate((AHE_step1, AHE_step2, AHE_step3))
        

        self.progress_ahe = len(steps)
        self.al_progress = self.progress_ahe
        for i, fieldcurrent in enumerate(steps):
            self.kepcosource.write("CURR %f"%(fieldcurrent))
            real_fieldcurrent = float(self.kepcosource.query("MEAS:CURR?"))
            self.CurrentData.append(float(self.kepcosource.query("MEAS:CURR?")))
            self.HallVData.append(self.ahe_source.voltage)
            data = {
                'FieldCurrent (A)': real_fieldcurrent,
                'Hall Voltage (V)': self.ahe_source.voltage,
            }
            self.emit('results', data)
            self.emit('progress', 100. *  i / self.al_progress)
            sleep(self.AHE_waiting_time)
       
            if i == len(steps) - 1:
                log.info("AHE Measurement finished")
                self.ahe_source.source_current = 0
                self.kepcosource.write("CURR 0.0")
                self.ahe_source.beep(frequency = 200, duration = 2)
                self.kepcosource.write("SYSTem:BEEP")
                # self.kepcosource.write("MEM:UPDATE SHUTDOWN")
            else:
                pass
    
            if self.should_stop():
                log.warning("Catch stop command in procedure")
                self.ahe_source.shutdown()
                # self.kepcosource.write("MEM:UPDATE SHUTDOWN")
                break

        # np.savetxt(parent_path+'\\Current  

    def execute(self):
        thread_bias = Thread(target=self.Bias_Current())
        thread_ahe = Thread(target=self.AHE_loop())

        #start bothe threads
        thread_bias.start()
        thread_ahe.start()

        #wait for both threads to finish
        thread_bias.join()
        thread_ahe.join()

        # np.savetxt(parent_path+'\\CurrentvsHallV.txt',np.c_[CurrentData,HallVData],fmt='%s')




    def shutdown(self): 
        self.ahe_source.shutdown()
        # self.kepcosource.write("MEM:UPDATE SHUTDOWN")
        
        log.info("Finished")

    def get_estimates(self, sequence_length=None, sequence=None):
        
        duration_ahe = abs(self.AHE_field) / self.AHE_field_step * self.AHE_waiting_time * 5
        duration = duration_ahe 
        
        

        estimates = [
            ("Duration", "%d s" % int(duration)),
            ("Sequence length", str(sequence_length)),
            ('Measurement finished at', str(datetime.now() + timedelta(seconds=duration))),
        ]

        return estimates



class MainWindow(ManagedDockWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=IVProcedure,
            inputs=[
                'AHE_field', 'AHE_field_step', 'AHE_waiting_time', 'AHE_bias_current'
            ],
            displays=[
                'AHE_field', 'AHE_field_step', 'AHE_waiting_time', 'AHE_bias_current'
            ],
            x_axis='FieldCurrent (A)',
            y_axis='Hall Voltage (V)',
            directory_input = True,
            sequencer=True,
            sequencer_inputs=['AHE_field', 'AHE_field_step', 'AHE_waiting_time', 'AHE_bias_current'],
            inputs_in_scrollarea = True,
        )
        self.setWindowTitle('AHE Measurement Automation')
        
       
        
        

    def queue(self, procedure=None):
        if procedure is None:
            procedure = self.make_procedure()
        # global directory
        directory = self.directory
        
        
        
        # Change this to the desired directory
        # #mkdir the folder name with the name of the E-field and time applied
        # CurrentData = IVProcedure().execute().CurrentData
        # HallVData = IVProcedure().execute().HallVData
        # 
        #  
    
        # np.savetxt(parent_path+'\\CurrentvsHallV.txt',np.c_[CurrentData,HallVData],fmt='%s')
        filename = unique_filename(directory, prefix='IV') #from pymeasure.experiment     
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)
        self.manager.queue(experiment)
        
    
                 

        

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())