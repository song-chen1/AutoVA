"""
This script is used to control the keithley 2450 to apply one gate voltage to 
the sample. the ramp rate can be chosen to reach the gate voltage wanted.
 
 written by Song

Two things should be taken into consideration before using:
1. Address and model of the keithley should be taken care of: @line47 and @line52
2. the address where the results can be exported: @line 266
=
"""

import logging
import sys
from time import sleep
import numpy as np
import time
from datetime import datetime, timedelta

from pymeasure.instruments.keithley import Keithley2000, Keithley2400, Keithley2450
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
from pymeasure.display.widgets import TableWidget, LogWidget, SequencerWidget


log = logging.getLogger('')
log.addHandler(logging.NullHandler())





# class Manager(manager.Manager):
#     """Extension of the pymeasure Manager class to allow for multiple plots."""
#     def load(self, experiment):
#         """ Load a previously executed Experiment
#         """
#         for index, plot in enumerate(self.plot):
#             for curve in experiment.curve[index]:
#                 plot.addItem(curve)
#         self.browser.add(experiment)
#         self.experiments.append(experiment)

#     def remove(self, experiment):.
#         """ Removes an Experiment
#         """
#         self.experiments.remove(experiment)
#         self.browser.takeTopLevelItem(
#             self.browser.indexOfTopLevelItem(experiment.browser_item))
#         for index, plot in enumerate(self.plot):
#             for curve in experiment.curve[index]:
#                 plot.removeItem(curve)

    # def next(self):
    #     """
    #     Initiates the start of the next experiment in the queue as long
    #     as no other experiments are currently running and there is a procedure
    #     in the queue. Uses the Worker class from mkidplotter instead of pymeasure.
    #     """
    #     if self.is_running():
    #         raise Exception("Another procedure is already running")
    #     else:
    #         if self.experiments.has_next():
    #             log.debug("Manager is initiating the next experiment")
    #             experiment = self.experiments.next()
    #             self._running_experiment = experiment

    #             self._worker = Worker(experiment.results, port=self.port,
    #                                   log_level=self.log_level)

    #             self._monitor = Monitor(self._worker.monitor_queue)
    #             self._monitor.worker_running.connect(self._running)
    #             self._monitor.worker_failed.connect(self._failed)
    #             self._monitor.worker_abort_returned.connect(self._abort_returned)
    #             self._monitor.worker_finished.connect(self._finish)
    #             self._monitor.progress.connect(self._update_progress)
    #             self._monitor.status.connect(self._update_status)
    #             self._monitor.log.connect(self._update_log)

    #             self._monitor.start()
    #             self._worker.start()

#     def _running(self):
#         if self.is_running():
#             self.running.emit(self._running_experiment)
#             for index in range(self.browser.columnCount()):  # resize so "Running" fits in the browser column
#                 self.browser.resizeColumnToContents(index)

