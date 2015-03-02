cmake_minimum_required(VERSION 2.8.9)

project(ManualExtensionInstaller)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://www.example.com/Slicer/Extensions/ManualExtensionInstaller")
set(EXTENSION_CATEGORY “Developer Tools”)
set(EXTENSION_CONTRIBUTORS “Francois Budin (UNC)”)
set(EXTENSION_DESCRIPTION "This extension allows to install extension directly from a file”)
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/ManualExtensionInstaller.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/ManualExtensionInstaller/Screenshots/1.png")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(ManualExtensionInstaller)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
