import pyvisa
import time
import numpy as np
import datetime
import pickle
import threading  
from astropy.table import Table
#from tabulate import tabulate
from astropy.io import ascii
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import askdirectory
import os
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as py
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure


ResMan = pyvisa.ResourceManager()


from tkinter import *
Field = None
Current = None
duration = None

MaxField = None
Step = None
WaitingTime= None
BiasCurrent= None



#----------------------------------------Check Instrument-----------------------------

def popupmsg(msg):
    popup = Tk()
    popup.wm_title("!")
    label = Label(popup, text=msg)
    label.pack(side="top", fill="x", pady=10)
    B1 = Button(popup, text="Okay", command = popup.destroy)
    B1.pack()
    popup.mainloop()

try:
    Kepco = ResMan.open_resource("GPIB0::4::INSTR",read_termination="\n",write_termination="\n")
except visa.VisaIOError:
    popupmsg ("The KEPCO is OFF!")
    pass
    exit()
    
    
    
# from pymeasure.instruments.keithley import Keithley2400
# keithley = Keithley2400("GPIB::03")

# keithley.apply_current()                # Sets up to source current
# keithley.source_current_range = 10e-3   # Sets the source current range to 10 mA
# keithley.compliance_voltage = 1        # Sets the compliance voltage to 10 V
# keithley.source_current = 0.0             # Sets the source current to 0 mA
# keithley.enable_source()                # Enables the source output
# keithley.measure_voltage()              # Sets up to measure voltage  


#----------------Hall Loop animation---------------    

fig = py.figure(4)
ax = py.axes(xlim=(-5, 5), ylim=(-0.009, 0.01))
line, = ax.plot([], [], lw=2)
    
    
# def clearaxes(): 
#     global ax    
#     ax.clear()
#     line, = ax.plot([], [], lw=2)
#     ax = py.axes(xlim=(-5, 5), ylim=(-0.009, 0.01))


def initan():
    line.set_data([], [])
    return line,

def animate(i):
    ax.set_xlim(min(CurrentData), max(CurrentData))
    ax.set_ylim(min(HallVData), max(HallVData))
    line.set_data(CurrentData[:i], HallVData[:i])
    return line,

anim = animation.FuncAnimation(fig, animate, init_func=initan,interval=200, blit=False)   


# def cleargraph():
#     global ax
#     global fig
#     ax.clear()
#----------------------------------------------------------------------------------------------
  
#------------------------------------Keithley------------------------------------------- 
from pymeasure.instruments.keithley import Keithley2400
keithley = Keithley2400("GPIB0::24")

# keithley.read_termination = '\r'
# keithley.timeout=5000
# keithley.baud_rate = 57600
# Kepco.baud_rate = 57600

keithley.write("*RST")
keithley.write("*CLS")
#keithley.timeout=2000

keithley.wires = 4
keithley.apply_current()                # Sets up to source current
#keithley.source_current_range = 10e-3   # Sets the source current range to 10 mA
keithley.compliance_voltage = 5        # Sets the compliance voltage to 10 V
#keithley.source_current = 1e-4 



            # Sets the source current to 0 mA
keithley.write(":SENS:FUNC 'VOLT' ")
keithley.write(":OUTP ON")
keithley.enable_source()                # Enables the source output
keithley.measure_voltage()              # Sets up to measure voltage    
    
    
def KeithleyCurrent():
    global BiasCurrent
    
    bs= BiasCurrent.get()
    keithley.source_current = float(bs)

def BCurrentOff():
    keithley.source_current = 0
    
#------------------------------------Constant field script-----------------------------
def init():
    Kepco.write("*RST")
    Kepco.write("FUNC:MODE CURR")
    Kepco.write("VOLT 20.0")
    Kepco.write("OUTPUT ON; CURR 0.0")