#     def _finish(self):
#         log.debug("Manager's running experiment has finished")
#         experiment = self._running_experiment
#         self._clean_up()
#         experiment.browser_item.setProgress(100.)
#         for index, _ in enumerate(self.plot):
#             for curve in experiment.curve[index]:
#                 curve.update()
#         self.finished.emit(experiment)
#         if self._is_continuous:  # Continue running procedures
#             self.next()


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
        self.meter = Keithley2450("GPIB1::24")
        self.meter.measure_current()
        self.meter.current_range = self.current_range * 1e-6
        self.meter.current_nplc = 1  # Integration constant to Medium

        self.source = Keithley2450("GPIB1::24")
        self.source.apply_voltage()
        #self.source.source_voltage_range = self.max_voltage * 1e-3  # V
        self.source.source_current_range = self.current_range * 1e-6
        self.source.compliance_current = self.current_range * 1e-6 # A
        self.source.enable_source()
        sleep(2)


    def execute(self):
        voltages_up = np.arange(self.min_voltage, self.max_voltage, self.voltage_step)
        voltages_down = np.arange(self.max_voltage, self.min_voltage - self.voltage_step , -self.voltage_step)
        minus_voltages_up = np.arange(self.min_voltage, self.max_voltage + self.voltage_step, self.voltage_step)
        minus_voltages_down = np.arange(self.max_voltage, self.min_voltage, -self.voltage_step)
        #currents = np.concatenate((currents_up, currents_down))  # Include the reverse
        #currents *= 1e-3  # to mA from A
        voltages_up *= 1e-3 # to mV from V
        voltages_down *= 1e-3 # to mV from V
        minus_voltages_up *=1e-3 # to mV from V
        minus_voltages_down *=1e-3 # to mV from V

        # for the progress bar
        self.progress_ef_1 = len(voltages_up)
        self.progress_ef_2 = self.voltage_dwell_time
        self.progress_ef_3 = len(voltages_down)
        self.al_progress = self.progress_ef_1 + self.progress_ef_2 + self.progress_ef_3

        log.info("Starting to sweep through voltage")


        if self.max_voltage > 0:
            for i, voltage in enumerate(voltages_up):
                log.debug("Measuring voltage: %g mV" % voltage)

                self.source.source_voltage = voltage
                current = self.meter.current
                sleep(self.delay * 1e-3)
                # Or use self.source.ramp_to_current(current, delay=0.1)

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
                self.emit('progress', 100. * i / self.al_progress)

                if voltage >= ((self.max_voltage * 1e-3) - ((self.voltage_step) * 1e-3)):
                    temp = self.voltage_dwell_time
                    while temp > -1:
                        #self.source.source_voltage = (self.max_voltage * 1e-3)
                        self.source.source_voltage = self.max_voltage * 1e-3 
                        voltage = self.max_voltage * 1e-3
                        current = self.meter.current

                        timer = '{0:f}'.format(temp)
                        print(timer, end="\r")
                        time.sleep(1)
                        temp_rest = self.voltage_dwell_time - temp
                        temp -=1
                    
                        #sleep(self.delay * 1e-3)        

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
                        self.emit('progress', 100. * (self.progress_ef_1 + temp_rest) / self.al_progress)
                        # self.emit('progress', 100. * i / steps)
                        if self.should_stop():
                            log.warning("Catch stop command in procedure")
                            self.source.shutdown()  
                            break

                        if temp == -1:
                            for i, voltage in enumerate(voltages_down):
                                self.source.source_voltage = voltage
                                current = self.meter.current
                                sleep(self.delay * 1e-3)

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
                                self.emit('progress', 100. * (self.progress_ef_1 + self.voltage_dwell_time + i) / self.al_progress)
                                # self.emit('progress', 100. * i / steps)
                                if self.should_stop():
                                    log.warning("Catch stop command in procedure")
                                    self.source.shutdown()  
                                    break

                        else:
                            pass
                else:
                    pass

                # self.emit('progress', 100. * i / steps)
                if self.should_stop():
                    log.warning("Catch stop command in procedure")
                    self.source.shutdown()  
                    break
        else:
            for i, voltage in enumerate(minus_voltages_down):
                log.debug("Measuring voltage: %g mV" % voltage)

                self.source.source_voltage = voltage
                current = self.meter.current
                # Or use self.source.ramp_to_current(current, delay=0.1)
                sleep(self.delay * 1e-3)
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
                self.emit('progress', 100. * i / self.al_progress)
                # Or use self.source.ramp_to_current(current, delay=0.1)

                if voltage <= ((self.min_voltage * 1e-3) + (self.voltage_step * 1e-3)):
                    temp = self.voltage_dwell_time
                    while temp > -1:
                        self.source.source_voltage = self.min_voltage * 1e-3
                        voltage = self.source.source_voltage
                        current = self.meter.current
                        timer = '{0:f}'.format(temp)
                        print(timer, end="\r")
                        time.sleep(1)
                        temp_rest = self.voltage_dwell_time - temp
                        temp -=1

                        #sleep(self.delay * 1e-3)

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
                        self.emit('progress', 100. * (self.progress_ef_1 + temp_rest) / self.al_progress)

                        if self.should_stop():
                            self.source.shutdown()  
                            log.warning("Catch stop command in procedure")
                            break

                        if temp == -1:
                            for i, voltage in enumerate(minus_voltages_up):
                                self.source.source_voltage = voltage
                                current = self.meter.current
                                sleep(self.delay * 1e-3)
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
                                self.emit('progress', 100. * (self.progress_ef_1 + self.voltage_dwell_time + i) / self.al_progress)
                                if self.should_stop():
                                    self.source.shutdown()  
                                    log.warning("Catch stop command in procedure")
                                    break

                        else:
                            pass
                else:
                    pass

                if self.should_stop():
                    self.source.shutdown()  
                    log.warning("Catch stop command in procedure")
                    break



    def shutdown(self):
        self.source.shutdown()
        self.source.beep(frequency = 200, duration = 2)
        # self.source.enable_source()
        log.info("Finished")

    def get_estimates(self, sequence_length=None, sequence=None):
        
        duration_ef_1 = abs(self.max_voltage - self.min_voltage) / self.voltage_step * self.delay * 1e-3 * 2
        duration_ef_2 = self.voltage_dwell_time
        duration = duration_ef_1 + duration_ef_2
        
        

        estimates = [
            ("Duration", "%d s" % int(duration)),
            ("Sequence length", str(sequence_length)),
            ('Measurement finished at', str(datetime.now() + timedelta(seconds=duration))),
        ]

        return estimates




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
