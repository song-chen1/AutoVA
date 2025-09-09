import unittest
from unittest.mock import MagicMock
from AutoVA import IVProcedure

class TestIVProcedure(unittest.TestCase):
    def setUp(self):
        self.procedure = IVProcedure()

    def test_startup(self):
        self.procedure.IV_source = MagicMock()
        self.procedure.kepcosource = MagicMock()
        self.procedure.ahe_source = MagicMock()

        self.procedure.startup()

        self.procedure.IV_source.reset.assert_called_once()
        self.procedure.IV_source.write.assert_called_with("*CLS")
        self.procedure.IV_source.use_front_terminals.assert_called_once()
        self.procedure.IV_source.apply_voltage.assert_called_once()
        self.procedure.IV_source.source_voltage_range = 20
        self.procedure.IV_source.compliance_current = self.procedure.current_range * 1e-6
        self.procedure.IV_source.measure_current.assert_called_once()
        self.procedure.IV_source.enable_source.assert_called_once()

        self.procedure.kepcosource.write.assert_called_with("*RST")
        self.procedure.kepcosource.write.assert_called_with("FUNC:MODE CURR")
        self.procedure.kepcosource.write.assert_called_with("VOLT 20.0")
        self.procedure.kepcosource.write.assert_called_with("OUTPUT ON; CURR 0.0")

        self.procedure.ahe_source.reset.assert_called_once()
        self.procedure.ahe_source.write.assert_called_with("*CLS")
        self.procedure.ahe_source.wires = 4
        self.procedure.ahe_source.use_front_terminals.assert_called_once()
        self.procedure.ahe_source.apply_current.assert_called_once()
        self.procedure.ahe_source.compliance_voltage = 5
        self.procedure.ahe_source.measure_voltage.assert_called_once()
        self.procedure.ahe_source.enable_source.assert_called_once()

    def test_Bias_Current(self):
        self.procedure.ahe_source = MagicMock()

        self.procedure.Bias_Current()

        self.procedure.ahe_source.source_current = self.procedure.AHE_bias_current

    def test_AHE_loop(self):
        self.procedure.kepcosource = MagicMock()
        self.procedure.kepcosource.query.side_effect = [0.1, 0.2, 0.3]
        self.procedure.ahe_source = MagicMock()
        self.procedure.ahe_source.voltage = 1.0
        self.procedure.progress_ahe = 3
        self.procedure.al_progress = 3

        self.procedure.AHE_loop()

        self.assertEqual(self.procedure.kepcosource.write.call_count, 3)
        self.assertEqual(self.procedure.kepcosource.query.call_count, 3)
        self.assertEqual(self.procedure.CurrentData, [0.1, 0.2, 0.3])
        self.assertEqual(self.procedure.HallVData, [1.0, 1.0, 1.0])
        self.assertEqual(self.procedure.emit.call_count, 3)
        self.assertEqual(self.procedure.emit.call_args_list[0][0][0], 'results')
        self.assertEqual(self.procedure.emit.call_args_list[0][0][1]['FieldCurrent (A)'], 0.1)
        self.assertEqual(self.procedure.emit.call_args_list[0][0][1]['Hall Voltage (V)'], 1.0)
        self.assertEqual(self.procedure.emit.call_args_list[1][0][0], 'results')
        self.assertEqual(self.procedure.emit.call_args_list[1][0][1]['FieldCurrent (A)'], 0.2)
        self.assertEqual(self.procedure.emit.call_args_list[1][0][1]['Hall Voltage (V)'], 1.0)
        self.assertEqual(self.procedure.emit.call_args_list[2][0][0], 'results')
        self.assertEqual(self.procedure.emit.call_args_list[2][0][1]['FieldCurrent (A)'], 0.3)
        self.assertEqual(self.procedure.emit.call_args_list[2][0][1]['Hall Voltage (V)'], 1.0)
        self.assertEqual(self.procedure.emit.call_count, 3)
        self.assertEqual(self.procedure.emit.call_args_list[0][0][0], 'results')
        self.assertEqual(self.procedure.emit.call_args_list[0][0][1]['FieldCurrent (A)'], 0.1)
        self.assertEqual(self.procedure.emit.call_args_list[0][0][1]['Hall Voltage (V)'], 1.0)
        self.assertEqual(self.procedure.emit.call_args_list[1][0][0], 'results')
        self.assertEqual(self.procedure.emit.call_args_list[1][0][1]['FieldCurrent (A)'], 0.2)
        self.assertEqual(self.procedure.emit.call_args_list[1][0][1]['Hall Voltage (V)'], 1.0)
        self.assertEqual(self.procedure.emit.call_args_list[2][0][0], 'results')
        self.assertEqual(self.procedure.emit.call_args_list[2][0][1]['FieldCurrent (A)'], 0.3)
        self.assertEqual(self.procedure.emit.call_args_list[2][0][1]['Hall Voltage (V)'], 1.0)
        self.assertEqual(self.procedure.kepcosource.write.call_count, 3)
        self.assertEqual(self.procedure.kepcosource.write.call_args_list[0][0][0], "CURR 0.0")
        self.assertEqual(self.procedure.kepcosource.write.call_args_list[1][0][0], "CURR 0.0")
        self.assertEqual(self.procedure.kepcosource.write.call_args_list[2][0][0], "CURR 0.0")
        self.assertEqual(self.procedure.ahe_source.source_current, 0)
        self.assertEqual(self.procedure.ahe_source.beep.call_count, 1)
        self.assertEqual(self.procedure.kepcosource.write.call_args_list[0][0][0], "SYSTem:BEEP")

    def test_AHE_threading_process(self):
        self.procedure.Bias_Current = MagicMock()
        self.procedure.AHE_loop = MagicMock()

        self.procedure.AHE_threading_process()

        self.procedure.Bias_Current.assert_called_once()
        self.procedure.AHE_loop.assert_called_once()

    def test_E_field_application(self):
        self.procedure.IV_source = MagicMock()
        self.procedure.min_voltage = -2000
        self.procedure.max_voltage = 2000
        self.procedure.voltage_step = 20
        self.procedure.voltage_dwell_time = 30.0

        self.procedure.E_field_application()

        self.assertEqual(self.procedure.IV_source.source_voltage, -2.0)
        self.assertEqual(self.procedure.IV_source.source_voltage, -1.98)
        self.assertEqual(self.procedure.IV_source.source_voltage, -1.96)
        # ...

    def test_execute(self):
        self.procedure.IV_source = MagicMock()
        self.procedure.min_voltage = -2000
        self.procedure.max_voltage = 2000
        self.procedure.voltage_step = 20
        self.procedure.delay = 100
        self.procedure.current_range = 1.05
        self.procedure.voltage_dwell_time = 30.0
        self.procedure.al_progress = 100

        self.procedure.execute()

        self.assertEqual(self.procedure.IV_source.source_voltage, -2.0)
        self.assertEqual(self.procedure.IV_source.current, 0.0)
        self.assertEqual(self.procedure.IV_source.source_voltage, -1.98)
        self.assertEqual(self.procedure.IV_source.current, 0.0)
        self.assertEqual(self.procedure.IV_source.source_voltage, -1.96)
        # ...
        self.assertEqual(self.procedure.emit.call_count, 100)
        self.assertEqual(self.procedure.emit.call_args_list[0][0][0], 'results')
        self.assertEqual(self.procedure.emit.call_args_list[0][0][1]['Voltage (V)'], -2.0)
        self.assertEqual(self.procedure.emit.call_args_list[0][0][1]['Current (A)'], 0.0)
        self.assertEqual(self.procedure.emit.call_args_list[0][0][1]['Resistance (ohm)'], float('nan'))
        self.assertEqual(self.procedure.emit.call_args_list[1][0][0], 'results')
        self.assertEqual(self.procedure.emit.call_args_list[1][0][1]['Voltage (V)'], -1.98)
        self.assertEqual(self.procedure.emit.call_args_list[1][0][1]['Current (A)'], 0.0)
        self.assertEqual(self.procedure.emit.call_args_list[1][0][1]['Resistance (ohm)'], float('nan'))
        # ...

if __name__ == '__main__':
    unittest.main()