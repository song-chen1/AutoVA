"""
This script is used to control the keithley 2450 to apply one gate voltage to 
the sample. the ramp rate can be chosen to reach the gate voltage wanted.
 
 written by Song

Two things should be taken into consideration before using:
1. Address and model of the keithley should be taken care of: @line47 and @line52
2. the address where the results can be exported: @line 266

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


from pymeasure.instruments.keithley import Keithley2000, Keithley2400, Keithley2450, Keithley2200
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

    max_voltage = FloatParameter('Maximum Voltage', units='mV',default=2000)
    min_voltage = FloatParameter('Minimum Voltage', units='mV',default=-2000)
    voltage_step = FloatParameter('Voltage Step', units='mV', default=20)
    delay = FloatParameter('Delay Time', units='ms', default=100)
    current_range = FloatParameter('Compliance Current', units='uA', default=1.05)
    voltage_dwell_time = FloatParameter('Dwelling Time', units='s', default=30.0)
    DATA_COLUMNS = ['Voltage (V)', 'Current (A)', 'Resistance (ohm)']

    def startup(self):
        log.info("Setting up instruments")        
        
        self.IV_source = Keithley2200("GPIB::23")
        
        # self.IV_source.write("SOURCE:FUNC:MODE FIX")
        self.IV_source.display_enabled = True
        
        self.channel1 = self.IV_source.ch_1
        self.IV_source.write("SOURCE:FUNC:MODE FIX")
        # self.channel1.output_enabled = True
        self.IV_source.current_limit = self.current_range * 1e-6
        self.IV_source.output_enabled = True
        
    def Efield_apply(self):
        
        self.IV_source.source_voltage = self.voltage
        
    def measure_voltage(self):
        self.mes_voltage = self.IV_source.voltage
        
    def measure_current(self):
        self.current = self.IV_source.current
        print(self.current)
        
    def PBias_voltage(self):
       
        self.IV_source.source_voltage = self.max_voltage * 1e-3
        
    def NBias_voltage(self):
       
        self.IV_source.source_voltage = self.min_voltage * 1e-3
        
    def Efield_threading(self):
        thread_Efield_apply = Thread(target=self.Efield_apply())
        thread_measure_voltage = Thread(target=self.measure_voltage())
        thread_measrue_current = Thread(target=self.measure_current())
        
        thread_Efield_apply.start()
        thread_measrue_current.start()
        thread_measure_voltage.start()
        
        thread_Efield_apply.join()
        thread_measrue_current.join()
        thread_measure_voltage.join()
        
    def PBias_threading(self):
        thread_PBias_voltage = Thread(target=self.PBias_voltage())
        thread_measure_voltage = Thread(target=self.measure_voltage())
        thread_measrue_current = Thread(target=self.measure_current())
        
        thread_PBias_voltage.start()
        thread_measrue_current.start()
        thread_measure_voltage.start()
        
        thread_PBias_voltage.join()
        thread_measrue_current.join()
        thread_measure_voltage.join()
        
    def NBias_threading(self):
        thread_NBias_voltage = Thread(target=self.NBias_voltage())
        thread_measure_voltage = Thread(target=self.measure_voltage())
        thread_measrue_current = Thread(target=self.measure_current())
        
        thread_NBias_voltage.start()
        thread_measrue_current.start()
        thread_measure_voltage.start()
        
        thread_NBias_voltage.join()
        thread_measrue_current.join()
        thread_measure_voltage.join()  

    def execute(self):

        """
        apply the E-field to the sample
        """
        # define the voltages arrary for the E-field application
        voltages_up = np.arange(self.min_voltage, self.max_voltage, self.voltage_step)
        voltages_down = np.arange(self.max_voltage, self.min_voltage - self.voltage_step , -self.voltage_step)
        minus_voltages_up = np.arange(self.min_voltage, self.max_voltage + self.voltage_step, self.voltage_step)
        minus_voltages_down = np.arange(self.max_voltage, self.min_voltage, -self.voltage_step)
        # to mV from V
        voltages_up *= 1e-3 
        voltages_down *= 1e-3
        minus_voltages_up *=1e-3
        minus_voltages_down *=1e-3

        self.progress_ef_1 = len(voltages_up)
        self.progress_ef_2 = self.voltage_dwell_time
        self.progress_ef_3 = len(voltages_down)
        self.al_progress = self.progress_ef_1 + self.progress_ef_2 + self.progress_ef_3
        


        log.info("Starting to sweep through voltage")


        if self.max_voltage > 0:
            for i, voltage in enumerate(voltages_up):
                self.voltage = voltage
                log.debug("Measuring voltage: %g mV" % voltage)
                self.Efield_threading()

                if voltage >= ((self.max_voltage * 1e-3) - ((self.voltage_step) * 1e-3)):
                    temp = self.voltage_dwell_time
                    while temp > -1:
                        self.PBias_threading()
                        timer = '{0:f}'.format(temp)
                        print(timer, end="\r")
                        time.sleep(1)
                        temp -=1

                        if abs(self.current) <= 1e-10:
                            resistance = np.nan
                        else:
                            resistance = self.voltage / self.current
                        data = {
                            'Voltage (V)': self.mes_voltage,
                            'Current (A)': self.current,
                            'Resistance (ohm)': resistance
                        }

                        self.emit('results', data)
                        # self.emit('progress', 100. * i / steps)
                        if self.should_stop():
                            log.warning("Catch stop command in procedure")
                            break

                        if temp == -1:
                            for i, voltage in enumerate(voltages_down):
                                self.voltage = voltage
                                self.Efield_threading()
                                sleep(self.delay * 1e-3)

                                if abs(self.current) <= 1e-10:
                                    resistance = np.nan
                                else:
                                    resistance = self.voltage / self.current
                                data = {
                                    'Voltage (V)': self.mes_voltage,
                                    'Current (A)': self.current,
                                    'Resistance (ohm)': resistance
                                }
                                self.emit('results', data)
                                # self.emit('progress', 100. * i / steps)
                                if self.should_stop():
                                    self.IV_source.output_enabled = False
                                    log.warning("Catch stop command in procedure")
                                    break


                        else:
                            pass
                else:
                    pass

                

                sleep(self.delay * 1e-3)
                
                if abs(self.current) <= 1e-10:
                    resistance = np.nan
                else:
                    resistance = self.voltage / self.current
                data = {
                    'Voltage (V)': self.mes_voltage,
                    'Current (A)': self.current,
                    'Resistance (ohm)': resistance
                }
                self.emit('results', data)
                # self.emit('progress', 100. * i / steps)
                if self.should_stop():
                    self.IV_source.output_enabled = False
                    log.warning("Catch stop command in procedure")
                    break
        else:
            for i, voltage in enumerate(minus_voltages_down):
                self.voltage = voltage
                log.debug("Measuring voltage: %g mV" % voltage)
                self.Efield_threading()

                if voltage <= ((self.min_voltage * 1e-3) + ((self.voltage_step) * 1e-3)):
                    temp = self.voltage_dwell_time
                    while temp > -1:
                        self.NBias_threading()
                        timer = '{0:f}'.format(temp)
                        print(timer, end="\r")
                        time.sleep(1)
                        temp -=1

                        if abs(self.current) <= 1e-10:
                            resistance = np.nan
                        else:
                            resistance = self.voltage / self.current
                        data = {
                            'Voltage (V)': self.voltage,
                            'Current (A)': self.current,
                            'Resistance (ohm)': resistance
                        }

                        self.emit('results', data)
                        # self.emit('progress', 100. * i / steps)

                        if self.should_stop():
                            self.IV_source.output_enabled = False
                            log.warning("Catch stop command in procedure")
                            break

                        if temp == -1:
                            for i, voltage in enumerate(minus_voltages_up):
                                self.voltage = voltage
                                self.Efield_threading()
                                sleep(self.delay * 1e-3)

                                if abs(self.current) <= 1e-10:
                                    resistance = np.nan
                                else:
                                    resistance = self.voltage / self.current
                                data = {
                                    'Voltage (V)': self.voltage,
                                    'Current (A)': self.current,
                                    'Resistance (ohm)': resistance
                                }
                                self.emit('results', data)
                                # self.emit('progress', 100. * i / steps)
                                if self.should_stop():
                                    self.IV_source.output_enabled = False
                                    log.warning("Catch stop command in procedure")
                                    break

                        else:
                            pass
                else:
                    pass

                sleep(self.delay * 1e-3)

                if abs(self.current) <= 1e-10:
                    resistance = np.nan
                else:
                    resistance = self.voltage / self.current
                data = {
                    'Voltage (V)': self.voltage,
                    'Current (A)': self.current,
                    'Resistance (ohm)': resistance
                }
                self.emit('results', data)
                # if ExperimentQueue.has_next(experiment):
                #     ExperimentQueue.next(experiment)
                # self.emit('progress', 100. * i / steps)

                if self.should_stop():
                    self.IV_source.output_enabled = False
                    log.warning("Catch stop command in procedure")
                    break



    def shutdown(self):
        self.IV_source.output_enabled = False
        # self.IV_source.beep(frequency = 200, duration = 2)
        # self.IV_source.enable_source()
        log.info("Finished")




class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=IVProcedure,
            inputs=[
                'max_voltage','voltage_dwell_time', 'min_voltage', 'voltage_step',
                'delay', 'current_range'
            ],
            displays=[
                'max_voltage', 'voltage_dwell_time', 'min_voltage', 'voltage_step', 
                'delay', 'current_range'
            ],
            x_axis='Voltage (V)',
            y_axis='Current (A)',
            directory_input = True,
            sequencer = True,
            sequencer_inputs=['max_voltage', 'voltage_dwell_time', 'min_voltage', 'voltage_step', 'delay', 'current_range']
        )
        self.setWindowTitle('IV Measurement')

    def queue(self, procedure=None):
        if procedure is None:
            procedure = self.make_procedure()
        directory = self.directory  # Change this to the desired directory
        filename = unique_filename(directory, prefix='IV') #from pymeasure.experiment      
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)
        self.manager.queue(experiment)
        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
