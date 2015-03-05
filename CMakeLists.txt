cmake_minimum_required(VERSION 2.8.9)

project(DeveloperToolsForExtensions)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://www.slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/DeveloperToolsForExtensions")
set(EXTENSION_CATEGORY "Developer Tools")
set(EXTENSION_CONTRIBUTORS "Francois Budin (UNC)")
set(EXTENSION_DESCRIPTION "This extension allows to install extension directly from a file")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/fbudin69500/SlicerDeveloperToolsForExtensions/master/DeveloperToolsForExtensions/Resources/Icons/DeveloperToolsForExtensions.png")
set(EXTENSION_SCREENSHOTURLS "http://www.slicer.org/slicerWiki/images/5/54/SlicerExtension-SlicerDeveloperToolsForExtensions-Screenshot.png")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(DeveloperToolsForExtensions)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
