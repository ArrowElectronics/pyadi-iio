import iio
import time

import adi
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

## TX DAC Output Mode Selector
#  Select internal data sources. Supported values are:
#  - 0 (0x00): internal tone (DDS)
#  - 1 (0x01): pattern (SED)
#  - 2 (0x02): input data (DMA Buffer)
#  - 3 (0x03): 0x00
#  - 6 (0x06): pn7 (standard O.150)
#  - 7 (0x07): pn15 (standard O.150)
#  - 10 (0x0A): Nibble ramp (Device specific e.g. adrv9001)
#  - 11 (0x0B): 16 bit ramp (Device specific e.g. adrv9001)
##
TX_DAC_MODE = 0

# TX DAC Mode Select Register
DAC_MODE_REGISTER = 0x0418

uri="ip:10.126.203.87"
ctx = iio.Context(uri)
dac = ctx.find_device("axi-adrv9002-tx-lpc") # DAC Core in HDL for DMA

def gen_tone(fc, fs, N):
    fc = int(fc / (fs / N)) * (fs / N)
    ts = 1 / float(fs)
    t = np.arange(0, N * ts, ts)
    i = np.cos(2 * np.pi * t * fc) * 2 ** 14
    q = np.sin(2 * np.pi * t * fc) * 2 ** 14
    return i + 1j * q

# Configure ADRV9002 parameters
sdr = adi.adrv9002(uri)
sdr.digital_gain_control_mode_chan0 = "Gain_Compensation_manual_control"
sdr.digital_gain_control_mode_chan1 = "Gain_Compensation_manual_control"
sdr.interface_gain_chan0 = "-24dB"
sdr.interface_gain_chan1 = "-24dB"
sdr.rx_ensm_mode_chan0 = "rf_enabled"
sdr.rx_ensm_mode_chan1 = "rf_enabled"
sdr.tx_ensm_mode_chan0 = "rf_enabled"
sdr.tx_ensm_mode_chan1 = "rf_enabled"
sdr.rx0_lo = 2400000000
sdr.rx1_lo = 2400000000
sdr.tx0_lo = 2400000000
sdr.tx1_lo = 2400000000
sdr.tx_hardwaregain_chan0 = -34
sdr.tx_hardwaregain_chan1 = -34
sdr.rx_hardwaregain_chan0 = -24
sdr.rx_hardwaregain_chan1 = -24
sdr.tx_cyclic_buffer = True

fs = int(sdr.rx0_sample_rate)

# Enable digital loopback
# sdr._ctrl.debug_attrs['tx0_ssi_test_mode_loopback_en'].value = '1'

dac.reg_write(DAC_MODE_REGISTER, TX_DAC_MODE)
reg_val = dac.reg_read(DAC_MODE_REGISTER)
print(reg_val)

if (TX_DAC_MODE == 0):
    # Set single DDS tone for TX on one transmitter
    sdr.dds_single_tone(-10e3, 0.5, channel=0)
elif (TX_DAC_MODE == 2):
    # Create a sinewave waveform
    N = 1024
    iq1 = gen_tone(-60e3, fs, N)
    iq2 = gen_tone(100e3, fs, N)

    # Send data
    sdr.tx([iq1, iq2])

sdr.rx_buffer_size = 2 ** 18

# Collect data from both channels
(rx1, rx2) = sdr.rx()
f, Pxx_den = signal.periodogram(rx1, fs, return_onesided=False)
plt.clf()
# Plot RX1 time data samples
print("Plotting graphs...")
plt.subplot(3, 1, 1)
plt.xlabel("(voltage0 i) Time Samples")
plt.ylabel("Amplitude")
plt.plot(rx1.real);
plt.subplot(3, 1, 2)
plt.xlabel("(voltage0 q) Time Samples")
plt.ylabel("Amplitude")
plt.plot(rx1.imag);
# Plot FFT data
plt.subplot(3, 1, 3)
plt.semilogy(f, Pxx_den)
# plt.ylim([1e-9, 1e2])
plt.xlabel("Frequency [Hz]")
plt.ylabel("PSD [V**2/Hz]")
plt.show()
plt.pause(0.05)
time.sleep(0.1)

# Disable digital loopback if enabled
sdr._ctrl.debug_attrs['tx0_ssi_test_mode_loopback_en'].value = '0'
