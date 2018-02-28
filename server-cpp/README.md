### Transmitter library setup
Transmitter library sources are in `telemetry/server-cpp`. Add the folder to your include search directory and add all the `.cpp` files to your build. Your platform should be automatically detected based on common `#define`s, like `ARDUINO` for Arduino targets and `__MBED__` for mbed targets.

For those using a [SCons](http://scons.org/)-based build system, a SConscript file is also included which defines a static library.

### Transmitter library usage
Include the telemetry header in your code:
```c++
#include "telemetry.h"
```

Then, instantiate a telemetry HAL (hardware abstraction layer) for your platform. This adapts the platform-specific UART into a standard interface allowing telemetry to be used across multiple platforms.

For Arduino, instantiate it with a Serial object:
```c++
telemetry::ArduinoHalInterface telemetry_hal(Serial1);
telemetry::Telemetry telemetry_obj(telemetry_hal);
```
For mbed, instantiate it with a MODSERIAL object (which provides transmit and receive buffering):
```c++
MODSERIAL telemetry_serial(PTA2, PTA1);  // PTA2 as TX, PTA1 as RX
telemetry_serial.baud(38400); // This rate should match with how you start the plotter.
telemetry::MbedHal telemetry_hal(telemetry_serial);
telemetry::Telemetry telemetry_obj(telemetry_hal);
```
*In future versions, telemetry will include a Serial buffering layer.*

Next, instantiate telemetry data objects. These objects act like their templated data types (for example, you can assign and read from a `telemetry::Numeric<uint32_t>` as if it were a regular `uint32_t`), but can both send updates and be remotely set using the telemetry link.

This example shows three data objects needed for a waterfall visualization of a linescan camera and a line plot for motor command:
```c++
telemetry::Numeric<uint32_t> tele_time_ms(telemetry_obj, "time", "Time", "ms", 0);
telemetry::NumericArray<uint16_t, 128> tele_linescan(telemetry_obj, "linescan", "Linescan", "ADC", 0);
telemetry::Numeric<float> tele_motor_pwm(telemetry_obj, "motor", "Motor PWM", "%DC", 0);
```
*Note: for default plotter usage, you must include a Numeric object with the name "Time" for the plotter to plot on the x axis*

In general, the constructor signatures for Telemetry data objects are:
- `template <typename T> Numeric(Telemetry& telemetry_container, const char* internal_name, const char* display_name, const char* units, T init_value)`
  - `Numeric` describes numeric data is type `T`. Only 8-, 16-, and 32-bit unsigned integers and single-precision floating point numbers are currently supported.
  - `telemetry_container`: a reference to a `Telemetry` object to associate this data with.
  - `internal_name`: a string giving this object an internal name to be referenced in code.
  - `display_name`: a string giving this object a human-friendly name.
  - `units`: a string describing the units this data is in (not currently used for purposes other than display, but that may change).
- `template <typename T, uint32 t array_count> telemetry container, const char* internal_name, const char* display_name, const char* units, T elem_init_value)`
  - `NumericArray` describes an array of numeric objects of type `T`. Same constraints on `T` as with `Numeric` apply. `array_count` is a template parameter (like a constant) to avoid dynamic memory allocation.
  - `telemetry_container`: a reference to a `Telemetry` object to associate this data with.
  - `internal_name`: a string giving this object an internal name to be referenced in code.
  - `display_name`: a string giving this object a human-friendly name.
  - `units`: a string describing the units this data is in (not currently used for purposes other than display, but that may change).
  - `elem_init_value`: initial value of array elements.

After instantiating a data object, you can also optionally specify additional parameters:
- `Numeric` can have the limits set. The plotter GUI will set the plot bounds / waterfall intensity bounds if this is set, otherwise it will autoscale. This does NOT affect the embedded code, values will not be clipped.
  - `tele_motor_pwm.set_limits(0.0, 1.0); // lower bound, upper bound`

Note that there is a limit on how many data objects any telemetry object can have (this is used to size some internal data structures). This can be set by compiler-defining `TELEMETRY_DATA_LIMIT`. The default is 16.

Once the data objects have been set up, transmit the data definitions.  This can be done only once from the embedded side:
```c++
telemetry_obj.transmit_header();
```

The telemetry system is set up and ready to use now. Load data to be transmitted into the telemetry object by either using the assign operator or the array indexing operator. For example, to update the linescan data:
```c++
uint16_t* data = camera.read() ;
for ( uint16_t i = 0; i < 128; i++) {
  tele_linescan[i] = data[i]
}
```

Actual IO operations (and hence plotter GUI updates) only happen when `Telemetry`'s `do_io()` method is called and should be done regularly. Only the latest update per `do_io()` is transmitted, intermediate values are clobbered. Remote set operations take effect during a `do_io()` and can also be clobbered by any set operations afterwards.
```c++
telemetry_obj.do_io();
```

You can continue using the UART to transmit other data (like with `printf`s) as long as this doesn't happen during a `Telemetry` `do_io()` operation (which will corrupt the sent data) or contain a start-of-frame sequence (`0x05, 0x39`).

You can also use the UART to receive non-telemetry data, which is made available through `Telemetry`'s `receive_available()` and `read_receive()`. `receive_available()` will return `true` if there is received data in the buffer. `read_receive()` will return the next byte in the receive buffer (if the buffer is empty, the return is undefined - don't do it). The internal receive buffer size can be set by compiler-defining `TELEMETRY_SERIAL_RX_BUFFER_SIZE`. The default is 256 bytes.

One usage of this is to allow using a serial console side-by-side with the telemetry framework. An example to get commands from the console with a newline as the delimiter is:
```c++
const size_t bufsize = 256;
char inbuf[bufsize];  // receive buffer allocation
char* inptr = inbuf;  // next received byte pointer

while (telemetry_obj.receive_available()) {
  uint8_t rx = telemetry_obj.read_receive();
  if (rx == '\n') {
    *inptr = '\0';  // optionally append the string terminator
    // do something with the contents of inbuf here, such as calling mbed-RPC.
    inptr = inbuf;  // reset the received byte pointer
  } else {
    *inptr = rx;
    inptr++;  // advance the received byte pointer
    if (inptr >= inbuf + bufsize) {
      // you should emit some helpful error on overflow
      inptr = inbuf;  // reset the received byte pointer, discarding what we have
    }
  }
}
```
