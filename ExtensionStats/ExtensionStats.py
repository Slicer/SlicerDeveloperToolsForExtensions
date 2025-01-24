import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.i18n import tr as _
from slicer.i18n import translate

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

    # # Set module icon from Resources/Icons/<ModuleName>.png
    # moduleDir = os.path.dirname(self.parent.path)
    # iconPath = os.path.join(moduleDir, 'Resources/Icons', self.moduleName+'.svg')
    # if os.path.isfile(iconPath):
    #   parent.icon = qt.QIcon(iconPath)

    self.parent.title = _("Extension Download Statistics")
    self.parent.categories = [translate("qSlicerAbstractCoreModule", "Developer Tools")]
    self.parent.dependencies = []
    self.parent.contributors = ["Andras Lasso (PerkLab, Queen's University), Jean-Christophe Fillion-Robin (Kitware)"]
    self.parent.helpText = _("This module retrieves cumulated download statistics for a Slicer extension from the Slicer app store.")
    self.parent.acknowledgementText = _("This work was funded by Cancer Care Ontario Applied Cancer Research Unit (ACRU) and the Ontario Consortium for Adaptive Interventions in Radiation Oncology (OCAIRO) grants.")

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
    parametersCollapsibleButton.text = _("Parameters")
    self.layout.addWidget(parametersCollapsibleButton)

    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    extensionNameBox = qt.QHBoxLayout()

    self.extensionNameEdit = qt.QLineEdit()
    # Developers usually have a list of extensions that they are interested in, remember that in application settings
    self.extensionNameEdit.setText(qt.QSettings().value('ExtensionStats/ExtensionNames', ''))
    self.extensionNameEdit.toolTip = _("Comma-separated list of extension to collect download statistics for. If not specified then all extensions will be listed.")
    extensionNameBox.addWidget(self.extensionNameEdit)

    self.extensionNameAllButton = qt.QPushButton()
    self.extensionNameAllButton.text = _("all")
    self.extensionNameAllButton.toolTip = _("Get statistics for all extensions")
    extensionNameBox.addWidget(self.extensionNameAllButton)

    parametersFormLayout.addRow(_("Extension names: "), extensionNameBox)

    self.totalDownloadsButton = qt.QPushButton(_("Get total downloads"))
    self.totalDownloadsButton.toolTip = _("Get total number of downloaded extensions per release")
    parametersFormLayout.addRow(self.totalDownloadsButton)
    self.dailyDownloadsButton = qt.QPushButton(_("Get daily downloads"))
    self.dailyDownloadsButton.toolTip = _("Get daily downloads for each extension, useful for plotting download counts over time."
        " It is just a rough estimation, assuming that the download count is evenly distributed in the time period starting"
        " with the release date and ending with the next release date. In reality, users keep using older extensions and downloading extensions for it."
        )
    parametersFormLayout.addRow(self.dailyDownloadsButton)

    # Stats table
    self.statsTableWidget = slicer.qMRMLTableView()
    self.statsTableWidget.setMRMLScene(slicer.mrmlScene)
    parametersFormLayout.addRow(_("Statistics:"), self.statsTableWidget)
    policy = qt.QSizePolicy()
    policy.setVerticalStretch(1)
    policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
    policy.setVerticalPolicy(qt.QSizePolicy.Expanding)
    self.statsTableWidget.setSizePolicy(policy)

    self.statsTableNode = slicer.vtkMRMLTableNode()
    self.statsTableNode.SetName(_('ExtensionStats'))
    self.statsTableNode.SetUseColumnTitleAsColumnHeader(True)
    self.statsTableNode.SetUseFirstColumnAsRowHeader(True)
    slicer.mrmlScene.AddNode(self.statsTableNode)
    self.statsTableWidget.setMRMLTableNode(self.statsTableNode)

    # Copy to clipboard button
    self.copyToClipboardButton = qt.QPushButton(_("Copy table to clipboard"))
    parametersFormLayout.addRow('', self.copyToClipboardButton)

    # connections
    self.extensionNameAllButton.connect('clicked()', self.populateExtensionNameEdit)
    self.totalDownloadsButton.connect('clicked(bool)', self.onTotalDownloadsButton)
    self.dailyDownloadsButton.connect('clicked(bool)', self.onDailyDownloadsButton)
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

  def _selectedExtensionNames(self):
    """Get list of extension names (can be used to limit the query)"""
    if self.extensionNameEdit.text.strip():
      extensionNames = list(map(str.strip, self.extensionNameEdit.text.split(',')))
    else:
      extensionNames = None
    return extensionNames

  def onTotalDownloadsButton(self):
    # Save last extension list
    qt.QSettings().setValue('ExtensionStats/ExtensionNames', self.extensionNameEdit.text)
    with slicer.util.tryWithErrorDisplay(_("Unexpected error."), waitCursor=True):
      self.logic.getExtensionDownloadStatsAsTable(self.statsTableNode, self._selectedExtensionNames(), mode="total")

  def onDailyDownloadsButton(self):
    # Save last extension list
    qt.QSettings().setValue('ExtensionStats/ExtensionNames', self.extensionNameEdit.text)
    with slicer.util.tryWithErrorDisplay(_("Unexpected error."), waitCursor=True):
      self.logic.getExtensionDownloadStatsAsTable(self.statsTableNode, self._selectedExtensionNames(), mode="daily")

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
        tableText += str(table.GetColumn(columnIndex).GetValue(rowIndex))
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

    self.postReleasePrefix = "post-"

    # The list of revision for each release is reported on these pages:
    # -  https://github.com/Slicer/Slicer/wiki/Release-Details
    # -  https://github.com/Slicer/Slicer/tags
    # Only stable releases must be listed here (preview releases
    # will be listed as post-SomeStableRelease).
    releases_revisionsDates = {
      '4.0.0': ['18777', '2011-11-27'],
      '4.0.1': ['19033', '2012-01-06'],
      '4.1.0': ['19886', '2012-04-12'],
      '4.1.1': ['20313', '2012-06-01'],
      '4.2.0': ['21298', '2012-10-31'],
      '4.2.1': ['21438', '2012-11-16'],
      '4.2.2': ['21508', '2012-12-07'],
      '4.2.2-1': ['21513', '2012-12-08'],
      '4.3.0': ['22408', '2013-09-04'],
      '4.3.1': ['22599', '2013-10-04'],
      '4.3.1-1': ['22704', '2013-11-14'],
      '4.4.0': ['23774', '2014-11-02'],
      '4.5.0-1': ['24735', '2015-11-12'],
      '4.6.0': ['25441', '2016-10-13'],
      '4.6.2': ['25516', '2016-11-08'],
      '4.8.0': ['26489', '2017-10-18'],
      '4.8.1': ['26813', '2017-12-19'],
      '4.10.0': ['27510', '2018-10-17'],
      '4.10.1': ['27931', '2019-01-15'],
      '4.10.2': ['28257', '2019-05-16'],
      '4.11.20200930': ['29402', '2020-09-30'],
      '4.11.20210226': ['29738', '2021-02-26'],
      '5.0.2': ['30822', '2022-05-06'],
      '5.0.3': ['30893', '2022-07-08'],
      '5.2.1': ['31317', '2022-11-24'],
      '5.2.2': ['31382', '2023-02-21'],
      '5.4.0': ['31938', '2023-08-19'],
      '5.6.0': ['32390', '2023-11-16'],
      '5.6.1': ['32438', '2023-12-12'],
      '5.6.2': ['32448', '2024-04-05'],
      '5.8.0': ['33216', '2025-01-24'],
      # NEXT RELEASE REVISION
    }

    # sort releases based on SVN revision
    self.releases_revisionsDates = sorted(releases_revisionsDates.items(), key=lambda t: t[1])

    self.legacyReleaseName = "legacy"
    self.unknownReleaseName = "unknown"
    self.legacyReleaseDate = "2009-10-07"

    self.baselineExtensionDownloadStatsFile = os.path.dirname(slicer.modules.extensionstats.path) + "/Resources/ExtensionsDownloadStats-20211027.csv"

    self.downloadstatsUrl = "https://slicer-packages.kitware.com/api/v1/app/5f4474d0e1d8c75dfc705482/downloadstats"
    self.downloadstats = None

  #---------------------------------------------------------------------------
  def getExtensionNames(self):
    extension_release_downloads = self.getExtensionDownloadStats()
    return list(extension_release_downloads.keys())

  #---------------------------------------------------------------------------
  def getSlicerReleasesRevisions(self):
    """Return dictionary of Slicer release and associated Slicer revision.
    Kept for backward compatibility only.
    """
    # Remove release date from self.releases_revisionsDates
    releases_revisions = {}
    for release, revision_date in self.releases_revisionsDates:
      releases_revisions[release] = revision_date[0]
    return releases_revisions

  #---------------------------------------------------------------------------
  def getSlicerReleaseNames(self):
    """Return sorted list of release names.
    legacy: before any known release.
    unknown: invalid revision (not integer)
    """
    releases = [self.unknownReleaseName, self.legacyReleaseName]
    for releaseRevision in self.releases_revisionsDates:
      releases.append(releaseRevision[0])
      releases.append(self.postReleasePrefix + releaseRevision[0])
    return releases

  #---------------------------------------------------------------------------
  def getSlicerReleaseName(self, revision):
      """Return Slicer release name that corresponds to a Slicer revision.
      Downloads associated with nightly build happening between release A and B are
      associated with post-A "release".
      """

      try:
          revision = int(revision)
      except ValueError:
          return self.unknownReleaseName

      release = self.legacyReleaseName
      for release_revisionDate in self.releases_revisionsDates:
          if revision < int(release_revisionDate[1][0]):
              break
          if revision == int(release_revisionDate[1][0]):
              # Exact match to a release
              release = release_revisionDate[0]
              break
          release = self.postReleasePrefix + release_revisionDate[0]

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

  def getReleaseDate(self, release):
    if release.startswith(self.postReleasePrefix):
      release = release.removeprefix(self.postReleasePrefix)
    for release_revisionDate in self.releases_revisionsDates:
      if release_revisionDate[0] == release:
        return release_revisionDate[1][1]
    return None

  def getReleaseDurationDays(self, release):
    if release.startswith(self.postReleasePrefix):
      release = release.removeprefix(self.postReleasePrefix)
    startDate = None
    endDate = None
    for release_revisionDate in self.releases_revisionsDates:
      if not startDate:
        # Looking for release date
        if release_revisionDate[0] == release:
          startDate = release_revisionDate[1][1]
      else:
        # Release date is found, now get the next release date
        endDate = release_revisionDate[1][1]
    if not startDate:
      raise ValueError("Cannot determine release duration for release: " + release)
    if not endDate:
      # Get current date as string
      endDate = time.strftime("%Y-%m-%d")
    # Get duration in days
    startDate = time.strptime(startDate, "%Y-%m-%d")
    endDate = time.strptime(endDate, "%Y-%m-%d")
    startDateSec = time.mktime(startDate)
    endDateSec = time.mktime(endDate)
    return int((endDateSec - startDateSec) / (24 * 3600))

  def getExtensionDownloadStatsAsTable(self, statsTableNode, extensionNames, mode=None):
      """mode:
        - `total` (default)
        - `daily`
      """
      # Initialize columns
      if mode is None:
        mode = "total"

      extensionNamesColumn = vtk.vtkStringArray()
      extensionNamesColumn.SetName("Extension")

      releases = self.getSlicerReleaseNames()
      releaseDurationDaysreleaseDurationDays = {}
      releaseColumns = {}
      for release in releases:
        if mode == "total":
          releaseColumns[release] = vtk.vtkIntArray()
          date = self.getReleaseDate(release)
          if date and not release.startswith(self.postReleasePrefix):
            name = f"{release} ({self.getReleaseDate(release)})"
          else:
            name = release
          releaseColumns[release].SetName(name)
        elif mode == "daily":
          if release in [self.unknownReleaseName, self.legacyReleaseName]:
            # we don't have dates for these releases, so we ignore them
            continue
          if release.startswith(self.postReleasePrefix):
            # we merge release and post-release stats
            continue
          releaseColumns[release] = vtk.vtkFloatArray()
          releaseColumns[release].SetName(self.getReleaseDate(release))
        else:
          raise ValueError("Invalid mode: " + mode)

      # Fill columns

      extension_release_downloads = self.getExtensionDownloadStats(extensionNames)
      if not extensionNames:
        extensionNames = extension_release_downloads.keys()

      for extensionName in extensionNames:
          if extensionName not in extension_release_downloads:
            continue
          extensionNamesColumn.InsertNextValue(extensionName)
          release_downloads = extension_release_downloads[extensionName]
          if mode == "total":
            for release in releaseColumns:
                releaseColumns[release].InsertNextValue(release_downloads[release] if (release in release_downloads) else 0)
          elif mode == "daily":
            for release in releaseColumns:
                releaseDurationDay = self.getReleaseDurationDays(release)
                dailyDownloadCount = 0
                if release in release_downloads:
                  dailyDownloadCount += release_downloads[release] / releaseDurationDay
                if self.postReleasePrefix + release in release_downloads:
                  dailyDownloadCount += release_downloads[self.postReleasePrefix + release] / releaseDurationDay
                releaseColumns[release].InsertNextValue(dailyDownloadCount)
          else:
            raise ValueError("Invalid mode: " + mode)

      # Add columns to table

      statsTableNode.RemoveAllColumns()
      statsTableNode.AddColumn(extensionNamesColumn)
      for release in releaseColumns:
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