def convert1():
    def convert():

        global Field
        global Current
        global duration
        global flag
    
        
        val = Field.get()
        val2= val * 1.0 #insert calibration here
        dur= int(duration.get())
        if val2 >= 29:
            popupmsg ("CURRENT TOO HIGH, DECREASE YOUR FIELD VALUE!!!")
            Kepco.write("CURR 0.0")
            time.sleep(0.05)
        else:
            for i in range(dur):
                if flag == True:
                      Kepco.write("CURR %s" %(val2))
                      time.sleep(1)
                      if flag == False:  
                           Kepco.write("CURR 0.0")
                           break
                else:
                    break
            Kepco.write("CURR 0.0")
        
    thread = threading.Thread(target=convert)  
    thread.start() 
 
 
def start():
    global flag
    flag = True
    convert1()  

def stop():
    global flag
    flag = False   
    
#---------------------------------Field ramp and file saving script----------------------------
CurrentData=[]
TimeData=[]
HallVData=[]



def sweep1():
    def sweep():
#
        global MaxField
        global Step
        global flagsweep
        global WaitingTime
        global NewFolder

        
        start=time.time()
    
        MF = MaxField.get()  #Convert field to current
        C= MF * 1.0 
        St= Step.get()
        S= St * 1.0
        W= WaitingTime.get()
        
#        CurrentData=[]
#        TimeData=[]

        steps1 = np.r_[0.0:C:S]
        steps2 = np.r_[C:-C:-S]
        steps3 = np.r_[-C:C+S/10:S]
        steps = list(steps1)+list(steps2)+list(steps3)	
        if C >= 29:
            popupmsg ("CURRENT TOO HIGH, DECREASE YOUR FIELD VALUE!!!")
            Kepco.write("CURR 0.0")
            time.sleep(0.05)
        else:
            for my_curr in steps:
                if flagsweep == True:
#                    print("CURR %f"%(my_curr))
                     Kepco.write("CURR %f"%(my_curr))
                     time.sleep(W)#0.4 for 5ms exposure time
                     CurrentData.append(float(Kepco.query("MEAS:CURR?")))
                     # CurrentData.append(my_curr)
                     # TimeData.append(time.time())
                     HallVData.append(float(keithley.voltage))
#                     TimeData.append(time.time()-start)
                     
                     if flagsweep == False:  
                       Kepco.write("CURR 0.0")
                       keithley.source_current = 0
                       break
                else:
                    break
                    Kepco.write("CURR 0.0")
                    keithley.source_current = 0
                 
        Kepco.write("CURR 0.0")
        keithley.source_current = 0
        np.savetxt(NewFolder+'/CurrentvsHallV.txt',np.c_[CurrentData,HallVData],fmt='%s')
        # np.savetxt(NewFolder+'/Current.txt', CurrentData)
        # np.savetxt(NewFolder+'/Time.txt', TimeData)
        # np.savetxt(NewFolder+'/HallV.txt', HallVData)
        CurrentData.clear()
#        TimeData.clear()
        HallVData.clear()
#        np.savetxt('C:\\Users\\Carolyna\\Documents\\Liza\\Data\\Current.txt', CurrentData)
#        np.savetxt('C:\\Users\\Carolyna\\Documents\\Liza\\Data\\Time.txt', TimeData)
#        
    thread = threading.Thread(target=sweep)  
    thread.start() 
 
# 
def startsweep():
    global flagsweep
    flagsweep = True
    sweep1()    
    

def stopsweep():
    global flagsweep
    flagsweep = False
                    
    
#---------------------------Save data with File name from GUI-----------------------------------------------
def ChooseDirectory():
    global Path

    win = Tk()
    win.withdraw()
    Path = askdirectory(initialdir=os.getcwd(),title='Please select a directory')
    


#FileName=None

def CreateFolder():
    global FileName
    global NewFolder
    global FN

    FN = FileName.get()

    NewFolder=Path +"/"+"%s" %(FN)
    os.mkdir(NewFolder)

