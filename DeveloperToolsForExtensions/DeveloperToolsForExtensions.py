import os
import unittest
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# ManualExtensionInstaller
#

class ManualExtensionInstaller(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Manual Extension Installer"
        self.parent.categories = ["Developer Tools"]
        self.parent.dependencies = []
        self.parent.contributors = ["Francois Budin (UNC)"] # replace with "Firstname Lastname (Organization)"
        self.parent.helpText = """
    This extension allows to install an extension directly from an archive (*.zip or *.tar.gz). \
    This is useful to verify that your extension has been correctly packaged. This is also useful if \
    one wants to distribute their extensions through their personal website.
    """
        self.parent.acknowledgementText = """
    This work is supported by NA-MIC and the Slicer Community. See <a>http://www.slicer.org</a> for details.
"""

#
# ManualExtensionInstallerWidget
#
class ManualExtensionInstallerWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.fileDialog = None
        icon = self.parent.style().standardIcon(qt.QStyle.SP_ArrowForward)
        iconSize = qt.QSize(22, 22)
        def createToolButton(text):
            tb = qt.QToolButton()

            tb.text = text
            tb.icon = icon

            font = tb.font
            font.setBold(True)
            font.setPixelSize(14)
            tb.font = font

            tb.iconSize = iconSize
            tb.toolButtonStyle = qt.Qt.ToolButtonTextBesideIcon
            tb.autoRaise = True

            return tb
        # Instantiate and connect widgets ...

        #
        # Parameters Area
        #
        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Manual Extension Installer"
        self.layout.addWidget(parametersCollapsibleButton)

        # Layout within the dummy collapsible button
        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        # Select extension

        self.extensionSelector = createToolButton("Select extension archive")
        self.extensionSelector.setToolTip("Select extension archive that has been locally created or manually downloaded")
        parametersFormLayout.addRow(self.extensionSelector)

        # connections
        self.extensionSelector.connect('clicked(bool)', self.onSelect)

        # Add vertical spacer
        self.layout.addStretch(1)

        # Create logic
        self.logic=ManualExtensionInstallerLogic()

    def cleanup(self):
        pass

    def onSelect(self):
        if not self.fileDialog:
            self.fileDialog = qt.QFileDialog(self.parent)
            self.fileDialog.options = self.fileDialog.DontUseNativeDialog
            self.fileDialog.acceptMode = self.fileDialog.AcceptOpen
            self.fileDialog.setNameFilter("Extension archive (*.zip *.tar.gz)")
            self.fileDialog.setLabelText( qt.QFileDialog.Accept,"Install" )
            self.fileDialog.setWindowTitle("Select extension to install")
            self.fileDialog.connect("fileSelected(QString)", self.onFileSelected)
        self.fileDialog.show()

    def onFileSelected(self,fileName):
        self.fileDialog.hide()
        if self.logic.run(fileName):
            value=qt.QMessageBox.question(slicer.util.mainWindow(),"",
                                          "Are you sure you want to restart?",qt.QMessageBox.Ok|qt.QMessageBox.No)
            #http://qt-project.org/doc/qt-4.8/qmessagebox.html#StandardButton-enum
            if value == qt.QMessageBox.Ok:
                slicer.util.restart()
        else:
            qt.QMessageBox.critical(slicer.util.mainWindow(),"",
                                    "Error during installation. Verify log messages. The extension may already be install")
#
# ManualExtensionInstallerLogic
#

class ManualExtensionInstallerLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """
    def PlatformCheck(self,filename):
        """Compare extension platform with current platform.
        """
        name=os.path.basename(filename)
        extensionrepositoryRevision,extensionos,extensionarch=name.split('-')[:3]
        for var in ('repositoryRevision','os','arch'):
            currentVar=getattr(slicer.app,var)
            extensionVar=locals()['extension'+var]
            if extensionVar != currentVar:
                logging.error(var+": "+currentVar+"(Slicer) "+extensionVar+"(extension)")
                return False
        return True

    #http://stackoverflow.com/questions/17277566/check-os-path-isfilefilename-with-case-sensitive-in-python
    def CheckFileExistsCaseSensitive(self,filename):
        """Verifies that the given file exists. Default python function to do so (\
        os.path.isfile(filename) ) is not case-sensitive.
        """
        if not os.path.isfile(filename):
            return False   # exit early, file does not exist (not even with wrong case)
        directory, filename = os.path.split(filename)
        return filename in os.listdir(directory)

    def run(self, filename):
        """
        Install a given extension, from an archive, in Slicer
        """
        if not self.CheckFileExistsCaseSensitive(filename):
            slicer.util.errorDisplay('Extension file does not exist')
            return False
        if not self.PlatformCheck(filename):
            slicer.util.errorDisplay('Extension file for wrong platform')
            return False
        logging.info('Processing started')
        val=slicer.app.extensionsManagerModel().installExtension(filename)
        logging.info('Processing completed')
        return val


class ManualExtensionInstallerTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def runTest(self):
    #  """Run as few or as many tests as needed here.
    #  """
    #  self.test_ManualExtensionInstaller1()
        self.test_PlatformCheck1()
        self.test_PlatformCheck2()
        self.test_CheckFileExistsCaseSensitive1()
        self.test_CheckFileExistsCaseSensitive2()
        self.test_run()

    def test_PlatformCheck1(self):
        """Verifies that platformCheck() works appropriately if filename with correct platform given.
        """
        testName="PlatformCheck1"
        self.delayDisplay("Starting the test: "+testName)
        absoluteDummyPath="/test/hello"
        dummyExtensionName="myExtension"
        dummyExtensionSuffix="svn224-2014-07-28.tar.gz"#Extension does not matter for this test
        myCurrentOS=slicer.app.os
        myCurrentArch=slicer.app.arch
        myCurrentRev=slicer.app.repositoryRevision
        myFileName="-".join([myCurrentRev,myCurrentOS,myCurrentArch,
                             dummyExtensionName,dummyExtensionSuffix])
        myAbsoluteFileName="/".join([absoluteDummyPath,myFileName])
        logging.info("Check platform with given dummy file name:%s", myAbsoluteFileName)
        logic = ManualExtensionInstallerLogic()
        self.assertTrue( logic.PlatformCheck(myAbsoluteFileName) )
        self.delayDisplay(testName+': Test passed!')

    def test_PlatformCheck2(self):
        """Verifies that plafformCheck() returns errors when the given file
        does not correspond to the current platform. Tests with wrong OS, wrong architecture
        and wrong revision number.
        """
        testName="PlateformCheck2"
        self.delayDisplay("Starting the test: "+testName)
        absoluteDummyPath="/test/hello"
        dummyExtensionName="myExtension"
        dummyExtensionSuffix="svn224-2014-07-28.tar.gz"#Extension does not matter for this test
        myCurrentOS=slicer.app.os
        myCurrentArch=slicer.app.arch
        myCurrentRev=slicer.app.repositoryRevision
        logic = ManualExtensionInstallerLogic()
        #check that False is returned for wrong OS
        listOS=['linux','macosx','win']
        listOS.remove(myCurrentOS)
        for testOS in listOS:
            myFileName="-".join([myCurrentRev,testOS,myCurrentArch,
                             dummyExtensionName,dummyExtensionSuffix])
            myAbsoluteFileName="/".join([absoluteDummyPath,myFileName])
            logging.info("Check platform with given dummy file name:%s", myAbsoluteFileName)
            self.assertTrue( not logic.PlatformCheck(myAbsoluteFileName) )
        #Check that False is returned for wrong revision number
        badRev="xxxxx"
        myFileName="-".join([badRev,myCurrentOS,myCurrentArch,
                             dummyExtensionName,dummyExtensionSuffix])
        myAbsoluteFileName="/".join([absoluteDummyPath,myFileName])
        logging.info("Check platform with given dummy file name:%s", myAbsoluteFileName)
        self.assertTrue( not logic.PlatformCheck(myAbsoluteFileName) )
        #Check that False is returned for wrong architecture detected
        badArchitecture="badArch"
        myFileName="-".join([myCurrentRev,myCurrentOS,badArchitecture,
                             dummyExtensionName,dummyExtensionSuffix])
        myAbsoluteFileName="/".join([absoluteDummyPath,myFileName])
        logging.info("Check platform with given dummy file name:%s", myAbsoluteFileName)
        self.assertTrue( not logic.PlatformCheck(myAbsoluteFileName) )
        self.delayDisplay(testName+': Test passed!')

    def test_CheckFileExistsCaseSensitive1(self):
        """Checks that CheckFileExistsCaseSensitive returns False if given file does
        not exist.
        """
        testName="CheckFileExistsCaseSensitive1"
        self.delayDisplay("Starting the test: "+testName)
        logic = ManualExtensionInstallerLogic()
        slicerPath=slicer.app.applicationFilePath()
        fileDoesNotExists=os.path.join(slicerPath,"fileThatDoesntExist")
        logging.info("Check that the given file which does not exist is not found:%s",fileDoesNotExists)
        self.assertTrue( not logic.CheckFileExistsCaseSensitive(fileDoesNotExists) )
        self.delayDisplay(testName+': Test passed!')

    def test_CheckFileExistsCaseSensitive2(self):
        """Checks that CheckFileExistsCaseSensitive returns True if given file exists.
        """
        testName="CheckFileExistsCaseSensitive2"
        self.delayDisplay("Starting the test: "+testName)
        logic = ManualExtensionInstallerLogic()
        slicerPath=slicer.app.applicationFilePath()
        logging.info("Check that the given file is found:%s",slicerPath)
        self.assertTrue( logic.CheckFileExistsCaseSensitive(slicerPath) )
        self.delayDisplay(testName+': Test passed!')

    def _install_dummy_extension(self,myExtensionName):
        logic = ManualExtensionInstallerLogic()
        myCurrentOS=slicer.app.os
        myCurrentArch=slicer.app.arch
        myCurrentRev=slicer.app.repositoryRevision
        #The only archive format we are sure we have is zip, through the python interface.
        #Since this format works on the 3 platforms we support (Windows, MacOS, and linux),
        #we use this format instead of 'tar.gz' on linux and MacOS.
        extenstion=".zip"
        myExtensionFileRootName="-".join([myCurrentRev,myCurrentOS,myCurrentArch,myExtensionName])
        tempPath = slicer.app.temporaryPath
        currentFilePath=os.path.dirname(os.path.realpath(__file__))
        inputDescriptionFile=os.path.join(currentFilePath,"Testing","Python","myDummyExtension.s4ext")
        myCurrentOS=slicer.app.os
        myCurrentVersion=slicer.app.applicationVersion
        versionNoDate=myCurrentVersion.split("-")#Get version number without date
        versionSplit=versionNoDate[0].split(".")#Split major.minor.patch
        #Create a variable containing a string of the form "Slicer-4.4"
        slicerVersionDirectory="Slicer-"+versionSplit[0]+"."+versionSplit[1]
        if myCurrentOS=="macosx":
            internalPackagePath=os.path.join(myExtensionFileRootName,
                                             "Slicer.app","Contents",
                                             "Extensions-"+myCurrentRev,myExtensionName,
                                             "share",slicerVersionDirectory)
        else: # "win" or linux
            internalPackagePath=os.path.join("share",slicerVersionDirectory)
        import errno
        try:
            pathToCreate=os.path.join(tempPath,internalPackagePath)
            logging.info("Directory to create for test extension: "+pathToCreate)
            os.makedirs(pathToCreate)
        except OSError as exception:
            if exception.errno != errno.EEXIST:#We report error except if it is because directory already exists
                logging.critical("Error while creating extension directory in temp folder")
                return False
            logging.info("Extension directory already exists")
        try:
            import shutil
            outputDescriptionFile=os.path.join(pathToCreate,myExtensionName+".s4ext")
            shutil.copyfile(inputDescriptionFile,outputDescriptionFile)
            myExtensionFileName=myExtensionFileRootName+extenstion
            myExtensionInputDirectory=os.path.join(tempPath,myExtensionFileRootName)
            outputExtensionFileName=os.path.join(tempPath,myExtensionFileName)
            logging.info("Output zipped file name:"+outputExtensionFileName)
            logging.info("Directory to zip:"+myExtensionInputDirectory)
            slicer.vtkMRMLApplicationLogic().Zip(outputExtensionFileName,myExtensionInputDirectory)
        except Exception as exception:
            logging.critical(exception)
            return False
        if logic.run(outputExtensionFileName):
            slicer.app.extensionsManagerModel().scheduleExtensionForUninstall(myExtensionName)
            return True
        return False

    def test_run(self):
        """ Downloads and install a fake package. After the installation, is schedule the extension for uninstall
        as it cannot uninstall it right away.
        """
        testName="CheckIfInstallTestExtensionWorks"
        myTestExtension="myTestExtension"
        #In case the extension is already installed, skip test and schedule for removal.
        if slicer.app.extensionsManagerModel().isExtensionInstalled(myTestExtension):
            slicer.app.extensionsManagerModel().scheduleExtensionForUninstall(myTestExtension)
            logging.info("Extension already installed. Scheduled to be removed.")
            self.delayDisplay('Test extension scheduled to be removed. Test skipped. Restart Slicer and run it again.',
                              3000)
            return
        self.delayDisplay("Starting the test: "+testName)
        self.assertTrue( self._install_dummy_extension(myTestExtension) )
        self.delayDisplay(testName+': Test passed!')