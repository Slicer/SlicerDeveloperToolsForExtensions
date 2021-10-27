from __future__ import print_function

import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

import json
import logging
import os
import requests
import sys
import time

#
# ExtensionStats
#

class ExtensionStats(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Extension Download Statistics" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Developer Tools"]
    self.parent.dependencies = []
    self.parent.contributors = ["Andras Lasso (PerkLab, Queen's University), Jean-Christophe Fillion-Robin (Kitware)"]
    self.parent.helpText = """
    This module retrieves cumulated download statistics for a Slicer extension from the Slicer app store.
    """
    self.parent.acknowledgementText = """
    This work was funded by Cancer Care Ontario Applied Cancer Research Unit (ACRU) and the Ontario Consortium for Adaptive Interventions in Radiation Oncology (OCAIRO) grants.
    """

#
# ExtensionStatsWidget
#

class ExtensionStatsWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = ExtensionStatsLogic()

    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    extensionNameBox = qt.QHBoxLayout()

    self.extensionNameEdit = qt.QLineEdit()
    # Developers usually have a list of extensions that they are interested in, remember that in application settings
    self.extensionNameEdit.setText(qt.QSettings().value('ExtensionStats/ExtensionNames', ''))
    self.extensionNameEdit.toolTip = "Comma-separated list of extension to collect download statistics for. If not specified then all extensions will be listed."
    extensionNameBox.addWidget(self.extensionNameEdit)

    self.extensionNameAllButton = qt.QPushButton()
    self.extensionNameAllButton.text = "all"
    self.extensionNameAllButton.toolTip = "Get statistics for all extensions"
    extensionNameBox.addWidget(self.extensionNameAllButton)

    parametersFormLayout.addRow("Extension names: ", extensionNameBox)

    self.applyButton = qt.QPushButton("Get download statistics")
    self.applyButton.toolTip = "Get download statistics"
    parametersFormLayout.addRow(self.applyButton)

    # Stats table
    self.statsTableWidget = slicer.qMRMLTableView()
    self.statsTableWidget.setMRMLScene(slicer.mrmlScene)
    parametersFormLayout.addRow("Statistics:", self.statsTableWidget)
    policy = qt.QSizePolicy()
    policy.setVerticalStretch(1)
    policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
    policy.setVerticalPolicy(qt.QSizePolicy.Expanding)
    self.statsTableWidget.setSizePolicy(policy)

    self.statsTableNode = slicer.vtkMRMLTableNode()
    self.statsTableNode.SetName('ExtensionStats')
    self.statsTableNode.SetUseColumnNameAsColumnHeader(True)
    self.statsTableNode.SetUseFirstColumnAsRowHeader(True)
    slicer.mrmlScene.AddNode(self.statsTableNode)
    self.statsTableWidget.setMRMLTableNode(self.statsTableNode)

    # Copy to clipboard button
    self.copyToClipboardButton = qt.QPushButton("Copy table to clipboard")
    parametersFormLayout.addRow('', self.copyToClipboardButton)

    # connections
    self.extensionNameAllButton.connect('clicked()', self.populateExtensionNameEdit)
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.copyToClipboardButton.connect('clicked()', self.copyTableToClipboard)

    # Add vertical spacer
    #self.layout.addStretch(1)

  def cleanup(self):
    pass

  def populateExtensionNameEdit(self):
    extensionsList = self.logic.getExtensionNames()
    extensionsList.sort()
    extensionNames = ",".join(extensionsList)
    self.extensionNameEdit.setText(extensionNames)

  def onApplyButton(self):

    # Save last extension list
    qt.QSettings().setValue('ExtensionStats/ExtensionNames', self.extensionNameEdit.text)

    # Get list of extension names (can be used to limit the query)
    if self.extensionNameEdit.text.strip():
      extensionNames = list(map(str.strip, self.extensionNameEdit.text.split(',')))
    else:
      extensionNames = None

    self.logic.getExtensionDownloadStatsAsTable(self.statsTableNode, extensionNames)

  def copyTableToClipboard(self):
    table = self.statsTableNode.GetTable()
    tableText = ''

    header = []
    for columnIndex in range(table.GetNumberOfColumns()):
      header.append(table.GetColumn(columnIndex).GetName())
    tableText += '\t'.join(header) # convert list to tab-separated string

    for rowIndex in range(table.GetNumberOfRows()):
      tableText += '\n'
      for columnIndex in range(table.GetNumberOfColumns()):
        if columnIndex>0:
          tableText += '\t'
        tableText += table.GetColumn(columnIndex).GetValue(rowIndex)
    qt.QApplication.clipboard().setText(tableText)

