# telemetry
Telemetry protocol with spec, transmit-side library, and visualization client.

## Introduction
The telemetry library is designed to provide a simple and efficient way to get data off an embedded platform and both visualized and logged on a PC. The intended use case is streaming data from an embedded system to a PC through an UART interface with either a Bluetooth or UART bridge. Since data definitions are transmitted, users only need to alter code on the transmitting side, eliminating the need to keep both transmitter and visualizer definitions in sync.

The server-side (transmitter) code is written in C++ and designed with embedded constraints in mind (no dynamic memory allocation is done). Templated classes allow most native data types and a hardware abstraction layer allows multiple platforms (currently Arduino and mBed).

The client-side (plotter / visualizer) code is written in Python. A basic telemetry protocol parser is provided that separates and interprets telemetry packets and other data from the received stream. A matplotlib-based GUI is also provided on top of the parser that visualizes numeric data as a line plot and array-numeric data as a waterfall / spectrogram style plot.

The [protocol spec](../master/docs/protocol.tex) defines a binary wire format along with packet structures for data and headers, allowing for other implementations of either side that interoperate.

## Changelog
### From Version 0.0 (Spring 2015)
- Platform automatically detected by just including `telemetry.h`, no need to manually specify `telemetry-arduino.h` or `telemetry-mbed.h`.

