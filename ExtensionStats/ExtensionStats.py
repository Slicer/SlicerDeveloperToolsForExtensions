import os
import unittest
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

import collections
import json
import urllib
import urllib2
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
    self.logic.setStatusCallback(self.setStatusText)

    self.queryInProgress = False

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
    self.extensionNameEdit.setText('')
    extensionNameBox.addWidget(self.extensionNameEdit)

    self.extensionNameAllButton = qt.QPushButton()
    self.extensionNameAllButton.text = "all"
    self.extensionNameAllButton.toolTip = "Get statistics for all extensions"
    extensionNameBox.addWidget(self.extensionNameAllButton)
    self.populateExtensionNameEdit()

    parametersFormLayout.addRow("Extension name: ", extensionNameBox)

    self.applyButton = qt.QPushButton("Get download statistics")
    self.applyButton.toolTip = "Get download statistics"
    parametersFormLayout.addRow(self.applyButton)

    self.statusText = qt.QLabel()
    parametersFormLayout.addRow("Status:", self.statusText)

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
    extensionNames = ",".join(self.logic.getExtensionNames())
    self.extensionNameEdit.setText(extensionNames)

  def onApplyButton(self):

    if self.queryInProgress:
      self.logic.setCancelRequested(True)
      self.applyButton.setText("Cancelling...")
      self.applyButton.enabled = False
      slicer.app.processEvents()
      return

    # Get sorted list of releases and nightly versions
    releases = self.logic.getSlicerReleaseNames()

    # Initialize table contents: clear and add release column
    self.statsTableNode.RemoveAllColumns()
    self.statsTableNode.AddColumn().SetName("Extension")
    for release in releases:
      self.statsTableNode.AddColumn().SetName(release)
    self.statsTableNode.Modified()

    self.applyButton.setText("Cancel")
    self.queryInProgress = True
    slicer.app.processEvents()

    for extensionName in self.extensionNameEdit.text.split(','):

      release_downloads = self.logic.getExtensionDownloadStats(extensionName)

      if self.logic.getCancelRequested():
        break

      # Add results to table
      newRowIndex = self.statsTableNode.AddEmptyRow()
      self.statsTableNode.SetCellText(newRowIndex,0, extensionName)
      for (idx, release) in enumerate(releases):
        if release in release_downloads.keys():
          self.statsTableNode.SetCellText(newRowIndex,idx+1, str(release_downloads[release]))
        else:
          self.statsTableNode.SetCellText(newRowIndex,idx+1, "0")

    self.queryInProgress = False
    self.logic.setCancelRequested(False)
    self.applyButton.setText("Get download statistics")
    self.applyButton.enabled = True

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

  def setStatusText(self, text):
    self.statusText.text = text

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
    self.statusCallback = None
    self.cancelRequested = False

    # Sampling ratio of info packages. Useful for testing or getting approximations
    # of download counts with reduced waiting time.
    # Value of 1.0 means all packages are queried.
    # Smaller value results in less accurate information but faster results.
    self.package_sampling_ratio = 1.0

    # List of extension names obtained doing:
    #  $ git clone github.com/Slicer/ExtensionsIndex SlicerExtensionsIndex
    #  $ cd SlicerExtensionsIndex
    #  $ for name in $(ls -1 | cut -d"." -f1); do echo "'$name',"; done
    #
    self.extension_names = [
        'ABC',
        'AnglePlanesExtension',
        'AnomalousFiltersExtension',
        'BoneTextureExtension',
        'CardiacAgatstonMeasures',
        'Cardiac_MRI_Toolkit',
        'CarreraSlice',
        'CBC_3D_I2MConversion',
        'ChangeTracker',
        'Chest_Imaging_Platform',
        'CleaverExtension',
        'CMFreg',
        'CornerAnnotation',
        'CurveMaker',
        'DatabaseInteractor',
        'DCMQI',
        'DebuggingTools',
        'DeepInfer',
        'DeveloperToolsForExtensions',
        'DiceComputation',
        'DiffusionQC',
        'DSCMRIAnalysis',
        'DTIAtlasBuilder',
        'DTIAtlasFiberAnalyzer',
        'DTIPrep',
        'DTIProcess',
        'DTI-Reg',
        'EasyClip',
        'Eigen3',
        'ErodeDilateLabel',
        'exStone',
        'FacetedVisualizer',
        'FastGrowCutEffect',
        'FiberViewerLight',
        'FilmDosimetryAnalysis',
        'GelDosimetryAnalysis',
        'GraphCutSegment',
        'GyroGuide',
        'IASEM',
        'iGyne',
        'ImageMaker',
        'IntensitySegmenter',
        'LAScarSegmenter',
        'LASegmenter',
        'LesionSpotlight',
        'LightWeightRobotIGT',
        'LongitudinalPETCT',
        'MABMIS',
        'MarginCalculator',
        'MarkupsToModel',
        'MatlabBridge',
        'MeshStatisticsExtension',
        'MeshToLabelMap',
        'ModelClip',
        'ModelToModelDistance',
        'mpReview',
        'MultiLevelRegistration',
        'NeedleFinder',
        'OpenCAD',
        'OpenCVExample',
        'OsteotomyPlanner',
        'PathReconstruction',
        'PBNRR',
        'PedicleScrewSimulator',
        'PercutaneousApproachAnalysis',
        'PerkTutor',
        'PETDICOMExtension',
        'PET-IndiC',
        'PETLiverUptakeMeasurement',
        'PetSpectAnalysis',
        'PETTumorSegmentation',
        'PickAndPaintExtension',
        'PkModeling',
        'PortPlacement',
        'Q3DC',
        'QuantitativeReporting',
        'Radiomics',
        'README',
        'RegQAExtension',
        'ResampleDTIlogEuclidean',
        'ResectionPlanner',
        'ROBEXBrainExtraction',
        'RSSExtension',
        'Sandbox',
        'ScatteredTransform',
        'Scoliosis',
        'scripts',
        'SegmentationAidedRegistration',
        'SegmentationWizard',
        'SegmentEditorExtraEffects',
        'SegmentMesher',
        'SegmentRegistration',
        'SequenceRegistration',
        'Sequences',
        'ShapePopulationViewer',
        'ShapeQuantifier',
        'ShapeRegressionExtension',
        'ShapeVariationAnalyzer',
        'SkeletalRepresentation',
        'SkullStripper',
        'Slicer-AirwaySegmentation',
        'SlicerAstro',
        'SlicerAutoscroll',
        'SlicerCaseIterator',
        'SlicerCochlea',
        'SlicerDevelopmentToolbox',
        'SlicerDMRI',
        'SlicerElastix',
        'SlicerFab',
        'SlicerHeart',
        'SlicerIGSIO',
        'SlicerIGT',
        'SlicerITKUltrasound',
        'SlicerJupyter',
        'SlicerLayoutButtons',
        'SlicerOpenCV',
        'SlicerOpenIGTLink',
        'SlicerPathology',
        'SlicerPETPhantomAnalysis',
        'SlicerProstateAblation',
        'SlicerProstate',
        'SlicerRT',
        'SlicerToKiwiExporter',
        'Slicer-TrackerStabilizer',
        'SlicerVASST',
        'SlicerVideoCameras',
        'SlicerVirtualReality',
        'SlicerVMTK',
        'Slicer-Wasp',
        'SlicerWMA',
        'SliceTracker',
        'SNRMeasurement',
        'SoundControl',
        'SPHARM-PDM',
        'SwissSkullStripper',
        'T1Mapping',
        'T2mapping',
        'TCIABrowser',
        'TOMAAT',
        'UKFTractography',
        'VASSTAlgorithms',
        'VirtualFractureReconstruction',
        'VolumeClip',
        'WindowLevelEffect',
        'XNATSlicer',
        'ZFrameRegistration',
    ]

    # The list of revision for each release is reported here:
    # http://wiki.slicer.org/slicerWiki/index.php/Release_Details
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
      '4.11.0': '27529'
    }

    # sort releases based on SVN revision
    self.releases_revisions = sorted(releases_revisions.items(), key=lambda t: t[1])

    self.legacyReleaseName = "legacy"
    self.unknownReleaseName = "unknown"

  #---------------------------------------------------------------------------
  def getDefaultMidasJsonQueryUrl(self):
   return "http://slicer.kitware.com/midas3/api/json"

  #---------------------------------------------------------------------------
  def getExtensionNames(self):
    return self.extension_names

  #---------------------------------------------------------------------------
  def setStatusCallback(self, callbackMethod):
    self.statusCallback = callbackMethod

  #---------------------------------------------------------------------------
  def setCancelRequested(self, cancelRequested):
    self.cancelRequested = cancelRequested

  #---------------------------------------------------------------------------
  def getCancelRequested(self):
    slicer.app.processEvents() # get a chance of button presses to be processed
    return self.cancelRequested

  #---------------------------------------------------------------------------
  def setStatus(self, statusText):
    logging.info(statusText)
    if self.statusCallback:
      self.statusCallback(statusText)
      slicer.app.processEvents()

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
    releases = [self.legacyReleaseName]
    for releaseRevision in releasesRevisions:
      releases.append(releaseRevision[0])
      releases.append(releaseRevision[0]+"-nightly")
    releases.append(self.unknownReleaseName)
    return releases

  #---------------------------------------------------------------------------
  def getSlicerReleaseName(self, revision):
      """Return Slicer release name that corresponds to a Slicer revision.
      Downloads associated with nightly build happening between release A and B are
      associated with A-nightly "release".
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
          release = releaseRevision[0] + "-nightly"

      return release

  #---------------------------------------------------------------------------
  def _call_midas_url(self, url, data):
      url_values = urllib.urlencode(data)
      full_url = url + '?' + url_values
      response = urllib2.urlopen(full_url)
      response_read = response.read()
      response_dict = json.loads(response_read)
      response_data = response_dict['data']
      return response_data

  #---------------------------------------------------------------------------
  def getExtensionListByName(self, url, extensionName, release=None):
      """By default, return list of all extensions with ``extensionName``.
      """
      method = 'midas.slicerpackages.extension.list'
      codebase = 'Slicer4'
      data = {'method': method, 'codebase': codebase, 'productname': extensionName}
      slicer_revision = None
      if release is not None:
          releases = self.getSlicerReleasesRevisions()
          if release in releases:
              slicer_revision = releases[release]
      if slicer_revision is not None:
          data['slicer_revision'] = slicer_revision
      return self._call_midas_url(url, data)

  #---------------------------------------------------------------------------
  def getExtensionById(self, url, extensionId):
      """Return property associated with extension identified by ``extensionId``.
      """
      method = 'midas.slicerpackages.extension.list'
      codebase = 'Slicer4'
      data = {'method': method, 'codebase': codebase, 'extension_id': extensionId}
      extensions = self._call_midas_url(url, data)
      if len(extensions) > 0:
          return extensions[0]
      else:
          return []

  #---------------------------------------------------------------------------
  def getItemById(self, url, itemId):
      """Return property associated with item identified by ``itemId``.
      """
      method = 'midas.item.get'
      data = {'method': method, 'id': itemId}
      return self._call_midas_url(url, data)

  #---------------------------------------------------------------------------
  def getExtensionSlicerRevisionAndDownloads(self, url, extensionName):
      """Return a dictionary of slicer revision and download counts for
      the given ``extensionName``.
      """
      self.setStatus("Collecting list of packages for extension '{0}'".format(extensionName))
      all_itemids = [(ext['item_id'], ext['extension_id']) for ext in self.getExtensionListByName(url, extensionName)]

      item_rev_downloads = {}
      sampling_step = int(1.0/self.package_sampling_ratio)
      # Collecting `slicer_revision` and `download` for 'extension_id' / 'item_id' pair
      for (idx, (itemid, extensionid)) in enumerate(all_itemids):

          # If statistical sampling is used and we are not at a sampling step then just
          # reuse the previous sample value.
          if self.package_sampling_ratio < 1.0 and (idx % sampling_step != 0):
            item_rev_downloads[itemid] = last_rev_download
            continue

          querySuccess = False
          remainingRetryAttempts = 10
          for i in xrange(remainingRetryAttempts):
              try:
                  item_rev_downloads[itemid] = [self.getItemById(url, itemid)['download'], self.getExtensionById(url, extensionid)['slicer_revision']]
              except urllib2.URLError as e:
                  self.setStatus("Retrieving package info {0}/{1} for extension {2} - Query error({3}): {4} - ".format(idx+1, len(all_itemids), extensionName, e.errno, e.strerror))
                  time.sleep(3*i) # wait progressively more after each failure
              else:
                  querySuccess = True
                  last_rev_download = item_rev_downloads[itemid]
                  break
          self.setStatus("Retrieving package info {0}/{1} for extension {2}: rev {3} downloaded {4} times (midas itemid: {5})".
                            format(idx+1, len(all_itemids), extensionName, item_rev_downloads[itemid][1], item_rev_downloads[itemid][0], itemid))

          if self.getCancelRequested():
            break

      self.setStatus("Consolidating `download` by 'slicer_revision' for extension {0}".format(extensionName))
      rev_downloads = {}
      for (itemid, downloads_rev) in item_rev_downloads.iteritems():
          downloads = int(downloads_rev[0])
          rev = downloads_rev[1]
          if downloads == 0:
              continue
          if rev not in rev_downloads:
              rev_downloads[rev] = downloads
          else:
              rev_downloads[rev] += downloads

      # Order the items based on revision
      sorted_rev_downloads = collections.OrderedDict(sorted(rev_downloads.items(), key=lambda t: t[0]))

      return sorted_rev_downloads

  #---------------------------------------------------------------------------
  def getExtensionDownloadStatsByReleaseName(self, extension_slicer_revision_downloads):
      """Given a dictionary of slicer_revision and download counts, this function
      return a dictionary release and download counts.
      Downloads associated with nightly build happening between release A and B are
      associated with A-nightly "release".
      """

      # Create ordered, complete list of all releases and corresponding download counts
      release_downloads = collections.OrderedDict()
      releases = self.getSlicerReleaseNames()
      for release in releases:
          release_downloads[release] = 0

      # Accumulate download counts
      for (revision, downloads) in extension_slicer_revision_downloads.iteritems():
          release = self.getSlicerReleaseName(revision)
          release_downloads[release] += downloads

      return release_downloads

  #---------------------------------------------------------------------------
  def getExtensionDownloadStats(self, extensionName, url = None):
      """Return download stats associated with ``extensionName``.
      """

      if url is None:
        url = self.getDefaultMidasJsonQueryUrl()

      extensionName.strip() # trim whitespace

      self.setStatus("Retrieving '{0}' extension download statistics from '{1}' server".format(extensionName, url))
      rev_downloads = self.getExtensionSlicerRevisionAndDownloads(url, extensionName)
      self.setStatus("Grouping download statistics by release name")
      extensionDownloadStatsByRelease = self.getExtensionDownloadStatsByReleaseName(rev_downloads)
      self.setStatus('Cancelled.' if self.getCancelRequested() else 'Done.')
      return extensionDownloadStatsByRelease

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
    logic.package_sampling_ratio = 0.01 # Query every 100th statistics package
    release_downloads = logic.getExtensionDownloadStats("SlicerRT")
    print(repr(release_downloads))
    self.assertTrue(len(release_downloads)>0)

    self.delayDisplay('Test passed!')

def main(argv):
  import argparse, json, csv

  parser = argparse.ArgumentParser(description="Slicer Extensions download statistics query tool")
  parser.add_argument('-e', '--extensions', dest="extensionsList", required=False, help="Extension(s) to be queried. If more than one, separate by comma. If not specified, all extensions will be queried.")
  parser.add_argument('-j', '--output-json', dest="jsonName", required=False, help="Name of the output JSON file to store the results.")
  parser.add_argument('-c', '--output-csv', dest="csvName", required=False, help="Name of the output JSON file to store the results.")

  args = parser.parse_args(argv)

  logic = ExtensionStatsLogic()

  if args.extensionsList is None:
    extensionsList = logic.getExtensionNames()
  else:
    extensionsList = args.extensionsList.split(',')
  
  releases = logic.getSlicerReleaseNames()

  csvWriter = None
  if args.csvName:
    csvFile = open(args.csvName, 'wb')
    csvWriter = csv.writer(csvFile, delimiter=',')
    csvWriter.writerow(['Extension name']+releases)

  allStats = {}

  for extensionName in extensionsList:

    release_downloads = logic.getExtensionDownloadStats(extensionName)

    allStats[extensionName] = release_downloads

    if csvWriter:
      extensionStats = [extensionName]
      for release in releases:
        if release in release_downloads:
          extensionStats = extensionStats+[release_downloads[release]]
        else:
          extensionStats = extensionStats+['0']
      csvWriter.writerow(extensionStats)

  if args.jsonName:
    jsonStats = json.dumps(allStats, indent=2)
    with open(args.jsonName, 'w') as jsonFile:
      jsonFile.write(jsonStats)

  sys.exit(0)


if __name__ == "__main__":
  main(sys.argv[1:])