#---------------------------Plot Loop in window script------------------------------------------------------   
#import matplotlib
#matplotlib.use('TkAgg')
##
##def plot():
##    import XMLDataExtraction3rdSept2019
##    FinalLoop = np.loadtxt(NewFolder+'FinalLoop.txt')
##    plt.plot(FinalLoop[:,0], FinalLoop[:,1])
##    plt.xlabel('Current (s)')
##    plt.ylabel('Grey Level (A)')
##    plt.show()
#    
#    
#
#
#
#
#
#
#def plot ():
#    x=np.array ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
#    v= np.array ([16,16.31925,17.6394,16.003,17.2861,17.3131,19.1259,18.9694,22.0003,22.81226])
#    p= np.array ([16.23697,     17.31653,     17.22094,     17.68631,     17.73641 ,    18.6368,
#        19.32125,     19.31756 ,    21.20247  ,   22.41444   ,  22.11718  ,   22.12453])
#
#    fig = Figure(figsize=(6,6))
#    a = fig.add_subplot(111)
#    a.scatter(v,x,color='red')
#    a.plot(p, range(2 +max(x)),color='blue')
#    a.invert_yaxis()
#
#    a.set_title ("Estimation Grid", fontsize=16)
#    a.set_ylabel("Y", fontsize=14)
#    a.set_xlabel("X", fontsize=14)
#        
        
        
        

#-------------------------------------Set up GUI---------------------------------------------
# Create the main window
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib import style  
    
    
root =Tk()
root.title("Magnetic field control -- GMW Magnet")

# Create the main container
frame = Frame(root)
#
## Lay out the main container, specify that we want it to grow with window size
frame.pack(fill=BOTH, expand=True)
#------------------------------------------------------


# Variables for holding Field and Current data
Field = DoubleVar()
Current = DoubleVar()
duration = DoubleVar()
FileName= StringVar()
MaxField = DoubleVar()
Step = DoubleVar()
WaitingTime = DoubleVar()
BiasCurrent= DoubleVar()
#


# Create widgets
#----------------------------------Sub Fields---------------------------------------
ConstantFieldFrame = LabelFrame(root, text="CONSTANT PERPENDICULAR FIELD")
ConstantFieldFrame.pack(side='top',fill="both", expand="yes")

#LoopPlotFrame = LabelFrame(root, text="CONVERTED HYSTERESIS LOOP")
#LoopPlotFrame.pack(side='left',fill="both", expand="yes")

SweepFieldFrame = LabelFrame(root, text="SWEEP PERPENDICULAR FIELD")
SweepFieldFrame.pack(side='left',fill="both", expand="yes")

# BothFieldFrame = LabelFrame(root, text="IN-PLANE AND PERPENDICULAR FIELD SIMULTANEOUSLY")
# BothFieldFrame.pack(side='top',fill="both", expand="yes")

# GraphFrame = LabelFrame(root, text="LIVE HALL EFFECT LOOP")
# GraphFrame.pack(side='right',fill="both", expand="yes")

TransportFrame = LabelFrame(root, text="TRANSPORT")
TransportFrame.pack(side='top',fill="both", expand="yes")
#-----------------------------------------------------------------------------------
# Lay out widgets
#-----------------------------TRANSPORT-------------------------

entry_BiasCurrent = Entry(TransportFrame, width=7, textvariable=BiasCurrent)
entry_BiasCurrent.grid(row=1, column=1, padx=5, pady=5)
label_BiasCurrent = Label(TransportFrame, text="Bias Current (A)")
label_BiasCurrent.grid(row=1, column=0, padx=5, pady=5, sticky=W)

button_ApplyCurrent = Button(TransportFrame, text="Apply Bias Current", bg='light green', command=KeithleyCurrent)
button_ApplyCurrent.grid(row=2, column=0, columnspan=1, padx=15, pady=15, sticky=E)

button_StopBC = Button(TransportFrame, text="STOP Bias Current", bg='red', command=BCurrentOff)
button_StopBC.grid(row=2, column=1, columnspan=2, padx=15, pady=15, sticky=E)


