// dicom-probe -- a native C++/ITK pre-flight inspector for DICOM series.
//
// It reads a DICOM directory through ITK's GDCM-backed series reader -- the same
// read path 3D Slicer and ITK-SNAP use -- and prints the *true* volume geometry
// ITK computes (dimensions, spacing, origin, direction cosines) plus intensity
// statistics, as JSON on stdout. This complements dicom-forge's Python QC, which
// inspects tags slice-by-slice: dicom-probe instead validates the authoritative
// ITK load and reports the geometry a downstream ITK/Slicer pipeline will see.
//
// Usage:
//   dicom-probe <dicom-directory> [--series <SeriesInstanceUID>]
//
// Exit codes:
//   0  success: a series was read and its report printed
//   1  usage error (bad arguments)
//   2  no DICOM series found in the directory
//   3  the requested series UID was not present
//   4  ITK failed to read the series into a coherent volume
//
// On any non-zero exit a JSON object with "ok": false and an "error" message is
// still printed, so callers can parse stdout uniformly.

#include "itkGDCMImageIO.h"
#include "itkGDCMSeriesFileNames.h"
#include "itkImage.h"
#include "itkImageSeriesReader.h"
#include "itkStatisticsImageFilter.h"

#include <algorithm>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

using PixelType = float;  // modality-agnostic; GDCM casts integer CT/MR into float.
constexpr unsigned int Dimension = 3;
using ImageType = itk::Image<PixelType, Dimension>;

// Format a double with enough precision for geometry without trailing noise.
std::string num(double value) {
  std::ostringstream os;
  os.precision(8);
  os << value;
  return os.str();
}

// Emit a JSON array of doubles, e.g. [0.7,0.7,1].
std::string array(const std::vector<double>& values) {
  std::ostringstream os;
  os << '[';
  for (std::size_t i = 0; i < values.size(); ++i) {
    if (i != 0) {
      os << ',';
    }
    os << num(values[i]);
  }
  os << ']';
  return os.str();
}

// Minimal JSON string escaping (UIDs/paths only need quote and backslash).
std::string quote(const std::string& text) {
  std::ostringstream os;
  os << '"';
  for (const char c : text) {
    if (c == '"' || c == '\\') {
      os << '\\';
    }
    os << c;
  }
  os << '"';
  return os.str();
}

// Print a uniform failure object and return the chosen exit code.
int fail(int code, const std::string& message) {
  std::cout << "{\"ok\":false,\"error\":" << quote(message) << "}\n";
  return code;
}

}  // namespace

int main(int argc, char* argv[]) {
  std::string directory;
  std::string requestedSeries;

  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--series") {
      if (i + 1 >= argc) {
        return fail(1, "--series requires a SeriesInstanceUID argument");
      }
      requestedSeries = argv[++i];
    } else if (directory.empty()) {
      directory = arg;
    } else {
      return fail(1, "unexpected extra argument: " + arg);
    }
  }
  if (directory.empty()) {
    std::cerr << "usage: dicom-probe <dicom-directory> [--series <uid>]\n";
    return fail(1, "missing DICOM directory argument");
  }

  // Enumerate the DICOM series present in the directory.
  auto names = itk::GDCMSeriesFileNames::New();
  names->SetUseSeriesDetails(true);
  names->SetDirectory(directory);

  std::vector<std::string> seriesUIDs;
  try {
    seriesUIDs = names->GetSeriesUIDs();
  } catch (const itk::ExceptionObject& ex) {
    return fail(2, std::string("could not scan directory: ") + ex.what());
  }
  if (seriesUIDs.empty()) {
    return fail(2, "no DICOM series found in " + directory);
  }

  // Choose the series: the requested UID, or otherwise the one with most slices.
  std::string chosen;
  if (!requestedSeries.empty()) {
    if (std::find(seriesUIDs.begin(), seriesUIDs.end(), requestedSeries) ==
        seriesUIDs.end()) {
      return fail(3, "series not found in directory: " + requestedSeries);
    }
    chosen = requestedSeries;
  } else {
    std::size_t best = 0;
    for (const auto& uid : seriesUIDs) {
      const std::size_t count = names->GetFileNames(uid).size();
      if (count > best) {
        best = count;
        chosen = uid;
      }
    }
  }

  const std::vector<std::string> fileNames = names->GetFileNames(chosen);

  // Read the chosen series into a 3D volume via the GDCM image IO.
  auto reader = itk::ImageSeriesReader<ImageType>::New();
  auto dicomIO = itk::GDCMImageIO::New();
  reader->SetImageIO(dicomIO);
  reader->SetFileNames(fileNames);

  auto stats = itk::StatisticsImageFilter<ImageType>::New();
  stats->SetInput(reader->GetOutput());
  try {
    stats->Update();
  } catch (const itk::ExceptionObject& ex) {
    return fail(4, std::string("ITK failed to read series: ") + ex.what());
  }

  const ImageType::Pointer image = reader->GetOutput();
  const ImageType::SizeType size = image->GetLargestPossibleRegion().GetSize();
  const ImageType::SpacingType spacing = image->GetSpacing();
  const ImageType::PointType origin = image->GetOrigin();
  const ImageType::DirectionType direction = image->GetDirection();

  std::vector<double> directionCosines;
  for (unsigned int r = 0; r < Dimension; ++r) {
    for (unsigned int c = 0; c < Dimension; ++c) {
      directionCosines.push_back(direction(r, c));
    }
  }

  // Emit the report. Single-line JSON keeps it pipe- and jq-friendly.
  std::cout << "{"
            << "\"ok\":true,"
            << "\"directory\":" << quote(directory) << ","
            << "\"series_instance_uid\":" << quote(chosen) << ","
            << "\"series_found\":" << seriesUIDs.size() << ","
            << "\"slices\":" << fileNames.size() << ","
            << "\"dimensions\":"
            << array({static_cast<double>(size[0]), static_cast<double>(size[1]),
                      static_cast<double>(size[2])})
            << ","
            << "\"spacing\":" << array({spacing[0], spacing[1], spacing[2]}) << ","
            << "\"origin\":" << array({origin[0], origin[1], origin[2]}) << ","
            << "\"direction\":" << array(directionCosines) << ","
            << "\"intensity\":{"
            << "\"min\":" << num(stats->GetMinimum()) << ","
            << "\"max\":" << num(stats->GetMaximum()) << ","
            << "\"mean\":" << num(stats->GetMean())
            << "}"
            << "}\n";

  return 0;
}
