"""
This script is used to control the Agilent to apply one gate voltage to 
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

from pymeasure.instruments.keithley import Keithley2000, Keithley2400, Keithley2450, Keithley2200
from pymeasure.instruments.agilent import Agilent34410A, Agilent34450A
from pymeasure.display.Qt import QtGui
from pymeasure.display.windows import ManagedWindow
from pymeasure.display.manager import ExperimentQueue
from pymeasure.experiment import (
    Procedure, FloatParameter, IntegerParameter, unique_filename, Results, Worker
)
# from mkidplotter.gui.workers import Worker
# from PyQt5 import QtCore, QtGui, QtWidgets
import pymeasure.display.manager as manager
from pymeasure.display.listeners import Monitor
from PyQt5 import QtCore, QtGui, QtWidgets


log = logging.getLogger('')
log.addHandler(logging.NullHandler())



class IVProcedure(Procedure):

    #max_current = FloatParameter('Maximum Current', units='mA', default=10)
    #min_current = FloatParameter('Minimum Current', units='mA', default=-10)
    #current_step = FloatParameter('Current Step', units='mA', default=0.1)
    max_voltage = FloatParameter('Maximum Voltage', units='mV',default=2000)
    min_voltage = FloatParameter('Minimum Voltage', units='mV',default=-2000)
    voltage_step = FloatParameter('Voltage Step', units='mV', default=20)
    delay = FloatParameter('Delay Time', units='ms', default=20)
    current_range = FloatParameter('Compliance Current', units='uA', default=1.05)
    voltage_dwell_time = FloatParameter('Dwelling Time', units='s', default=30.0)
    


    DATA_COLUMNS = ['Voltage (V)', 'Current (A)', 'Resistance (ohm)']

    def startup(self):
        log.info("Setting up instruments")
        self.IV_source = Keithley2400("GPIB::23")
        self.IV_source.measure_current()
        self.IV_source.current_range = self.current_range * 1e-6
        self.IV_source.current_nplc = 1  # Integration constant to Medium

        self.IV_source = Keithley2400("GPIB::23")
        self.IV_source.apply_voltage()
        #self.IV_source.source_voltage_range = self.max_voltage * 1e-3  # V
        self.IV_source.source_current_range = self.current_range * 1e-6
        self.IV_source.compliance_current = self.current_range * 1e-6 # A
        self.IV_source.enable_source()
        sleep(2)
        
        
        self.IV_source = Keithley2200("GPIB:23")
        self.IV_source.display_enabled = True
        self.channel1 = self.IV_source.ch1
        self.channel2 = self.IV_source.ch2
        self.channel1.voltage_setpoint = 0
        self.channnel1.output_enabled = True

        self.IV_source = Agilent34110A("GPIB::04")



    def execute(self):
        voltages_up = np.arange(self.min_voltage, self.max_voltage, self.voltage_step)
        voltages_down = np.arange(self.max_voltage, self.min_voltage, -self.voltage_step)
        minus_voltages_up = np.arange(self.min_voltage, self.max_voltage, self.voltage_step)
        minus_voltages_down = np.arange(self.max_voltage, self.min_voltage, -self.voltage_step)
        #currents = np.concatenate((currents_up, currents_down))  # Include the reverse
        #currents *= 1e-3  # to mA from A
        voltages_up *= 1e-3 # to mV from V
        voltages_down *= 1e-3
        minus_voltages_up *=1e-3
        minus_voltages_down *=1e-3
        voltages = voltages_up + voltages_down
        #voltages_negative = minus_voltages_down + minus_voltages_up

        steps = len(voltages) + int(self.voltage_dwell_time)
        #temp = time.second.get(self.voltage_dwell_time)
        


        log.info("Starting to sweep through voltage")


        if self.max_voltage > 0:
            for i, voltage in enumerate(voltages_up):
                log.debug("Measuring voltage: %g mV" % voltage)

                self.channel1.voltage_setpoint = voltage
                # Or use self.IV_source.ramp_to_current(current, delay=0.1)


                if voltage >= ((self.max_voltage * 1e-3) - ((self.voltage_step) * 1e-3)):
                    temp = self.voltage_dwell_time
                    while temp > -1:
                        #self.IV_source.source_voltage = (self.max_voltage * 1e-3)
                        self.channel1.voltage_setpoint = self.max_voltage * 1e-3 
                        voltage = self.channel1.voltage * 1e-3
                        
                        timer = '{0:f}'.format(temp)
                        print(timer, end="\r")
                        time.sleep(1)
                        temp -=1

                        #sleep(self.delay * 1e-3)

                        current = self.channnel1.current

                        if abs(current) <= 1e-10:
                            resistance = np.nan
                        else:
                            resistance = voltage / current
                        data = {
                            'Voltage (V)': voltage,
                            'Current (A)': current,
                            'Resistance (ohm)': resistance
                        }

                        self.emit('results', data)
                        # self.emit('progress', 100. * i / steps)
                        if self.should_stop():
                            log.warning("Catch stop command in procedure")
                            break

                        if temp == -1:
                            for i, voltage in enumerate(voltages_down):
                                self.channel1.voltage_setpoint = voltage
                                sleep(self.delay * 1e-3)

                                current = self.channel1.current

                                if abs(current) <= 1e-10:
                                    resistance = np.nan
                                else:
                                    resistance = voltage / current
                                data = {
                                    'Voltage (V)': voltage,
                                    'Current (A)': current,
                                    'Resistance (ohm)': resistance
                                }
                                self.emit('results', data)
                                # self.emit('progress', 100. * i / steps)
                                if self.should_stop():
                                    log.warning("Catch stop command in procedure")
                                    break


                        else:
                            pass
                else:
                    pass

                sleep(self.delay * 1e-3)

                current = self.IV_source.current

                if abs(current) <= 1e-10:
                    resistance = np.nan
                else:
                    resistance = voltage / current
                data = {
                    'Voltage (V)': voltage,
                    'Current (A)': current,
                    'Resistance (ohm)': resistance
                }
                self.emit('results', data)
                # self.emit('progress', 100. * i / steps)
                if self.should_stop():
                    log.warning("Catch stop command in procedure")
                    break
        else:
            for i, voltage in enumerate(minus_voltages_down):
                log.debug("Measuring voltage: %g mV" % voltage)

                self.IV_source.source_voltage = voltage
                # Or use self.IV_source.ramp_to_current(current, delay=0.1)

                if voltage <= ((self.min_voltage * 1e-3) + ((self.voltage_step) * 1e-3)):
                    temp = self.voltage_dwell_time
                    while temp > -1:
                        self.IV_source.source_voltage = self.min_voltage * 1e-3
                        voltage = self.IV_source.source_voltage
                        
                        timer = '{0:f}'.format(temp)
                        print(timer, end="\r")
                        time.sleep(1)
                        temp -=1

                        #sleep(self.delay * 1e-3)

                        current = self.IV_source.current

                        if abs(current) <= 1e-10:
                            resistance = np.nan
                        else:
                            resistance = voltage / current
                        data = {
                            'Voltage (V)': voltage,
                            'Current (A)': current,
                            'Resistance (ohm)': resistance
                        }

                        self.emit('results', data)
                        # self.emit('progress', 100. * i / steps)

                        if self.should_stop():
                            log.warning("Catch stop command in procedure")
                            break

                        if temp == -1:
                            for i, voltage in enumerate(minus_voltages_up):
                                self.IV_source.source_voltage = voltage
                                sleep(self.delay * 1e-3)

                                current = self.IV_source.current

                                if abs(current) <= 1e-10:
                                    resistance = np.nan
                                else:
                                    resistance = voltage / current
                                data = {
                                    'Voltage (V)': voltage,
                                    'Current (A)': current,
                                    'Resistance (ohm)': resistance
                                }
                                self.emit('results', data)
                                # self.emit('progress', 100. * i / steps)
                                if self.should_stop():
                                    log.warning("Catch stop command in procedure")
                                    break

                        else:
                            pass
                else:
                    pass

                sleep(self.delay * 1e-3)

                current = self.IV_source.current

                if abs(current) <= 1e-10:
                    resistance = np.nan
                else:
                    resistance = voltage / current
                data = {
                    'Voltage (V)': voltage,
                    'Current (A)': current,
                    'Resistance (ohm)': resistance
                }
                self.emit('results', data)
                # if ExperimentQueue.has_next(experiment):
                #     ExperimentQueue.next(experiment)
                # self.emit('progress', 100. * i / steps)

                if self.should_stop():
                    log.warning("Catch stop command in procedure")
                    break



    def shutdown(self):
        self.IV_source.shutdown()
        self.IV_source.beep(frequency = 200, duration = 2)
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
            sequencer=False,
            sequencer_inputs=['max_voltage', 'voltage_dwell_time', 'min_voltage', 'voltage_step', 'delay', 'current_range']
        )
        self.setWindowTitle('IV Measurement')

    def queue(self):
        directory = self.directory  # Change this to the desired directory
        filename = unique_filename(directory, prefix='IV') #from pymeasure.experiment

       
        procedure = self.make_procedure()
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)
        self.manager.queue(experiment)

        # self.Exprerimentqueue.queue.append(experiment)

# class Experimentqueue(manager.ExperimentQueue):
#     """ Represents a Queue of Experiments and allows queries to
#     be easily preformed
#     """