#
# ExtensionStatsLogic
#

class ExtensionStatsLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)

    # The list of revision for each release is reported here:
    # http://wiki.slicer.org/slicerWiki/index.php/Release_Details
    # Only stable releases must be listed here (preview releases
    # will be listed as post-SomeStableRelease)
    releases_revisions = {
      '4.0.0': '18777',
      '4.0.1': '19033',
      '4.1.0': '19886',
      '4.1.1': '20313',
      '4.2.0': '21298',
      '4.2.1': '21438',
      '4.2.2': '21508',
      '4.2.2-1': '21513',
      '4.3.0': '22408',
      '4.3.1': '22599',
      '4.3.1-1': '22704',
      '4.4.0': '23774',
      '4.5.0-1': '24735',
      '4.6.0': '25441',
      '4.6.2': '25516',
      '4.8.0': '26489',
      '4.8.1': '26813',
      '4.10.0': '27510',
      '4.10.1': '27931',
      '4.10.2': '28257',
      '4.11.20200930': '29402',
      '4.11.20210226': '29738',
    }

    # sort releases based on SVN revision
    self.releases_revisions = sorted(releases_revisions.items(), key=lambda t: t[1])

    self.legacyReleaseName = "legacy"
    self.unknownReleaseName = "unknown"

    self.baselineExtensionDownloadStatsFile = os.path.dirname(slicer.modules.extensionstats.path) + "/Resources/ExtensionsDownloadStats-20211027.csv"

    self.downloadstatsUrl = "https://slicer-packages.kitware.com/api/v1/app/5f4474d0e1d8c75dfc705482/downloadstats"
    self.downloadstats = None

  #---------------------------------------------------------------------------
  def getExtensionNames(self):
    extension_release_downloads = self.getExtensionDownloadStats()
    return list(extension_release_downloads.keys())

  #---------------------------------------------------------------------------
  def getSlicerReleasesRevisions(self):
    """Return dictionary of Slicer release and associated Slicer revision."""
    return self.releases_revisions

  #---------------------------------------------------------------------------
  def getSlicerReleaseNames(self):
    """Return sorted list of release names.
    legacy: before any known release.
    unknown: invalid revision (not integer)
    """
    releasesRevisions = self.getSlicerReleasesRevisions()
    releases = [self.unknownReleaseName, self.legacyReleaseName]
    for releaseRevision in releasesRevisions:
      releases.append(releaseRevision[0])
      releases.append('post-'+releaseRevision[0])
    return releases

  #---------------------------------------------------------------------------
  def getSlicerReleaseName(self, revision):
      """Return Slicer release name that corresponds to a Slicer revision.
      Downloads associated with nightly build happening between release A and B are
      associated with post-A "release".
      """

      # Get sorted list of releases and nightly versions
      releasesRevisions = self.getSlicerReleasesRevisions()

      try:
          revision = int(revision)
      except ValueError:
          return self.unknownReleaseName

      release = self.legacyReleaseName
      for releaseRevision in releasesRevisions:
          if revision < int(releaseRevision[1]):
              break
          if revision == int(releaseRevision[1]):
              # Exact match to a release
              release = releaseRevision[0]
              break
          release = 'post-'+releaseRevision[0]

      return release

  #---------------------------------------------------------------------------
  def getExtensionDownloadStats(self, extensionNames=None):
      """Return download count for extensions in a map indexed by extensionName and release.
      :param extensionNames: list containing extension names to consider, of None then statistics will be provided for all.
      """

      extension_release_downloads = {}

      # Read baseline extension downloads from CSV file (that are not available in the current server stats
      # because they were collected using the old Midas server)
      import csv
      with open(self.baselineExtensionDownloadStatsFile, 'r') as csvfile:
          datareader = csv.reader(csvfile)
          rows = iter(datareader)
          columns = next(rows)
          for row in rows:
              extensionName = row[0]
              if extensionNames and (extensionName not in extensionNames):
                  # this extension is not in the requested list of extensions
                  continue
              for release, downloadCount in zip(columns[1:], row[1:]):
                  downloadCount = int(downloadCount)
                  if downloadCount == 0:
                      continue
                  if extensionName not in extension_release_downloads:
                      extension_release_downloads[extensionName] = {}
                  if release not in extension_release_downloads[extensionName]:
                      extension_release_downloads[extensionName][release] = 0
                  extension_release_downloads[extensionName][release] += downloadCount

      # Get current extension download stats from Extensions Server (Girder server)
      if self.downloadstats is None:
        resp = requests.get(self.downloadstatsUrl)
        self.downloadstats = resp.json()
      for revision in self.downloadstats:
          release = self.getSlicerReleaseName(revision)
          if 'extensions' not in self.downloadstats[revision]:
            # no extensions downloaded for this release
            continue
          for extensionName in self.downloadstats[revision]['extensions']:
              if extensionNames and (extensionName not in extensionNames):
                  # this extension is not in the requested list of extensions
                  continue
              downloadCount = 0
              try:
                  downloadCount += self.downloadstats[revision]['extensions'][extensionName]['win']['amd64']
              except:
                  pass
              try:
                  downloadCount += self.downloadstats[revision]['extensions'][extensionName]['macosx']['amd64']
              except:
                  pass
              try:
                  downloadCount += self.downloadstats[revision]['extensions'][extensionName]['linux']['amd64']
              except:
                  pass
              if downloadCount == 0:
                continue
              if extensionName not in extension_release_downloads:
                extension_release_downloads[extensionName] = {}
              if release not in extension_release_downloads[extensionName]:
                extension_release_downloads[extensionName][release] = 0
              extension_release_downloads[extensionName][release] += downloadCount

      return extension_release_downloads

  def getExtensionDownloadStatsAsTable(self, statsTableNode, extensionNames):
      
      # Initialize columns

      extensionNamesColumn = vtk.vtkStringArray()
      extensionNamesColumn.SetName("Extension")

      releases = self.getSlicerReleaseNames()
      releaseColumns = {}
      for release in releases:
        releaseColumns[release] = vtk.vtkIntArray()
        releaseColumns[release].SetName(release)

      # Fill columns

      extension_release_downloads = self.getExtensionDownloadStats(extensionNames)
      if not extensionNames:
        extensionNames = extension_release_downloads.keys()

      for extensionName in extensionNames:
          if extensionName not in extension_release_downloads:
            continue
          extensionNamesColumn.InsertNextValue(extensionName)
          release_downloads = extension_release_downloads[extensionName]
          for release in releases:
              releaseColumns[release].InsertNextValue(release_downloads[release] if (release in release_downloads) else 0)

      # Add columns to table
      
      statsTableNode.RemoveAllColumns()
      statsTableNode.AddColumn(extensionNamesColumn)
      for release in releases:
        statsTableNode.AddColumn(releaseColumns[release])
      statsTableNode.Modified()


class ExtensionStatsTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_ExtensionStats1()

  def test_ExtensionStats1(self):
    self.delayDisplay("Starting the test")

    logic = ExtensionStatsLogic()
    extension_release_downloads = logic.getExtensionDownloadStats("SlicerRT")
    print(repr(extension_release_downloads))
    self.assertTrue(len(extension_release_downloads["SlicerRT"]) > 0)
    self.assertTrue(extension_release_downloads["SlicerRT"]["4.2.0"] >= 146)

    self.delayDisplay('Test passed!')

def main(argv):
  import argparse, json, csv

  parser = argparse.ArgumentParser(description="Slicer Extensions download statistics query tool")
  parser.add_argument('-e', '--extensions', dest="extensionsList", required=False, help="Extension(s) to be queried. If more than one, separate by comma. If not specified, all extensions will be queried.")
  parser.add_argument('-j', '--output-json', dest="jsonName", required=False, help="Name of the output JSON file to store the results.")
  parser.add_argument('-s', '--output-csv', dest="csvName", required=False, help="Name of the output JSON file to store the results.")

  args = parser.parse_args(argv)

  logic = ExtensionStatsLogic()

  if args.extensionsList is None:
    extensionsList = logic.getExtensionNames()
    extensionsList.sort()
  else:
    extensionsList = args.extensionsList.split(',')

  extension_release_downloads = logic.getExtensionDownloadStats(extensionsList)

  if args.jsonName:
    jsonStats = json.dumps(extension_release_downloads, indent=2)
    with open(args.jsonName, 'w') as jsonFile:
      jsonFile.write(jsonStats)

  if args.csvName:
    with open(args.csvName, 'w', newline='') as csvFile:
      csvWriter = csv.writer(csvFile, delimiter=',')

      releases = logic.getSlicerReleaseNames()
      csvWriter.writerow(['Extension name']+releases)

      for extensionName in extensionsList:
        if extensionName not in extension_release_downloads:
          continue

        release_downloads = extension_release_downloads[extensionName]
        extensionStats = [extensionName]
        for release in releases:
          if release in release_downloads:
            extensionStats = extensionStats+[release_downloads[release]]
          else:
            extensionStats = extensionStats+['0']
        csvWriter.writerow(extensionStats)


  sys.exit(0)


if __name__ == "__main__":
  main(sys.argv[1:])
