"""
Converts the BrainVision EEG data format into tab-delimited text format

BrainVision creates three data files per recording session:
1) .vhdr - the header file
  This contains all the metadata regarding the format of the recording, how
  many channels, sample rate, channel info
2) .vmrk - the marker file
  This contains all trigger data
3) .eeg - the raw data packed sequentially into a binary file
  The data is interleaved by channel. The default PyCorder format is
  32-bit float
"""
__author__ = 'Byron Galbraith'

import sys
import struct
import numpy as np
import re


class Parser(object):
    def init(self):
        self.fs = None
        self.nChannels = None
        self.nSamples = None
        self.nTriggers = None
        self.channel_labels = []
        self.trigger_points = []
        self.data = None

    def parse_eeg(self):
        fh = open(self.session_name + '.eeg', 'rb')
        raw = fh.read()
        fh.close()
        data = struct.unpack('%df' % (len(raw)/4), raw)
        self.nSamples = len(data) / self.nChannels
        self.data = np.array(data).reshape((self.nSamples, self.nChannels))

    def parse_header(self):
        fh = open(self.session_name + '.vhdr', 'r')
        data = fh.read()
        fh.close()
        m = re.search('NumberOfChannels=(\d+)', data)
        self.nChannels = int(m.group(1))
        m = re.search('SamplingInterval=(\d+)', data)
        self.fs = 1 / (int(m.group(1)) / 1000)
        for i in xrange(1, self.nChannels+1):
            m = re.search('Ch%d=(\w+),' % i, data)
            self.channel_labels.append(m.group(1))

    def parse_marker(self):
        fh = open(self.session_name + '.vmrk', 'r')
        data = fh.read()
        fh.close()
        i = 2
        m = re.search('Mk%d=\w+,([\w\s]+),(\d+),' % i, data)
        while m is not None:
            trigger = m.group(1)
            # our current trigger format looks like 'S #', and we only want to
            # retain the number
            self.trigger_points.append((int(trigger[-1]), int(m.group(2))))
            i += 1
            m = re.search('Mk%d=\w+,([\w\s]+),(\d+),' % i, data)
        self.nTriggers = i - 2

    def convert(self, session):
        self.init()
        session = str(session)
        self.session_name = session
        print "parsing header"
        self.parse_header()
        print "parsing markers"
        self.parse_marker()
        print "parsing data"
        self.parse_eeg()
        print "collating"
        header = '\t'.join(self.channel_labels) + '\tTrigger'
        triggers = np.zeros((self.nSamples, 1))
        for trigger in self.trigger_points:
            triggers[trigger[1]] = trigger[0]
        data = np.hstack((self.data, triggers))
        np.savetxt(self.session_name + '.txt', data, header=header,
                   fmt='%10.5f', delimiter='\t')


if __name__ == "__main__":
    args = sys.argv
    session = args[1]
    parser = Parser()
    parser.convert(session)