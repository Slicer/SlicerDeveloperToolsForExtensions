import os
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# DeveloperToolsForExtensions
#


class DeveloperToolsForExtensions(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Developer Tools For Extensions"
        self.parent.categories = ["Developer Tools"]
        self.parent.dependencies = []
        self.parent.contributors = ["Francois Budin (UNC)"]  # replace with "Firstname Lastname (Organization)"
        self.parent.helpText = """
    This extension gives the developers easy access to convenient functions that are available in Slicer \
    but difficult to access.
    """
        self.parent.acknowledgementText = """
    This work is supported by NA-MIC and the Slicer Community. See <a>http://www.slicer.org</a> for details.
"""

#
# DeveloperToolsForExtensionsWidget
#
class DeveloperToolsForExtensionsWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.timeout = 3000
        self.extensionFileDialog = None
        self.moduleFileDialog = None
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
        parametersCollapsibleButton.text = "Developer tools for extensions"
        self.layout.addWidget(parametersCollapsibleButton)

        # Layout within the dummy collapsible button
        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        # Select extension to install

        self.extensionSelector = createToolButton("Install extension archive")
        self.extensionSelector.setToolTip("Select extension archive that\
                                            has been locally created or manually downloaded")
        parametersFormLayout.addRow(self.extensionSelector)

        # Select script module to load
        self.moduleSelector = createToolButton("Load module")
        self.moduleSelector.setToolTip("Select a module you want to load in Slicer")
        parametersFormLayout.addRow(self.moduleSelector)

        # connections
        self.extensionSelector.connect('clicked(bool)', self.onExtensionSelect)
        self.moduleSelector.connect('clicked(bool)', self.onModuleSelect)

        # Add vertical spacer
        self.layout.addStretch(1)

        # Create logic
        self.logic = DeveloperToolsForExtensionsLogic()

    def cleanup(self):
        pass

    def customDialog(self, filter_name, okCaption, windowTitle ):
        dialog = qt.QFileDialog(self.parent)
        dialog.options = dialog.DontUseNativeDialog
        dialog.acceptMode = dialog.AcceptOpen
        dialog.setNameFilter(filter_name)
        dialog.setLabelText(qt.QFileDialog.Accept, okCaption)
        dialog.setWindowTitle(windowTitle)
        return dialog

    def onModuleSelect(self):
        if not self.moduleFileDialog:
            self.moduleFileDialog = self.customDialog("Script module (*.py)", "Load", "Select module to load")
            self.moduleFileDialog.connect("fileSelected(QString)", self.onModuleFileSelected)
        self.moduleFileDialog.show()

    def onModuleFileSelected(self, fileName):
        self.moduleFileDialog.hide()
        value = qt.QMessageBox.question(slicer.util.mainWindow(), "",
                                      "Do you want to add module path to permanent search paths?",
                                      qt.QMessageBox.Yes | qt.QMessageBox.No)
        permanent = False
        if value == qt.QMessageBox.Yes:
            permanent = True
        try:
            self.logic.addModule(fileName,permanent)
            slicer.util.delayDisplay("Module "+fileName+" loaded", self.timeout)
        except Exception as e:
            logging.critical(e.message)
            slicer.util.errorDisplay(e.message, self.timeout)

    def onExtensionSelect(self):
        if not self.extensionFileDialog:
            self.extensionFileDialog = self.customDialog("Extension archive (*.zip *.tar.gz)",
                                                         "Install", "Select extension to install")
            self.extensionFileDialog.connect("fileSelected(QString)", self.onExtensionFileSelected)
        self.extensionFileDialog.show()

    def onExtensionFileSelected(self, fileName):
        self.extensionFileDialog.hide()
        try:
            self.logic.installExtension(fileName)
            value=qt.QMessageBox.question(slicer.util.mainWindow(), "",
                                          "Are you sure you want to restart?", qt.QMessageBox.Ok | qt.QMessageBox.No)
            # http://qt-project.org/doc/qt-4.8/qmessagebox.html#StandardButton-enum
            if value == qt.QMessageBox.Ok:
                slicer.util.restart()
        except Exception as e:
            slicer.util.errorDisplay(e.message, self.timeout)
#
# DeveloperToolsForExtensionsLogic
#


class DeveloperToolsForExtensionsLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """
    def PlatformCheck(self, filename):
        """Compare extension platform with current platform.
        """
        name = os.path.basename(filename)
        try:
          extensionrepositoryRevision, extensionos, extensionarch = name.split('-')[:3]
        except:
            raise Exception('extension name does not match expected format \
                            (Revision-OS-Arch-NameAndExtension)')
        for var in ('repositoryRevision', 'os', 'arch'):
            currentVar = getattr(slicer.app, var)
            extensionVar = locals()['extension'+var]
            if extensionVar != currentVar:
                raise Exception(var+": "+currentVar+"(Slicer) "+extensionVar+"(extension)")
        return True

    # http://stackoverflow.com/questions/17277566/check-os-path-isfilefilename-with-case-sensitive-in-python
    def CheckFileExistsCaseSensitive(self, filename):
        """Verifies that the given file exists. Default python function to do so (\
        os.path.isfile(filename) ) is not case-sensitive.
        """
        if not os.path.isfile(filename):
            return False   # exit early, file does not exist (not even with wrong case)
        directory, filename = os.path.split(filename)
        return filename in os.listdir(directory)

    def installExtension(self, filename):
        """
        Install a given extension, from an archive, in Slicer
        """
        try:
            self.CheckFileExistsCaseSensitive(filename)
        except:
            raise Exception('Extension file does not exist')
        try:
            self.PlatformCheck(filename)
        except:
            raise Exception('Extension file for wrong platform')
        logging.info('Extension installation process started')
        val = slicer.app.extensionsManagerModel().installExtension(filename)
        logging.info('Extension installation process completed')
        return val

    # From ExtensionWizard.py in Slicer
    def _settingsList(self, settings, key):
        """
        Returns a settings value as a list (even if empty or a single value)
        """

        value = settings.value(key)

        if isinstance(value, basestring):
            return [value]

        return [] if value is None else value

    # From ExtensionWizard.py in Slicer
    def addModule(self, fileName, permanent):
        """
        Loads a module in the Slicer factory while Slicer is running
        """
        logging.info('Module addition process started')
        # Determine which modules in above are not already loaded
        factory = slicer.app.moduleManager().factoryManager()
        myModule = type('moduleType', (), {})
        myModule.dirPath = os.path.dirname(fileName)
        myModule.baseName = os.path.basename(fileName)
        myModule.key, myModule.fileExtension = os.path.splitext(myModule.baseName)
        if factory.isLoaded(myModule.key):
            raise Exception("Abort: Module already loaded")
        if permanent:
            # Add module(s) to permanent search paths, if requested
            settings = slicer.app.revisionUserSettings()
            rawSearchPaths = list(self._settingsList(settings, "Modules/AdditionalPaths"))
            searchPaths = [qt.QDir(path) for path in rawSearchPaths]

            modified = False
            rawPath = myModule.dirPath
            path = qt.QDir(rawPath)
            if path not in searchPaths:
                searchPaths.append(path)
                rawSearchPaths.append(rawPath)
                modified = True

            if modified:
                settings.setValue("Modules/AdditionalPaths", rawSearchPaths)

        # Register requested module(s)
        factory.registerModule(qt.QFileInfo(fileName))
        if not factory.isRegistered(myModule.key):
            raise Exception("Abort: Failed to register module %s", myModule.key)

        # Instantiate and load requested module(s)
        if not factory.loadModules([myModule.key]):
            raise Exception("Abort: The module factory manager reported an error. \
                     One or more of the requested module(s) and/or \
                     dependencies thereof may not have been loaded.")
        logging.info('Module addition process completed')
        return True


class DeveloperToolsForExtensionsTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def runTest(self):
        # """Run as few or as many tests as needed here.
        # """
        self.test_PlatformCheck1()
        self.test_PlatformCheck2()
        self.test_CheckFileExistsCaseSensitive1()
        self.test_CheckFileExistsCaseSensitive2()
        self.test_installExtension()

    def test_PlatformCheck1(self):
        """Verifies that platformCheck() works appropriately if filename with correct platform given.
        """
        testName = "PlatformCheck1"
        self.delayDisplay("Starting the test: "+testName)
        absoluteDummyPath = "/test/hello"
        dummyExtensionName = "myExtension"
        dummyExtensionSuffix = "svn224-2014-07-28.tar.gz"  # Extension does not matter for this test
        myCurrentOS = slicer.app.os
        myCurrentArch = slicer.app.arch
        myCurrentRev = slicer.app.repositoryRevision
        myFileName = "-".join([myCurrentRev, myCurrentOS, myCurrentArch,
                              dummyExtensionName, dummyExtensionSuffix])
        myAbsoluteFileName = "/".join([absoluteDummyPath, myFileName])
        logging.info("Check platform with given dummy file name:%s", myAbsoluteFileName)
        logic = DeveloperToolsForExtensionsLogic()
        self.assertTrue(logic.PlatformCheck(myAbsoluteFileName))
        self.delayDisplay(testName+': Test passed!')

    def test_PlatformCheck2(self):
        """Verifies that plafformCheck() raises exceptions when the given file
        does not correspond to the current platform. Tests with wrong OS, wrong architecture
        and wrong revision number.
        """
        testName = "PlatformCheck2"
        self.delayDisplay("Starting the test: "+testName)
        absoluteDummyPath = "/test/hello"
        dummyExtensionName = "myExtension"
        dummyExtensionSuffix = "svn224-2014-07-28.tar.gz"  # Extension does not matter for this test
        myCurrentOS = slicer.app.os
        myCurrentArch = slicer.app.arch
        myCurrentRev = slicer.app.repositoryRevision
        logic = DeveloperToolsForExtensionsLogic()
        # check that an exception is raised for wrong OS
        listOS = ['linux', 'macosx', 'win']
        listOS.remove(myCurrentOS)
        for testOS in listOS:
            myFileName = "-".join([myCurrentRev, testOS, myCurrentArch,
                                  dummyExtensionName, dummyExtensionSuffix])
            myAbsoluteFileName = "/".join([absoluteDummyPath,myFileName])
            logging.info("Check platform with given dummy file name:%s", myAbsoluteFileName)
            with self.assertRaises(Exception) as cm:
              logic.PlatformCheck(myAbsoluteFileName)
            e = cm.exception
            self.assertEqual(e.message, "os: "+myCurrentOS+"(Slicer) "+testOS+"(extension)")
        # Check that False is returned for wrong revision number
        badRev = "xxxxx"
        myFileName = "-".join([badRev, myCurrentOS, myCurrentArch,
                               dummyExtensionName, dummyExtensionSuffix])
        myAbsoluteFileName = "/".join([absoluteDummyPath, myFileName])
        logging.info("Check platform with given dummy file name:%s", myAbsoluteFileName)
        with self.assertRaises(Exception) as cm:
          logic.PlatformCheck(myAbsoluteFileName)
        e = cm.exception
        self.assertEqual(e.message, "repositoryRevision: "+myCurrentRev+"(Slicer) "+badRev+"(extension)")
        # Check that False is returned for wrong architecture detected
        badArchitecture = "badArch"
        myFileName = "-".join([myCurrentRev, myCurrentOS, badArchitecture,
                              dummyExtensionName, dummyExtensionSuffix])
        myAbsoluteFileName = "/".join([absoluteDummyPath, myFileName])
        logging.info("Check platform with given dummy file name:%s", myAbsoluteFileName)
        with self.assertRaises(Exception) as cm:
          logic.PlatformCheck(myAbsoluteFileName)
        e = cm.exception
        self.assertEqual(e.message, "arch: "+myCurrentArch+"(Slicer) "+badArchitecture+"(extension)")
        self.delayDisplay(testName+': Test passed!')

    def test_CheckFileExistsCaseSensitive1(self):
        """Checks that CheckFileExistsCaseSensitive returns False if given file does
        not exist.
        """
        testName = "CheckFileExistsCaseSensitive1"
        self.delayDisplay("Starting the test: "+testName)
        logic = DeveloperToolsForExtensionsLogic()
        slicerPath = slicer.app.applicationFilePath()
        fileDoesNotExists = os.path.join(slicerPath, "fileThatDoesntExist")
        logging.info("Check that the given file which does not exist is not found:%s", fileDoesNotExists)
        self.assertTrue(not logic.CheckFileExistsCaseSensitive(fileDoesNotExists))
        self.delayDisplay(testName+': Test passed!')

    def test_CheckFileExistsCaseSensitive2(self):
        """Checks that CheckFileExistsCaseSensitive returns True if given file exists.
        """
        testName = "CheckFileExistsCaseSensitive2"
        self.delayDisplay("Starting the test: "+testName)
        logic = DeveloperToolsForExtensionsLogic()
        slicerPath = slicer.app.applicationFilePath()
        logging.info("Check that the given file is found:%s", slicerPath)
        self.assertTrue(logic.CheckFileExistsCaseSensitive(slicerPath))
        self.delayDisplay(testName+': Test passed!')

    def _install_dummy_extension(self, myExtensionName):
        logic = DeveloperToolsForExtensionsLogic()
        myCurrentOS = slicer.app.os
        myCurrentArch = slicer.app.arch
        myCurrentRev = slicer.app.repositoryRevision
        # The only archive format we are sure we have is zip, through the python interface.
        # Since this format works on the 3 platforms we support (Windows, MacOS, and linux),
        # we use this format instead of 'tar.gz' on linux and MacOS.
        extenstion = ".zip"
        myExtensionFileRootName = "-".join([myCurrentRev, myCurrentOS, myCurrentArch, myExtensionName])
        tempPath = slicer.app.temporaryPath
        currentFilePath = os.path.dirname(os.path.realpath(__file__))
        inputDescriptionFile = os.path.join(currentFilePath, "Testing", "Python", "myDummyExtension.s4ext")
        myCurrentOS = slicer.app.os
        myCurrentVersion = slicer.app.applicationVersion
        versionNoDate = myCurrentVersion.split("-")  # Get version number without date
        versionSplit = versionNoDate[0].split(".")  # Split major.minor.patch
        # Create a variable containing a string of the form "Slicer-4.4"
        slicerVersionDirectory = "Slicer-"+versionSplit[0]+"."+versionSplit[1]
        if myCurrentOS == "macosx":
            internalPackagePath = os.path.join(myExtensionFileRootName,
                                               "Slicer.app", "Contents",
                                               "Extensions-"+myCurrentRev, myExtensionName,
                                               "share", slicerVersionDirectory)
        else:  # "win" or linux
            internalPackagePath = os.path.join(myExtensionFileRootName,"share", slicerVersionDirectory)
        import errno
        try:
            pathToCreate = os.path.join(tempPath, internalPackagePath)
            logging.info("Directory to create for test extension: "+pathToCreate)
            os.makedirs(pathToCreate)
        except OSError as exception:
            if exception.errno != errno.EEXIST:  # We report error except if it is because directory already exists
                logging.critical("Error while creating extension directory in temp folder")
                return False
            logging.info("Extension directory already exists")
        try:
            import shutil
            outputDescriptionFile = os.path.join(pathToCreate, myExtensionName+".s4ext")
            shutil.copyfile(inputDescriptionFile, outputDescriptionFile)
            myExtensionFileName = myExtensionFileRootName+extenstion
            myExtensionInputDirectory = os.path.join(tempPath, myExtensionFileRootName)
            outputExtensionFileName = os.path.join(tempPath, myExtensionFileName)
            logging.info("Output zipped file name:"+outputExtensionFileName)
            logging.info("Directory to zip:"+myExtensionInputDirectory)
            slicer.vtkMRMLApplicationLogic().Zip(outputExtensionFileName, myExtensionInputDirectory)
        except Exception as exception:
            logging.critical(exception)
            return False
        if logic.installExtension(outputExtensionFileName):
            slicer.app.extensionsManagerModel().scheduleExtensionForUninstall(myExtensionName)
            return True
        return False

    def test_installExtension(self):
        """ Downloads and install a fake package. After the installation, is schedule the extension for uninstall
        as it cannot uninstall it right away.
        """
        testName = "CheckIfInstallTestExtensionWorks"
        myTestExtension = "myTestExtension"
        # In case the extension is already installed, skip test and schedule for removal.
        if slicer.app.extensionsManagerModel().isExtensionInstalled(myTestExtension):
            slicer.app.extensionsManagerModel().scheduleExtensionForUninstall(myTestExtension)
            logging.info("Extension already installed. Scheduled to be removed.")
            self.delayDisplay('Test extension scheduled to be removed. Test skipped. Restart Slicer and run it again.',
                              3000)
            return
        self.delayDisplay("Starting the test: "+testName)
        self.assertTrue(self._install_dummy_extension(myTestExtension))
        self.delayDisplay(testName+': Test passed!')