#-----------------------------CONSTANT PERPENDICULAR FIELD-------------------------
entry_field = Entry(ConstantFieldFrame, width=7, textvariable=Field)
entry_field.grid(row=1, column=1, padx=5, pady=5)
label_field = Label(ConstantFieldFrame, text="Magnetic Field (mT)")
label_field.grid(row=1, column=0, padx=5, pady=5, sticky=W)

entry_time = Entry(ConstantFieldFrame, width=7, textvariable=duration)
entry_time.grid(row=2, column=1, padx=5, pady=5)
label_time = Label(ConstantFieldFrame, text="Duration (s)")
label_time.grid(row=2, column=0, padx=5, pady=5, sticky=W)

button_ApplyField = Button(ConstantFieldFrame, text="Apply Field", bg='green', command=start)
button_ApplyField.grid(row=4, column=0, columnspan=1, padx=15, pady=15, sticky=E)

button_Stop = Button(ConstantFieldFrame, text="STOP", bg='red', command=stop)
button_Stop.grid(row=4, column=1, columnspan=2, padx=15, pady=15, sticky=E)

button_Initialisation = Button(frame, text="INITIALISATION", bg='orange',command=init)
button_Initialisation.grid(row=0, column=2, columnspan=1, padx=5, pady=5, sticky=E)

#----------------------------SWEEP PERPENDICULAR FIELD------------------------------
entry_FileName = Entry(SweepFieldFrame, width=25, textvariable=FileName)
entry_FileName.grid(row=1, column=1, padx=5, pady=5)
label_FileName = Label(SweepFieldFrame, text="New Folder Name")
label_FileName.grid(row=1, column=0, padx=5, pady=5, sticky=W)
button_SelectPath = Button(SweepFieldFrame, text="Select Directory", bg='orange', command=ChooseDirectory)
button_SelectPath.grid(row=1, column=2, columnspan=1, padx=5, pady=5, sticky=E)
button_CreateFolder = Button(SweepFieldFrame, text="Create New Folder", bg='green', command=CreateFolder)
button_CreateFolder.grid(row=1, column=3, columnspan=1, padx=5, pady=5, sticky=E)


entry_Maxfield = Entry(SweepFieldFrame, width=7, textvariable=MaxField)
entry_Maxfield.grid(row=2, column=1, padx=5, pady=5)
label_Maxfield = Label(SweepFieldFrame, text="Maximum Magnetic Field (mT)")
label_Maxfield.grid(row=2, column=0, padx=5, pady=5, sticky=W)


entry_Step = Entry(SweepFieldFrame, width=7, textvariable=Step)
entry_Step.grid(row=3, column=1, padx=5, pady=5)
label_Step = Label(SweepFieldFrame, text="Step (mT)")
label_Step.grid(row=3, column=0, padx=5, pady=5, sticky=W)

entry_Wait = Entry(SweepFieldFrame, width=7, textvariable=WaitingTime)
entry_Wait.grid(row=4, column=1, padx=5, pady=5)
label_Wait = Label(SweepFieldFrame, text="Waiting Time (s)")
label_Wait.grid(row=4, column=0, padx=5, pady=5, sticky=W)


button_SweepON = Button(SweepFieldFrame, text="Start Sweep", bg='green', command=startsweep)
button_SweepON.grid(row=5, column=0, columnspan=1, padx=15, pady=15, sticky=E)

button_SweepStop = Button(SweepFieldFrame, text="STOP", bg='red', command=stopsweep)
button_SweepStop.grid(row=5, column=1, columnspan=2, padx=15, pady=15, sticky=E)

# button_ClearGraph = Button(SweepFieldFrame, text="Clear Axes", bg='light blue', command=clearaxes)
# button_ClearGraph.grid(row=6, column=0, columnspan=1, padx=15, pady=15, sticky=E)

