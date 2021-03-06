__doc__ = \
"""
================================================================
Application Input/Output utilities (:mod:`mango.application.io`)
================================================================

.. currentmodule:: mango.application.io

Application specific input/output utilities.

Classes
=======

.. autosummary::
   :toctree: generated/
   
   HistPeaksData - 2D histogram peaks.
   HistData - 2D histogram data.

Functions
=========

.. autosummary::
   :toctree: generated/
   
   readCsvPeaksPerStdd - Reads 2D histogram peaks data (generated by Histogram_2D filter) from CSV file.
   readCsvHistData - Reads 2D histogram data (generated by Histogram_2D filter) CSV file.
"""


from mango import mpi
haveMpi4py = mpi.haveMpi4py 

import numpy as np
import scipy as sp
import copy
import sys
import logging
import os
import os.path
import re
import math
logger, rootLogger = mpi.getLoggers(__name__)


class HistPeaksData:
    """
    Peak data for 2D histogram of neighbourhood-mean vs neighbourhood
    standard-deviation data.
    """
    def __init__(self):
        self.peaksPerStdd = None
        self.peakRgnLbl   = None
    
    def getPeakRegionLabelImage(self, numMean=None):
        numStdd = self.peakRgnLbl.shape[0]
        numPeaks = self.peakRgnLbl.shape[1]/3
        maxMeanIdx = 0
        if (numMean == None):
            for i in range(numPeaks):
                maxMeanIdx = max([maxMeanIdx, np.max(self.peakRgnLbl[:,i*3+2])])
            numMean = maxMeanIdx+1
        lblImg = sp.zeros((numStdd, numMean))
        for i in range(numStdd):
            for j in range(numPeaks):
                idx = j*3
                lblImg[i, self.peakRgnLbl[i, idx+1]:self.peakRgnLbl[i, idx+2]+1] = self.peakRgnLbl[i, idx]
        
        return  lblImg


def readCsvPeaksPerStdd(peaksPerStddCsvFileName, rgnLblsPerStddCsvFileName):
    """
    Reads histogram peak data from files generated by the Histogram2D filter.
    :rtype: :obj:`HistPeaksData`
    """
    hpd = HistPeaksData()

    if (peaksPerStddCsvFileName != None):
        lines = file(peaksPerStddCsvFileName, 'r').readlines()
        lineIdx = 0
        peaksRegEx = re.compile('\\s*((mean-[0-9]*)(,\\s*stdd-[0-9]*)(,\\s*density-[0-9]*))+(.*)')
        datasetsRegEx = re.compile('.*data-file-[0-9]*="(.*)"\\s*,\\s*data-file-[0-9]*="(.*)".*\\s*,\\s*runId="(.*)"(.*)')
        foundPeaksLine = False
        peaksHeaderLine = None
        while ((not foundPeaksLine) and (lineIdx < len(lines))):
            line = lines[lineIdx].strip()
            lineIdx += 1
            foundPeaksLine = ((peaksRegEx.match(line)) != None)
            if (foundPeaksLine):
                peaksHeaderLine = line
            datasetsMtch = datasetsRegEx.match(line)
            if (datasetsMtch != None):
                fName0 = datasetsMtch.group(1)
                fName1 = datasetsMtch.group(2)
                runId  = datasetsMtch.group(3)
                rootLogger.info("CSV file     = %s" % peaksPerStddCsvFileName)
                rootLogger.info("CSV dataset0 = %s" % fName0)
                rootLogger.info("CSV dataset1 = %s" % fName1)
                rootLogger.info("CSV runId    = %s\n" % runId)

        if (foundPeaksLine):
            numPeaks = (len(peaksHeaderLine.split(","))-1)/3
            peakData = []
            line = lines[lineIdx].strip()
            while ((len(line) > 0) and (lineIdx < len(lines))):
                row = map(float,map(str.strip, line.split(",")))
                peakData.append(row)
                lineIdx += 1
                if (lineIdx < len(lines)):
                    line = lines[lineIdx].strip()
    
            hpd.peaksPerStdd = sp.array(peakData, dtype="float64")
        else:
            raise RuntimeError("Could not find stdd-peaks header line in file '%s'" % peaksPerStddCsvFileName)

    if (rgnLblsPerStddCsvFileName != None):
        lines = file(rgnLblsPerStddCsvFileName, 'r').readlines()
        lineIdx = 0
        rgnsRegEx = re.compile('\\s*((rgn-lbl)(,\\s*min-idx-[0-9]*)(,\\s*max-idx-[0-9]*))+(.*)')
        datasetsRegEx = re.compile('.*data-file-[0-9]*="(.*)"\\s*,\\s*data-file-[0-9]*="(.*)".*\\s*,\\s*runId="(.*)"(.*)')
        foundRgnLblLine = False
        rgnLblHeaderLine = None
        while ((not foundRgnLblLine) and (lineIdx < len(lines))):
            line = lines[lineIdx].strip()
            lineIdx += 1
            foundRgnLblLine = ((rgnsRegEx.match(line)) != None)
            if (foundRgnLblLine):
                rgnLblHeaderLine = line
            datasetsMtch = datasetsRegEx.match(line)
            if (datasetsMtch != None):
                fName0 = datasetsMtch.group(1)
                fName1 = datasetsMtch.group(2)
                runId  = datasetsMtch.group(3)
                rootLogger.info("CSV file = %s" % rgnLblsPerStddCsvFileName)
                rootLogger.info("CSV dataset0 = %s" % fName0)
                rootLogger.info("CSV dataset1 = %s" % fName1)
                rootLogger.info("CSV runId    = %s\n" % runId)
        
        if (foundRgnLblLine):
            numPeaks = (len(rgnLblHeaderLine.split(",")))/3
            rgnLblData = []
            line = lines[lineIdx].strip()
            while ((len(line) > 0) and (lineIdx < len(lines))):
                row = map(int,map(str.strip, line.split(",")))
                rgnLblData.append(row)
                lineIdx += 1
                if (lineIdx < len(lines)):
                    line = lines[lineIdx].strip()
    
            hpd.peakRgnLbl = sp.array(rgnLblData, dtype="int64")
        else:
            raise RuntimeError("Could not find rgn-lbl-header line in file '%s'" % rgnLblsPerStddCsvFileName)

    if ((hpd.peaksPerStdd == None) and (hpd.peakRgnLbl == None)):
        hpd = None

    return hpd

