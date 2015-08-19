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

    self.extensionNameEdit = qt.QLineEdit()
    self.extensionNameEdit.setText('')
    parametersFormLayout.addRow("Extension name: ", self.extensionNameEdit)

    self.midasQueryUrlEdit = qt.QLineEdit()
    self.midasQueryUrlEdit.setText('http://slicer.kitware.com/midas3/api/json')
    parametersFormLayout.addRow("MIDAS json query URL: ", self.midasQueryUrlEdit)
    
    self.applyButton = qt.QPushButton("Get download statistics")
    self.applyButton.toolTip = "Get download statistics"
    parametersFormLayout.addRow(self.applyButton)

    self.statusText = qt.QLabel()
    parametersFormLayout.addRow("Status:", self.statusText)
    
    # Stats table
    self.statsTable = qt.QTableWidget()
    self.statsTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
    parametersFormLayout.addRow("Statistics:", self.statsTable)
    self.statsTableHeader = ['Revision', 'Downloads']
    policy = qt.QSizePolicy()
    policy.setVerticalStretch(1)
    policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
    policy.setVerticalPolicy(qt.QSizePolicy.Expanding)
    self.statsTable.setSizePolicy(policy)

    # Copy to clipboard button
    self.copyToClipboardButton = qt.QPushButton("Copy table to clipboard")
    parametersFormLayout.addRow('', self.copyToClipboardButton)    
    
    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.copyToClipboardButton.connect('clicked()', self.copyTableToClipboard)

    # Add vertical spacer
    #self.layout.addStretch(1)

  def cleanup(self):
    pass

  def onApplyButton(self):
  
    if self.queryInProgress:
      self.logic.setCancelRequested(True)
      self.applyButton.setText("Cancelling...")
      self.applyButton.enabled = False
      slicer.app.processEvents()
      return
    
    self.clearStatsTable()
    
    self.applyButton.setText("Cancel")    
    self.queryInProgress = True
    slicer.app.processEvents()
    
    #release_downloads = slicer.stats
    
    release_downloads = self.logic.getExtensionDownloadStats(self.midasQueryUrlEdit.text, self.extensionNameEdit.text)
    #slicer.stats = release_downloads # save results -- only for testing

    self.queryInProgress = False
    self.logic.setCancelRequested(False)
    self.applyButton.setText("Get download statistics")
    self.applyButton.enabled = True

    self.updateStatsTable(release_downloads)
    
  def clearStatsTable(self):
    self.statsTable.clear()
    self.statsTable.setRowCount( 0 )
    self.statsTable.setColumnCount( 0 )
    
  def updateStatsTable(self, release_downloads):
    self.statsTable.setRowCount(len(release_downloads));
    self.statsTable.setColumnCount(len(self.statsTableHeader));
    self.statsTable.setHorizontalHeaderLabels(self.statsTableHeader)
    
    self.items = []
    row = 0
    for release, downloads in release_downloads.items():    
      item = qt.QTableWidgetItem(release)
      self.items.append(item) # required, otherwise the item does not appear
      item.setFlags(item.flags() ^ qt.Qt.ItemIsEditable) # make the item read-only
      self.statsTable.setItem(row,0,item)
      item = qt.QTableWidgetItem(str(downloads))
      self.items.append(item) # required, otherwise the item does not appear
      item.setFlags(item.flags() ^ qt.Qt.ItemIsEditable) # make the item read-only
      self.statsTable.setItem(row,1,item)
      row = row + 1
  
    self.statsTable.horizontalHeader().setResizeMode(qt.QHeaderView.Stretch)    
    
  def copyTableToClipboard(self):
    tableText = '\t'.join(self.statsTableHeader) # convert list to tab-separated string
    for rowIndex in xrange(self.statsTable.rowCount):
      tableText += '\n'
      for columnIndex in xrange(self.statsTable.columnCount):
        if columnIndex>0:
          tableText += '\t'
        tableText += self.statsTable.item(rowIndex,columnIndex).text()
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

  def setStatusCallback(self, callbackMethod):
    self.statusCallback = callbackMethod

  def setCancelRequested(self, cancelRequested):
    self.cancelRequested = cancelRequested
    
  def getCancelRequested(self):
    slicer.app.processEvents() # get a chance of button presses to be processed
    return self.cancelRequested
    
  def setStatus(self, statusText):
    logging.info(statusText)
    if self.statusCallback:
      self.statusCallback(statusText)
      slicer.app.processEvents()
  
  #---------------------------------------------------------------------------
  def getSlicerReleases(self):
      """Return dictionary of Slicer release and associated Slicer revision.
      The list of revision for each release is reported here:
        http://wiki.slicer.org/slicerWiki/index.php/Release_Details
      """
      return {
          '4.0.0' : '18777',
          '4.0.1' : '19033',
          '4.1.0' : '19886',
          '4.1.1' : '20313',
          '4.2.0' : '21298',
          '4.2.1' : '21438',
          '4.2.2' : '21508',
          '4.2.2-1' : '21513',
          '4.3.0' : '22408',
          '4.3.1' : '22599',
          '4.3.1-1' : '22704',
          '4.4.0' : '23774'
      }

  #---------------------------------------------------------------------------
  def getSlicerRevision(self, release):
      """Return Slicer revision that corresponds to a Slicer release.
      Otherwise, return ``None``.
      """
      releases = self.getSlicerReleases()
      if release not in releases:
          return None
      return releases[release]

  #---------------------------------------------------------------------------
  def getSlicerRevisions(self):
      return {y:x for x,y in self.getSlicerReleases().iteritems()}

  #---------------------------------------------------------------------------
  def getSlicerRelease(self, revision):
      """Return Slicer release that corresponds to a Slicer revision.
      Otherwise, return ``None``.
      """
      revisions = self.getSlicerRevisions()
      if revision not in revisions:
          return None
      return revisions[revision]

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
          slicer_revision = self.getSlicerRevision(release)
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
      self.setStatus("Collecting 'extension_id' / 'item_id' pair matching '{0}' name".format(extensionName))
      all_itemids = [(ext['item_id'], ext['extension_id']) for ext in self.getExtensionListByName(url, extensionName)]

      item_rev_downloads = {}
      self.setStatus("Collecting `slicer_revision` and `download` for 'extension_id' / 'item_id' pair")
      for (idx, (itemid, extensionid)) in enumerate(all_itemids):
          self.setStatus("Retrieving package info {0}/{1}".format(idx+1, len(all_itemids)))
          querySuccess = False
          remainingRetryAttempts = 10
          for i in xrange(remainingRetryAttempts):
              try:
                  item_rev_downloads[itemid] = [self.getItemById(url, itemid)['download'], self.getExtensionById(url, extensionid)['slicer_revision']]
              except urllib2.URLError as e:
                  self.setStatus("Retrieving package info {0}/{1} - Query error({2}): {3} - ".format(idx+1, len(all_itemids), e.errno, e.strerror))
                  time.sleep(3*i) # wait progressively more after each failure
              else:
                  querySuccess = True
                  break
          if self.getCancelRequested():
            break

      self.setStatus("Consolidating `download` by 'slicer_revision'")
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
  def getExtensionDownloadStatsByRelease(self, extension_slicer_revision_downloads):
      """Given a dictionary of slicer_revision and download counts, this function
      return a dictionary release and download counts.
      Downloads associated with nightly build happening between release A and B are
      associated with A-nightly "release".
      """
      post_release = None
      pre_release_downloads = 0
      release_downloads = collections.OrderedDict()
      for (revision, downloads) in extension_slicer_revision_downloads.iteritems():
          release = self.getSlicerRelease(revision)
          if release:
              release_downloads[release] = downloads
              post_release = release + '-nightly'
          else:
              if post_release is not None:
                  if post_release not in release_downloads:
                      release_downloads[post_release] = downloads
                  else:
                      release_downloads[post_release] += downloads
              else:
                  pre_release_downloads += downloads

      if pre_release_downloads==0:
        return release_downloads

      release_downloads_with_pre = collections.OrderedDict() # need to create a new dict to prepend an item
      releases = self.getSlicerReleases().keys()
      releases_index = releases.index(release_downloads.keys()[0]) - 1
      if releases_index>=0 and releases_index<len(releases):
        release_for_pre_release = releases[releases_index]
        release_downloads_with_pre[release_for_pre_release + '-nightly'] = pre_release_downloads
      else:
        release_downloads_with_pre['pre-releases-nightly'] = pre_release_downloads
      release_downloads_with_pre.update(release_downloads) # append existing items

      return release_downloads_with_pre

  #---------------------------------------------------------------------------
  def getExtensionDownloadStats(self, url, extensionName):
      """Return download stats associated with ``extensionName``.
      """
      self.setStatus("Retrieving '{0}' extension download statistics from '{1}' server".format(extensionName, url))
      rev_downloads = self.getExtensionSlicerRevisionAndDownloads(url, extensionName)
      self.setStatus("Grouping `download` by 'release'")
      extensionDownloadStatsByRelease = self.getExtensionDownloadStatsByRelease(rev_downloads)
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
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = ExtensionStatsLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
