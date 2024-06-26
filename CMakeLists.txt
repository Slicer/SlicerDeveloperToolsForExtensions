cmake_minimum_required(VERSION 2.8.9)

project(DeveloperToolsForExtensions)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/DeveloperToolsForExtensions")
set(EXTENSION_CATEGORY "Developer Tools")
set(EXTENSION_CONTRIBUTORS "Francois Budin (UNC), Andras Lasso (PerkLab, Queen's University), Jean-Christophe Fillion-Robin (Kitware)")
set(EXTENSION_DESCRIPTION "This extension offers different tools to help developers when they create and maintain Slicer extension.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/Slicer/SlicerDeveloperToolsForExtensions/master/DeveloperToolsForExtensions/Resources/Icons/DeveloperToolsForExtensions.png")
set(EXTENSION_SCREENSHOTURLS "https://www.slicer.org/slicerWiki/images/5/54/SlicerExtension-SlicerDeveloperToolsForExtensions-Screenshot.png https://www.slicer.org/slicerWiki/images/d/db/SlicerExtensions-SlicerDeveloperToolsForExtensions-Screenshot-panels.png")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(DeveloperToolsForExtensions)
add_subdirectory(ExtensionStats)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