#----------------------------CONVERTED HYSTERESIS LOOP-------------------------------
#import matplotlib
#from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#from matplotlib.figure import Figure
#matplotlib.use('TkAgg')
#def plot():
#    import XMLDataExtraction3rdSept2019
#    from XMLDataExtraction3rdSept2019 import Pathdata
#    FinalLoop = np.loadtxt(Pathdata+'/FinalLoop.txt')
#    plt.plot(FinalLoop[:,0], FinalLoop[:,1])
#    plt.xlabel('Current (s)')
#    plt.ylabel('Grey Level (A)')
#    plt.show()
#    
#
#    fig = Figure(figsize=(7,7))
##        
#    a = fig.add_subplot(111)
##        a.scatter(v,x,color='red')
#    a.plot(FinalLoop[:,0], FinalLoop[:,1],'-o')
##        figure2=plt.plot(FieldValuePLot,GreyValuePlot,'-o')
##        a.plot(p, range(2 +max(x)),color='blue')
##        a.invert_yaxis()
#    
#
#    a.set_title ("Hysteresis loop converted from Kerr microscopy video", fontsize=16)
#    a.set_ylabel("Grey level", fontsize=14)
#    a.set_xlabel("Magnetic Field", fontsize=14)
#    canvas = FigureCanvasTkAgg(fig, master=root)
##        canvas = FigureCanvasTkAgg(figure2, master=self.root)
#    canvas.get_tk_widget().pack()
#    canvas.draw()
#
#    
#    root.mainloop()
    
    
    
#    
#----------------------------------------------------------------------------------------------------
#button_Plot = Button(SweepFieldFrame, text="Plot converted hysteresis loop", bg='cyan', command=plot)
#button_Plot.grid(row=6, column=0, columnspan=2, padx=15, pady=15, sticky=E)
#--------------------------------------------------------------------------------------------------







#
#from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#from matplotlib.figure import Figure
#
##GreyValuePlot = np.loadtxt('C:\\Users\\Carolyna\\Documents\\Liza\\Data\\GValues.txt')
##FieldValuePLot = np.loadtxt('C:\\Users\\Carolyna\\Documents\\Liza\\Data\\TValues.txt')
#
#class mclass:
##    GreyValuePlot = np.loadtxt('C:\\Users\\Carolyna\\Documents\\Liza\\Data\\GValues.txt')
##    FieldValuePLot = np.loadtxt('C:\\Users\\Carolyna\\Documents\\Liza\\Data\\TValues.txt')
#
#    def __init__(self,  root):
#        self.root = root
##        self.box = Entry(root)
#        self.button = Button (LoopPlotFrame, text="Plot", command=self.plot)
##       self.box.pack ()
#        self.button.pack()
#
#    def plot (self):
#        
##        x=np.array ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
##        v= np.array ([16,16.31925,17.6394,16.003,17.2861,17.3131,19.1259,18.9694,22.0003,22.81226])
##        p= np.array ([16.23697,     17.31653,     17.22094,     17.68631,     17.73641 ,    18.6368,
##            19.32125,     19.31756 ,    21.20247  ,   22.41444   ,  22.11718  ,   22.12453])
#
#        fig = Figure(figsize=(7,7))
##        
#        a = fig.add_subplot(111)
##        a.scatter(v,x,color='red')
#        a.plot(FieldValuePLot,GreyValuePlot,'-o')
##        figure2=plt.plot(FieldValuePLot,GreyValuePlot,'-o')
##        a.plot(p, range(2 +max(x)),color='blue')
##        a.invert_yaxis()
#        
#
#        a.set_title ("Hysteresis loop converted from Kerr microscopy video", fontsize=16)
#        a.set_ylabel("Grey level", fontsize=14)
#        a.set_xlabel("Magnetic Field", fontsize=14)
#        canvas = FigureCanvasTkAgg(fig, master=self.root)
##        canvas = FigureCanvasTkAgg(figure2, master=self.root)
#        canvas.get_tk_widget().pack()
#        canvas.draw()
#
#start= mclass (root)
#root.mainloop()
#-----------------------------------------------------------------------------------        

# Run forever! 
root.mainloop()





























