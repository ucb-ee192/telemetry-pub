from matplotlib import pyplot as plt
import matplotlib.animation as animation
import numpy as np
import serial

from telemetry.parser import *

class PlotData():
  def __init__(self, indep_name, dep_name, indep_span, subplot, line):
    self.indep_span = indep_span
    self.indep_name = indep_name
    self.dep_name = dep_name
    self.subplot = subplot
    self.line = line
    
    self.indep_data = deque()
    self.dep_data = deque()
  
  def update_from_packet(self, packet):
    assert isinstance(packet, DataPacket)
    data_names = packet.get_data_names()
    
    if self.indep_name in data_names and self.dep_name in data_names:
      latest_indep = packet.get_data(self.indep_name)
      self.indep_data.append(latest_indep)
      self.dep_data.append(packet.get_data(self.dep_name))
      
      indep_cutoff = latest_indep - self.indep_span
      
      while self.indep_data[0] < indep_cutoff:
        self.indep_data.popleft()
        self.dep_data.popleft()
        
      self.line.set_xdata(self.indep_data)
      self.line.set_ydata(self.dep_data)

  def get_indep_range(self):
    return [self.indep_data[0], self.indep_data[-1]]

  def set_indep_range(self, indep_range):
    self.subplot.set_xlim(indep_range)

  def autoset_dep_range(self):
    minlim = min(self.dep_data)
    maxlim = max(self.dep_data)
    if minlim < 0 and maxlim < 0:
      maxlim = 0
    elif minlim > 0 and maxlim > 0:
      minlim = 0
    self.subplot.set_ylim(minlim, maxlim)

if __name__ == "__main__":
  timespan = 10000
  independent_axis_name = 'time'
  
  telemetry = TelemetrySerial(serial.Serial("COM61", baudrate=1000000))
  all_plotdata = []
  fig = plt.figure()
  
  def update(data):
    telemetry.process_rx()
    plot_updated = False
    
    while True:
      packet = telemetry.next_rx_packet()
      if not packet:
        break
      
      #print('')
      #print(packet)
      plot_updated = True
      
      if isinstance(packet, HeaderPacket):
        all_plotdata.clear()
        fig.clf()
        
        plot_count = 0
        for data_def in packet.get_data_defs().values():
          if data_def.internal_name != independent_axis_name:
            plot_count += 1
            
        plot_idx = 0
        ax0 = None
        for data_def in packet.get_data_defs().values():
          if data_def.internal_name == independent_axis_name:
            continue
          
          if not ax0:
            ax0 = ax = fig.add_subplot(plot_count, 1, plot_count-plot_idx)
          else:
            ax = fig.add_subplot(plot_count, 1, plot_count-plot_idx, sharex=ax0)
            #ax.set_xticklabels([])
          plot_idx += 1

          ax.set_title("%s: %s (%s)"
                       % (data_def.internal_name, data_def.display_name, data_def.units))
          line, = ax.plot([0])
          plotdata = PlotData(independent_axis_name, data_def.internal_name,
                              timespan, ax, line)
          all_plotdata.append(plotdata)
          
          print("Found dependent data %s" % data_def.internal_name)

      elif isinstance(packet, DataPacket):
        indep_range = [None, None]
        for plotdata in all_plotdata:
          plotdata.update_from_packet(packet)
      else:
        raise Exception("Unknown received packet %s" % repr(next_packet))
      
    while True:
      next_byte = telemetry.next_rx_byte()
      if next_byte is None:
        break
      print(chr(next_byte), end='')

    if plot_updated:
      for plotdata in all_plotdata:
        plotdata.autoset_dep_range()
        
        plotdata_range = plotdata.get_indep_range()
        if (indep_range[0] is None) or (plotdata_range[0] < indep_range[0]):
          indep_range[0] = plotdata_range[0]
        if (indep_range[1] is None) or (plotdata_range[1] > indep_range[1]):
          indep_range[1] = plotdata_range[1]
          
      all_plotdata[-1].set_indep_range(indep_range)  

  ani = animation.FuncAnimation(fig, update, interval=100)
  plt.show()
