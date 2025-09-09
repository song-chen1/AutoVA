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

AutoVA_1.1.0, Features:
set one options for the process so that either E-field applicaiton or AHE measurement can be chosen

Two keithley and one kepcosource are used in this script:
1. keithley 2200: apply the E-field to the sample GPIB address: GPIB0::23::INSTR
2. keithley 2400: apply the bias current to the sample GPIB address: GPIB0::24::INSTR
3. kepcosource: apply the magnetic field to the sample GPIB address: GPIB0::4::INSTR

Anmerkung:
1. the keithley 2200 is uni-polar, so the voltage should be set to positive value

2. The AHE files are saved in the folder called AHE which is in the same folder as the IV files

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

from pymeasure.instruments.keithley import Keithley2200, Keithley2400, Keithley2450
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
    min_voltage = FloatParameter('Minimum Voltage', units='mV',default=0)
    voltage_step = FloatParameter('Voltage Step', units='mV', default=20)
    delay = FloatParameter('Delay Time', units='ms', default=100)
    current_range = FloatParameter('Compliance Current', units='uA', default=1.05)
    voltage_dwell_time = FloatParameter('Dwelling Time', units='s', default=30.0)
    interval = FloatParameter('Interval between E-field and AHE', units='s', default=8.0)

    AHE_field = FloatParameter('Maximum current sent to coil (A)', units='A', default=4.0)
    AHE_field_step = FloatParameter('Step (A)', units='A', default=0.1)
    AHE_waiting_time = FloatParameter('Waiting Time (s)', units='s', default=0.2)
    AHE_bias_current = FloatParameter('Bias Current (A)', units='A', default=400e-6)  

    DATA_COLUMNS = ['Voltage (V)', 'Current (A)', 'Resistance (ohm)', 'FieldCurrent (A)', 'Hall Voltage (V)']
    
  


    def startup(self):
        log.info("Setting up, Connecting and configuring instruments")
        
        """
        Configure the Keithley source for the E-field application
        """
        # self.IV_source = Keithley2400("GPIB1::24::INSTR")
        # self.IV_source.measure_current()
        # self.IV_source.current_range = self.current_range * 1e-6
        # self.IV_source.current_nplc = 1 # Integration constant to Medium

        # self.IV_source = Keithley2400("GPIB1::24::INSTR")
        # self.IV_source.apply_voltage()
        # #self.IV_source.source_voltage_range = self.max_voltage * 1e-3  # V
        # self.IV_source.source_voltage_range = 20   #source voltage
        # self.IV_source.compliance_current = self.current_range * 1e-6 # A
        # self.IV_source.enable_source()

        # self.IV_source = Keithley2400("GPIB0::24::INSTR")
        # self.IV_source.reset()
        # self.IV_source.write("*CLS")
        # self.IV_source.use_front_terminals()
        # self.IV_source.apply_voltage()
        # self.IV_source.source_voltage_range = 20
        # self.IV_source.compliance_current = self.current_range * 1e-6
        # self.IV_source.measure_current()
        # self.IV_source.enable_source()
        self.IV_source = Keithley2200("GPIB0::23::INSTR")
        self.IV_source.display_enabled = True
        self.IV_source.write("SOURCE:FUNC:MODE FIX")
        self.IV_source.current_limit = self.current_range * 1e-6
        self.IV_source.output_enabled = True
        
        log.info("Configuration for the E-field application finished")
        log.info("Setting up, Connecting and configuring instruments")

        # Initiate the KECPO source
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
        
       
        # Initiate the Keithley source for the AHE measurement
        self.ahe_source = Keithley2400("GPIB0::24::INSTR")
        self.ahe_source.reset()
        self.ahe_source.write("*CLS")
        self.ahe_source.wires = 4
        self.ahe_source.use_front_terminals()
        self.ahe_source.apply_current()
        self.ahe_source.compliance_voltage = 5  
        self.ahe_source.measure_voltage()
        self.ahe_source.enable_source()
        log.info("Configuration for the AHE measurement finished")

    def Efield_apply(self):
        
        self.IV_source.source_voltage = self.voltage
        
    def measure_voltage(self):
        self.mes_voltage = self.IV_source.voltage
        
    def measure_current(self):
        self.current = self.IV_source.current
        
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
    
    """
    Set the bias current for the AHE measurement
    """   
    def Bias_Current(self):
        self.ahe_source.source_current = self.AHE_bias_current

    """
    AHE transport sweep
    """
    def AHE_loop(self):
        CurrentData = []
        HallVData = []
        AHE_step1 = np.arange(0, self.AHE_field, self.AHE_field_step)
        AHE_step2 = np.arange(self.AHE_field, -self.AHE_field, -self.AHE_field_step)
        AHE_step3 = np.arange(-self.AHE_field, self.AHE_field + self.AHE_field_step, self.AHE_field_step)
        steps = np.concatenate((AHE_step1, AHE_step2, AHE_step3))
        # self.steps_ref = steps

        # define the elements for the progress bar
        voltages_up = np.arange(self.min_voltage, self.max_voltage, self.voltage_step)
        voltages_down = np.arange(self.max_voltage, self.min_voltage - self.voltage_step , -self.voltage_step)
        # to mV from V
        voltages_up *= 1e-3 
        voltages_down *= 1e-3
        # define the elements for the progress bar
        self.progress_ef_1 = len(voltages_up)
        self.progress_ef_2 = self.voltage_dwell_time
        self.progress_ef_3 = len(voltages_down)
        self.progress_ahe = len(steps)
        self.al_progress = self.progress_ef_1 + self.progress_ef_2 + self.progress_ef_3 + self.progress_ahe

            
        for i, fieldcurrent in enumerate(steps):
            self.kepcosource.write("CURR %f"%(fieldcurrent))
            real_fieldcurrent = float(self.kepcosource.query("MEAS:CURR?"))
            CurrentData.append(float(self.kepcosource.query("MEAS:CURR?")))
            HallVData.append(self.ahe_source.voltage)
            data = {
                'FieldCurrent (A)': real_fieldcurrent,
                'Hall Voltage (V)': self.ahe_source.voltage,
            }
            self.emit('results', data)
            self.emit('progress', 100. * (self.progress_ef_1 + self.voltage_dwell_time + self.progress_ef_3 + i) / self.al_progress)
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
                self.IV_source.shutdown()
                # self.kepcosource.write("MEM:UPDATE SHUTDOWN")
                break

        if self.max_voltage > 0:
            folder_name = f'{self.max_voltage / 1000}' + 'V_' + f'{self.voltage_dwell_time}' + 's'
            folder_path = directory + '\\AHE\\' + folder_name  
            # parent_path = os.path.abspath(os.path.join(directory, os.pardir)) + '\\AHE\\' + folder_name
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            else:
                count = 1
                while True:
                    new_folder_path = folder_path + '_' + str(count)
                    if not os.path.exists(new_folder_path):
                        os.makedirs(new_folder_path)
                        folder_path = new_folder_path
                        break
                    count += 1
            # voltages = np.concatenate((voltages_up, voltages_down))
            # steps = len(voltages) + int(self.voltage_dwell_time)
        else:
            folder_name = f'{self.min_voltage / 1000}' + 'V_' + f'{self.voltage_dwell_time}' + 's'
            folder_path = directory + '\\AHE\\' + folder_name
            # parent_path = os.path.abspath(os.path.join(directory, os.pardir)) + '\\AHE\\' + folder_name
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            else:
                count = 1
                while True:
                    new_folder_path = folder_path + '_' + str(count)
                    if not os.path.exists(new_folder_path):
                        os.makedirs(new_folder_path)
                        folder_path = new_folder_path
                        break
                    count += 1

        np.savetxt(folder_path+'\\CurrentvsHallV.txt',np.c_[CurrentData,HallVData],fmt='%s')

    def AHE_threading_process(self):
        thread_bias = Thread(target=self.Bias_Current())
        thread_ahe = Thread(target=self.AHE_loop())
       
        #start bothe threads
        thread_bias.start()
        thread_ahe.start()

        #wait for both threads to finish
        thread_bias.join()
        thread_ahe.join()


    def execute(self):
        """
        apply the E-field to the sample
        """
        # define the voltages arrary for the E-field application
        voltages_up = np.arange(self.min_voltage, self.max_voltage + self.voltage_step, self.voltage_step)
        voltages_down = np.arange(self.max_voltage, self.min_voltage - self.voltage_step , -self.voltage_step)
        minus_voltages_up = np.arange(self.min_voltage, self.max_voltage + self.voltage_step, self.voltage_step)
        minus_voltages_down = np.arange(self.max_voltage, self.min_voltage, -self.voltage_step)
        # to mV from V
        voltages_up *= 1e-3 
        voltages_down *= 1e-3
        minus_voltages_up *=1e-3
        minus_voltages_down *=1e-3

        AHE_step1 = np.arange(0, self.AHE_field, self.AHE_field_step)
        AHE_step2 = np.arange(self.AHE_field, -self.AHE_field, -self.AHE_field_step)
        AHE_step3 = np.arange(-self.AHE_field, self.AHE_field + self.AHE_field_step, self.AHE_field_step)
        steps = np.concatenate((AHE_step1, AHE_step2, AHE_step3))
        # define the elements for the progress bar
        self.progress_ef_1 = len(voltages_up)
        self.progress_ef_2 = self.voltage_dwell_time
        self.progress_ef_3 = len(voltages_down)
        self.progress_ahe = len(steps)
        self.al_progress = self.progress_ef_1 + self.progress_ef_2 + self.progress_ef_3 + self.progress_ahe
        temp = self.voltage_dwell_time
        log.info("Starting to sweep through voltage")
        
        if self.max_voltage > 0:
            # voltages = np.concatenate((voltages_up, voltages_down))
            # steps = len(voltages) + int(self.voltage_dwell_time)
            for i, voltage in enumerate(voltages_up):
                self.voltage = voltage
                log.debug("Measuring voltage: %g mV" % voltage)
                self.Efield_threading()
                sleep(self.delay * 1e-3)

                if abs(self.current) <= 1e-10:
                    resistance = np.nan
                else:
                    resistance = self.mes_voltage / self.current
                data = {
                    'Voltage (V)': self.mes_voltage,
                    'Current (A)': self.current,
                    'Resistance (ohm)': resistance
                }
                self.emit('results', data)
                self.emit('progress', 100. * i / self.al_progress)

                if voltage == (self.max_voltage * 1e-3) or voltage > (self.max_voltage - self.voltage_step) * 1e-3:
                    
                    while temp > -1:
                        self.PBias_threading()
                        timer = '{0:f}'.format(temp)
                        # print(timer, end="\r")
                        time.sleep(1)
                        temp_rest = self.voltage_dwell_time - temp
                        temp -=1
                        
                        #sleep(self.delay * 1e-3)
                        if abs(self.current) <= 1e-10:
                            resistance = np.nan
                        else:
                            resistance = self.mes_voltage / self.current
                        data = {
                            'Voltage (V)': self.mes_voltage,
                            'Current (A)': self.current,
                            'Resistance (ohm)': resistance
                        }

                        self.emit('results', data)
                        self.emit('progress', 100. * (self.progress_ef_1 + temp_rest) / self.al_progress)
                        if self.should_stop():
                            log.warning("Catch stop command in procedure")
                            self.IV_source.shutdown() 
                            self.IV_source.output_enabled = False
                            self.ahe_source.shutdown()
                            break

                        if temp == -1:
                            for i, voltage in enumerate(voltages_down):
                                self.voltage = voltage
                                self.Efield_threading()
                                sleep(self.delay * 1e-3)

                                if abs(self.current) <= 1e-10:
                                    resistance = np.nan
                                else:
                                    resistance = self.mes_voltage / self.current
                                data = {
                                    'Voltage (V)': self.mes_voltage,
                                    'Current (A)': self.current,
                                    'Resistance (ohm)': resistance
                                }
                                self.emit('results', data)
                                self.emit('progress', 100. * (self.progress_ef_1 + self.voltage_dwell_time + i) / self.al_progress)
                                if i == len(voltages_down) - 1:
                                    log.info("IV Measurement finished")
                                    self.IV_source.source_voltage = 0
                                    # self.IV_source.beep(frequency = 200, duration = 2)
                                    self.IV_source.shutdown() 
                                    self.IV_source.output_enabled = False
                                    log.info("E-field application finished, AHE Measurement start")                                

                                    sleep(self.interval)
                                    self.AHE_threading_process() 

                                if self.should_stop():
                                    log.warning("Catch stop command in procedure")
                                    self.IV_source.shutdown()
                                    self.IV_source.output_enabled = False
                                    self.ahe_source.shutdown()
                                    break
                        else:
                            pass
                else:
                    pass

                if self.should_stop():
                    log.warning("Catch stop command in procedure")
                    self.IV_source.shutdown()  
                    self.IV_source.output_enabled = False
                    self.ahe_source.shutdown()
                    break
        else:
            """
            Apply the negative E-field to the sample
            """
            for i, voltage in enumerate(minus_voltages_down):
                self.voltage = voltage
                self.Efield_threading()
                log.debug("Measuring voltage: %g mV" % voltage)
                sleep(self.delay * 1e-3)
                
                if abs(self.current) <= 1e-10:
                    resistance = np.nan
                else:
                    resistance = self.mes_voltage / self.current
                data = {
                    'Voltage (V)': self.mes_voltage,
                    'Current (A)': self.current,
                    'Resistance (ohm)': resistance
                }
                self.emit('results', data)
                self.emit('progress', 100. * i / self.al_progress)
                if voltage == (self.min_voltage * 1e-3) or voltage < (self.min_voltage + self.voltage_step) * 1e-3:
                    temp = self.voltage_dwell_time
                    while temp > -1:
                        self.NBias_threading()
                        # timer = '{0:f}'.format(temp)
                        # print(timer, end="\r")
                        time.sleep(1)
                        temp_rest = self.voltage_dwell_time - temp
                        temp -=1
                        
                        #sleep(self.delay * 1e-3)
                        if abs(self.current) <= 1e-10:
                            resistance = np.nan
                        else:
                            resistance = self.mes_voltage / self.current
                        data = {
                            'Voltage (V)': self.mes_voltage,
                            'Current (A)': self.current,
                            'Resistance (ohm)': resistance
                        }

                        self.emit('results', data)
                        self.emit('progress', 100. * (self.progress_ef_1 + temp_rest) / self.al_progress)
                        if self.should_stop():
                            log.warning("Catch stop command in procedure")
                            self.IV_source.shutdown() 
                            self.IV_source.output_enabled = False
                            self.ahe_source.shutdown()
                            break

                        if temp == -1:
                            for i, voltage in enumerate(minus_voltages_up):
                                self.voltage = voltage
                                self.Efield_threading()
                                sleep(self.delay * 1e-3)

                                if abs(self.current) <= 1e-10:
                                    resistance = np.nan
                                else:
                                    resistance = self.mes_voltage / self.current
                                data = {
                                    'Voltage (V)': self.mes_voltage,
                                    'Current (A)': self.current,
                                    'Resistance (ohm)': resistance
                                }
                                self.emit('results', data)
                                self.emit('progress', 100. * (self.progress_ef_1 + self.voltage_dwell_time + i) / self.al_progress)
                                if i == len(voltages_down) - 1:
                                    log.info("IV Measurement finished")
                                    self.IV_source.source_voltage = 0
                                    # self.IV_source.beep(frequency = 200, duration = 2)
                                    self.IV_source.shutdown() 
                                    self.IV_source.output_enabled = False
                                    log.info("E-field application finished, AHE Measurement start")                                

                                    sleep(self.interval)
                                    self.AHE_threading_process() 

                                if self.should_stop():
                                    log.warning("Catch stop command in procedure")
                                    self.IV_source.shutdown()
                                    self.IV_source.output_enabled = False
                                    self.ahe_source.shutdown()
                                    break

                        else:
                            pass
                else:
                    pass

                if self.should_stop():
                    log.warning("Catch stop command in procedure")
                    self.IV_source.shutdown()  
                    self.ahe_source.shutdown()
                    break


    def shutdown(self):
        self.IV_source.shutdown()  
        self.ahe_source.shutdown()
        
        
        # self.IV_source.beep(frequency = 200, duration = 2)
        # self.kepcosource.write("MEM:UPDATE SHUTDOWN")
        
        log.info("Finished")

    def get_estimates(self, sequence_length, sequence):
        
        duration_ef_1 = abs(self.max_voltage - self.min_voltage) / self.voltage_step * self.delay * 1e-3 * 2
        duration_ef_2 = self.voltage_dwell_time
        duration_interval = self.interval
        duration_ahe = abs(self.AHE_field) / self.AHE_field_step * self.AHE_waiting_time * 5
        duration = duration_ef_1 + duration_ef_2 + duration_ahe + duration_interval
        
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
                'max_voltage','voltage_dwell_time', 'min_voltage', 'voltage_step',
                'delay', 'current_range', 'interval', 'AHE_field', 'AHE_field_step', 'AHE_waiting_time', 'AHE_bias_current'
            ],
            displays=[
                'max_voltage', 'voltage_dwell_time', 'min_voltage', 'voltage_step', 
                'delay', 'current_range', 'interval', 'AHE_field', 'AHE_field_step', 'AHE_waiting_time', 'AHE_bias_current'
            ],
            x_axis=['Voltage (V)', 'FieldCurrent (A)'],
            y_axis=['Current (A)', 'Hall Voltage (V)'],
            directory_input = True,
            sequencer=True,
            sequencer_inputs=['devices', 'max_voltage','voltage_dwell_time', 'min_voltage', 'voltage_step',
            'delay', 'current_range', 'AHE_field', 'AHE_field_step', 'AHE_waiting_time', 'AHE_bias_current'],
            inputs_in_scrollarea = True,
        )
        self.setWindowTitle('AutoVA')
        
       
    def queue(self, procedure=None):
        if procedure is None:
            procedure = self.make_procedure()
        global directory
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
        
        # max_voltage = procedure.max_voltage
        # voltage_dwell_time = procedure.voltage_dwell_time
        # min_voltage = procedure.min_voltage
        # max_voltage = procedure.max_voltage
        
        # if max_voltage > 0:
        #     folder_name = f'{max_voltage / 1000}' + 'V_' + f'{voltage_dwell_time}' + 's'   
        #     parent_path = os.path.abspath(os.path.join(directory, os.pardir)) + '\\AHE\\' + folder_name
        #     if not os.path.exists(parent_path):
        #         os.makedirs(parent_path)
        #     else:
        #         count = 1
        #         while True:
        #             new_parent_path = parent_path + '_' + str(count)
        #             if not os.path.exists(new_parent_path):
        #                 os.makedirs(new_parent_path)
        #                 parent_path = new_parent_path
        #                 break
        #             count += 1
            
        #     # if procedure.shutdown.has_been_called:
                
        #     #     CurrentData = procedure.CurrentData
        #     #     HallVData = procedure.HallVData
        #     #     np.savetxt(parent_path+'\\CurrentvsHallV.txt',np.c_[CurrentData,HallVData],fmt='%s')
        # else:
        #     folder_name = f'{min_voltage / 1000}' + 'V_' + f'{voltage_dwell_time}' + 's'
        #     parent_path = os.path.abspath(os.path.join(directory, os.pardir)) + '\\AHE\\' + folder_name
        #     if not os.path.exists(parent_path):
        #         os.makedirs(parent_path)
        #     else:
        #         count = 1
        #         while True:
        #             new_parent_path = parent_path + '_' + str(count)
        #             if not os.path.exists(new_parent_path):
        #                 os.makedirs(new_parent_path)
        #                 parent_path = new_parent_path
        #                 break
        #             count += 1
       
        
        
                
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())