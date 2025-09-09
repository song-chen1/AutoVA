# AutoVA

## GUI introduction <a name="introduction"></a>

![](https://blog.songchen.science/en/AutoVA-Automated-VCMA-AHE-Measurement-System/1.png)

### Block 1: <a name="block1"></a>

- Maximum Voltage (mV): This setting determines the strength of positive electric fields. Use a positive value when you want positive electric fields, and set it to 0 if you prefer negative fields.
- Dwelling Time (s): This is the duration for which the targeting electric fields will be applied and held.
- Minimum Voltage (mV): This setting controls the intensity of negative electric fields. Set a negative value when you want negative electric fields and 0 when you want positive fields.
- Voltage Step (mV): This is the increment used when ramping up the voltage to reach the target electric field strength.
- Delay Time (ms): This delay time is used during the voltage step when ramping up to the target electric field strength.
- Compliance Current (uA): This current is applied to protect the sample from high leakage currents.
- Maximum Current Sent to Coil (A): This current is sent to the coil to create looping electromagnetic (EM) fields for generating hysteresis loops.
- Step (A): This is the current increment used during the looping of EM fields.
- Directory: Specify the path where you want to save the data.

### Block 2: <a name="block2"></a>

The sequencer is provided which allows users to queue a series of measurements with varying one, or more, of the parameters. This sequencer thereby provides a convient way to scan through the parameter space of the measurement procedure.

The sequences can be extended and shortened using the buttons `Add root item`, `Add item`, and `Remove item`. The latter two either add an item as a child of the currently selected item or remove the selected item, respectively. To queue the entered sequence the button `Queue` sequence can be used. If an error occurs in evaluating the sequence text-boxes, this is mentioned in the logger, and nothing is queued.

```
-"Maximum Voltage", "[0]"
-- "Minimum Voltage", "[-1000]"
--- "Dwelling Time", "[540]"
-- "Minimum Voltage", "arange(-2000, -4500, -500)"
--- "Dwelling Time", "[60, 180, 300]"
```

Finally, it is possible to create a sequence file such that the user  does not need to write the sequence again each time. The sequence file  can be created by saving current sequence built within the GUI using the `Save sequence` button or directly writing a simple text file. Once created, the sequence can be loaded with the `Load sequence` button.

### Block 3: <a name="block3"></a>

Graphical Display: 

- live plotting for data
  - Dock1: IV curve when E-fields are applied
  - Dock 2: Coil currents (EM after calibration) looped as a function of the Hall Voltage measured
- Experiments log

### Block 4: <a name="block4"></a>

A queue system for managing large numbers of experiments

## Experiment Running & Data Example<a name="example"></a>

### Experiment Running Example <a name="experiment"></a>

One experiment running example is shown as followings:

1. Parameters input:

![](https://blog.songchen.science/en/AutoVA-Automated-VCMA-AHE-Measurement-System/2.png)

![Screenshot 2023-09-19 171546](/Volumes/song_SI/Screenshot 2023-09-19 171546.png)

![](https://blog.songchen.science/en/AutoVA-Automated-VCMA-AHE-Measurement-System/3.png)

2. Applying the E-field:

   ![](https://blog.songchen.science/en/AutoVA-Automated-VCMA-AHE-Measurement-System/4.png)

3. Looping the electromagnetic fields and receive the Hall voltages:

   ![](https://blog.songchen.science/en/AutoVA-Automated-VCMA-AHE-Measurement-System/5.png)

4. Applying another E-field and EM looping:

   ![](https://blog.songchen.science/en/AutoVA-Automated-VCMA-AHE-Measurement-System/6.png)

5. Making the sequencer (Automated Measurement):

   ![](https://blog.songchen.science/en/AutoVA-Automated-VCMA-AHE-Measurement-System/7.png)

   ### Dataset Example <a name="data"></a>

   <mark>Two files will be generated: 1. the file containing all the data sets and one separate file containing the AHE data</mark>

   ![](https://blog.songchen.science/en/AutoVA-Automated-VCMA-AHE-Measurement-System/8.png)

   ![](https://blog.songchen.science/en/AutoVA-Automated-VCMA-AHE-Measurement-System/9.png)

   