### From Version 1.0 (Spring 2016)
- Added client support for using RPC on the embedded side.  Client code now has a command-prompt style interface, that filters out printfs from the telemetry stream cleanly.  Command-prompt also allows user to type commands, and then send later to the embedded side.
- For use with the mbed RPC library. (https://developer.mbed.org/cookbook/Interfacing-Using-RPC)

### From Version 2.0 (Spring 2018)
- Rewrote server side telemetry library in C for use with the K64F SDK in MCUXpresso

## Quickstart
### 1. Plotter setup
Telemetry depends on these:
- Python (ideally 2.7.  The graphing features were designed for 3.4 or later, but the serial console is 2.7 only)
- numpy 1.9.2 or later
- matplotlib 1.4.3 or later
- PySerial

#### On Windows
For Windows platforms, [Python](https://www.python.org/downloads/), [numpy](http://sourceforge.net/projects/numpy/files/NumPy/), [matplotlib](http://matplotlib.org/downloads.html) and [curses] (https://github.com/jmcb/python-pdcurses/blob/master/INSTALL.rst) (make sure to choose the correct version of python) must be downloaded & installed.

Currently only python 2.7 is compatable with the serial terminal.

Other software can be installed through pip, Python's package manager. pip is located in your Python/Scripts folder, and the installation commands for the necessary packages are:

`pip install pyserial`

`pip install six python-dateutil pyparsing`

`pip install future`

#### On Linux & Mac OS
For Linux & Mac platforms, the required software should be available from the OS package manager

On Debian-based platforms, including Ubuntu (This works on mac too!) the installation commands for the necessary packages are:

`sudo pip install future --upgrade`

`sudo pip install matplotlib`

### 2. Server setup
The server side c code is located in "server-c/telemetry". Copy the folder "telemetry" into the source folder of your project. Then add the following two lines into your main.c file to include the telemetry server code:

`#include "telemetry/telemetry_uart.h"`

`#include "telemetry/telemetry.h"'`


### 3. Plotter GUI Usage
The plotter is located in `telemetry/client-py/plotter.py` and can be directly executed using Python. The arguments can be obtained by running it with `--help`:
- Serial port: like COM1 for Windows or /dev/ttyUSB0 or /dev/ttyACM0 for Linux.
- Baud rate: optional, defaults to 38,400.
- Independent variable name: defaults to `time`.
- Independent variable span: defaults to 10,000 (or 10 seconds, if your units are in milliseconds).

The plotter must be running when the header is transmitted, otherwise it will fail to decode the data packets (and notify you of such). The plotter will automatically reinitialize upon receiving a new header, so you should reset the MCU after you open the plotter.

This simple plotter graphs all the data against a selected independent variable (like time). Numeric data is plotted as a line graph and array-numeric data is plotted as a waterfall / spectrograph-style graph. Regular UART data (like from `printf`s) will be routed to the console. All received data, including from `printf`s, is logged to a CSV. A new CSV is created each time a new header packet is received, with a timestamped filename. This can be disabled by giving an empty filename prefix.

You can double-click a plot to inspect its latest value numerically and optionally remotely set it to a new value. You can also send non-telemetry data by typing in the console (should have a `>>> ` prompt); note that data is buffered (not sent) until you hit enter. A newline (`\n\r`) is included at the end of whatever you type.  The command prompt also echos back any command that is sent to the embedded side.

If you feel really adventurous, you can also try to mess with the code to plot things in different styles. For example, the plot instantiation function from a received header packet is in `subplots_from_header`. The default just creates a line plot for numeric data and a waterfall plot for array-numeric data. You can make it do fancier things, like overlay a numerical detected track position on the raw camera waterfall plot.

### 4. Server Usage
To use the telemetry system you need only add a few lines of code to your existing project. See [this link](https://github.com/ucb-ee192/SkeletonMCUX/tree/master/frdmk64f_telemetry) for an example of a working MCUXpresso Project for FRDMK64F that showcases printing telemetry data.

1. First you must initialize the uart. This is done by calling the function:

`init_uart();`

The settings for the uart are in "telemetry/telemetry_uart.c". You can change these here if needed

2. You must register all variables you want to track with the telemetry system. Make sure these variables are either global or you have malloc'ed memory for them:
```
\\Global or Malloc'ed Variables
uint32_t time;
float motor_pwm;
uint32_t camera[128];

register_telemetry_variable("uint", "time", "Time", "ms", (uint32_t*) &time,  1, 0,  0.0);
register_telemetry_variable("float", "motor", "Motor PWM", "Percent DC", (uint32_t*) &motor_pwm,  1, 0.0f,  0.5f);
register_telemetry_variable("uint", "linescan", "Linescan", "ADC", (uint32_t*) &camera,  128, 0.0f,  0.0f);
```

The function signature and arguments for register_telemetry_variable are:
```
void register_telemetry_variable(char* data_type, char* internal_name, char* display_name, char* units, uint32_t* value_pointer, uint32_t num_elements, float lower_bound, float upper_bound)

  /* data_type = "uint", "int", or "float"
  * internal_name = internal reference name used for the python plotter (must have one variable with internal_name ='time')
  * display_name = string used to label the axis on the plot
  * units = string used to denote the units of the dependent variable
  * value_pointer = pointer to the variable you want to track. Make sure the variable is global or that you malloc space for it
  * num_elements = number of elements to track here (i.e. 1=just 1 number, 128=array of 128 elements)
  * lower_bound = float representing a lower bound on the data (used for setting plot bounds)
  * upper_bound = float representing an upper bound on the data (used for setting plot bounds)
  */
```

IMPORTANT: 

Currently you can only track 32 bit values (int32, uint32_t, float).
You MUST include a variable whose "internal_name"=time for the plotter to work. This will be used as the independent axis (x axis) for the plotter.

3. Once you have initialized the UART, and registered your telemetry variables you must transmit the header. This tells the plotter what variables you will be plotting, their size, names, units, etc. This can be done by:
```
transmit_header();

```
4. Now you are ready to send telemetry data using "do_io". Your main loop might look something like the following.
```
    while (1)
    {
      time = get_curr_time_ms();
      take_pic();
        
      //Do other stuff here
        
      do_io(); //Send a telemetry packet with the values of all the variables.
    }    
```
IMPORTANT:

do_io currently blocks the CPU as it writes bytes. Be careful if plotting many variables or calling do_io very often this may mess with other critical parts of your software timing.




### Protips
Bandwidth limits: the amount of data you can send is limited by your microcontroller's UART rate, the UART-PC interface (like Bluetooth-UART or a USB-UART adapter), and transmission overhead (for example, at high baud rates, the overhead from mbed's putc takes longer than the physical transmission of the character). If you're constantly getting receive errors, try:
- Reducing precision. A 8-bit integer is smaller than a 32-bit integer. If all you're doing is plotting, the difference may be visually imperceptible. (Currently telemetry system only supports 32 bit values- can be easily modified in the future to work with smaller ones).
- Decimating samples. Sending every nth sample will reduce the data rate by n. Again, the difference may be imperceptible if plotting, but you may also lose important high frequency components. Use with caution.

## Known Issues
### Transmitter Library
- No header resend request, so the plotter GUI must be started before the transmitter starts.
- No DMA support.
- No CRC or FEC support.
- printf's being called during do_io really messes things up.

### Plotter GUI
- Waterfall / spectrogram style plotting is CPU intensive and inefficient.

### server-c
- Data can only be sent from server to client (can easily be fixed by adding input buffer and related logic to do_io())
- Does not seem to work with more than 4 variables. Plotter says "packet dropped" (potentially fixed?)
- only works with 32 bit data types currently (float, int32, uint32_t)

### server-cpp
- mbed HAL: Serial putc is highly inefficient for bulk data.

## Copyright
*Contents are licensed under the BSD 3-clause ("BSD simplified", "BSD new") license, the terms of which are reproduced below.*

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

