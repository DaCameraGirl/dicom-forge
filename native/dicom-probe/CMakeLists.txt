# dicom-probe -- native C++/ITK pre-flight inspector for DICOM series.
#
# Build:
#   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
#   cmake --build build --parallel
#
# Requires ITK 5 with the GDCM IO module (Debian/Ubuntu: libinsighttoolkit5-dev).

cmake_minimum_required(VERSION 3.16)
# C is enabled alongside CXX because Ubuntu's ITK pulls in the VTK glue module,
# whose CMake config runs find_package(MPI COMPONENTS C) -- that requires the C
# language to be enabled even though dicom-probe itself is pure C++.
project(dicom-probe LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# Only the modules dicom-probe actually uses, so configuration stays fast and the
# dependency is explicit.
find_package(ITK 5 REQUIRED
  COMPONENTS
    ITKCommon
    ITKIOGDCM
    ITKImageStatistics
)
include(${ITK_USE_FILE})

add_executable(dicom-probe src/main.cpp)
target_link_libraries(dicom-probe PRIVATE ${ITK_LIBRARIES})

if(MSVC)
  target_compile_options(dicom-probe PRIVATE /W4)
else()
  target_compile_options(dicom-probe PRIVATE -Wall -Wextra)
endif()

install(TARGETS dicom-probe RUNTIME DESTINATION bin)