class HistData:
    """
    2D histogram object.
    """
    def __init__(self):
        self.fName0      = "x"
        self.fName1      = "y"
        self.runId       = ""
        self.hist2dData  = None
        self.hist1dData0 = None
        self.hist1dData1 = None
        self.x           = None
        self.y           = None
        self.edges       = None
        self.peaksData   = None

def getPerStddFileNames(csvFileName):
    peaksPerStddFileName = None
    rgnLblPerStddFileName = None
    
    csvDir,csvLeafFileName = os.path.split(csvFileName) 
    fNameRegEx = re.compile('hist2d_([0-9]*_[0-9]*_.*)')
    mtch = fNameRegEx.match(csvLeafFileName)
    if (mtch != None):
        peaksPerStddFileName = os.path.join(csvDir, "hist2d_stdd_peaks_" + mtch.group(1))
        rgnLblPerStddFileName = os.path.join(csvDir, "hist2d_stdd_regn_lbl_" + mtch.group(1))
        if (not os.path.exists(peaksPerStddFileName)):
            peaksPerStddFileName = None
        if (not os.path.exists(rgnLblPerStddFileName)):
            rgnLblPerStddFileName = None

    return (peaksPerStddFileName, rgnLblPerStddFileName)

def readCsvHistData(csvFileName):
    """
    Reads CSV 2D histogram data generated from the Histogram2d filter.
    
    :type csvFileName: :obj:`str`
    :param csvFileName: Name of file containing CSV histogram data.
    :rtype: :obj:`HistData`
    :return: A :obj:`HistData` object containing histogram data.
    """ 
    h2dd = HistData()
    peaksPerStddFileName, rgnLblPerStddFileName = getPerStddFileNames(csvFileName)
    hpd = readCsvPeaksPerStdd(peaksPerStddFileName, rgnLblPerStddFileName)
    h2dd.peaksData = hpd

    lines = file(csvFileName, 'r').readlines()
    lineIdx = 0
    edgesRegEx = re.compile('\\s*(bin-pts-[0-9]*)(,\\s*bin-pts-[0-9]*)*(.*)')
    datasetsRegEx = re.compile('.*data-file-[0-9]*="(.*)"\\s*,\\s*data-file-[0-9]*="(.*)".*\\s*,\\s*runId="(.*)"(.*)')
    foundEdgesLine = False
    while ((not foundEdgesLine) and (lineIdx < len(lines))):
        line = lines[lineIdx].strip()
        lineIdx += 1
        foundEdgesLine = ((edgesRegEx.match(line)) != None)
        datasetsMtch = datasetsRegEx.match(line)
        if (datasetsMtch != None):
            h2dd.fName0 = datasetsMtch.group(1)
            h2dd.fName1 = datasetsMtch.group(2)
            h2dd.runId  = datasetsMtch.group(3)
            rootLogger.info("CSV file     = %s" % csvFileName)
            rootLogger.info("CSV dataset0 = %s" % h2dd.fName0)
            rootLogger.info("CSV dataset1 = %s" % h2dd.fName1)
            rootLogger.info("CSV runId    = %s\n" % h2dd.runId)
    
    if (foundEdgesLine):
        edges = [[],[]]
        line = lines[lineIdx].strip()
        pairRegEx = re.compile("\\s*([^,]*)\\s*,\\s*([^,]*)((,.*)*)")
        while ((len(line) > 0) and (lineIdx < len(lines))):
            mtch = pairRegEx.match(line)
            if (mtch != None):
                g1 = mtch.group(1).strip()
                g2 = mtch.group(2).strip()
                if (len(g1) > 0):
                    edges[0].append(float(g1))
                if (len(g2) > 0):
                    edges[1].append(float(g2))
            lineIdx += 1
            if (lineIdx < len(lines)):
                line = lines[lineIdx].strip()
        h2dd.edges = [sp.array(edges[0], dtype="float64"), sp.array(edges[1], dtype="float64")]
        h2dd.x = (h2dd.edges[0][1:] + h2dd.edges[0][0:-1])/2.0
        h2dd.y = (h2dd.edges[1][1:] + h2dd.edges[1][0:-1])/2.0

        foundCountsLine = False
        countsRegEx = re.compile('\\s*bin-[0-9]*-idx\\s*,\\s*bin-[0-9]*-idx\\s*,\\s*count')
        while ((not foundCountsLine) and (lineIdx < len(lines))):
            line = lines[lineIdx].strip()
            lineIdx += 1
            foundCountsLine = ((countsRegEx.match(line)) != None)

        if (foundCountsLine):
            h2dd.hist2dData = sp.zeros((h2dd.x.size, h2dd.y.size), dtype="float64")
            if (lineIdx < len(lines)):
                line = lines[lineIdx].strip()
            tripleRegEx = re.compile("\\s*([^,]*)\\s*,\\s*([^,]*),\\s*([^,]*)")
            while (lineIdx < len(lines)):
                mtch = tripleRegEx.match(line)
                if (mtch != None):
                    triple = [int(mtch.group(1).strip()), int(mtch.group(2).strip()), int(mtch.group(3).strip())]
                    h2dd.hist2dData[triple[0], triple[1]] = triple[2]
                lineIdx += 1
                if (lineIdx < len(lines)):
                    line = lines[lineIdx].strip()

            h2dd.hist1dData0 = sp.sum(h2dd.hist2dData, axis=0)
            h2dd.hist1dData1 = sp.sum(h2dd.hist2dData, axis=1)

        else:
            raise RuntimeError("Could not find bin-counts header line in file '%s'" % csvFileName)
    else:
        raise RuntimeError("Could not find bin-pts header line in file '%s'" % csvFileName)

    # transpose everything for plotting
    tmp = h2dd
    h2dd = copy.copy(h2dd)
    h2dd.x              = tmp.y
    h2dd.y              = tmp.x
    h2dd.edges          = [tmp.edges[1], tmp.edges[0]]
    h2dd.hist2dData     = tmp.hist2dData.transpose()
    h2dd.hist1dData0    = tmp.hist1dData1
    h2dd.hist1dData1    = tmp.hist1dData0

    return h2dd

__all__ = [s for s in dir() if not s.startswith('_')]