#     def __init__(self):
#         super().__init__()
#         self.queue = []

#     def append(self, experiment):
#         self.queue.append(experiment)

#     def remove(self, experiment):
#         if experiment not in self.queue:
#             raise Exception("Attempting to remove an Experiment that is "
#                             "not in the ExperimentQueue")
#         else:
#             if experiment.procedure.status == Procedure.RUNNING:
#                 raise Exception("Attempting to remove a running experiment")
#             else:
#                 self.queue.pop(self.queue.index(experiment))

#     def __contains__(self, value):
#         if isinstance(value, Experiment):
#             return value in self.queue
#         if isinstance(value, str):
#             for experiment in self.queue:
#                 if basename(experiment.data_filename) == basename(value):
#                     return True
#             return False
#         return False

#     def __getitem__(self, key):
#         return self.queue[key]

#     def next(self):
#         """ Returns the next experiment on the queue
#         """
#         for experiment in self.queue:
#             if experiment.procedure.status == Procedure.QUEUED:
#                 return experiment
#         raise StopIteration("There are no queued experiments")

#     def has_next(self):
#         """ Returns True if another item is on the queue
#         """
#         try:
#             self.next()
#         except StopIteration:
#             return False

#         return True

#     def with_browser_item(self, item):
#         for experiment in self.queue:
#             if experiment.browser_item is item:
#                 return experiment
#         return None
        


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
