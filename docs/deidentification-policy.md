# De-identification policy

This page defines exactly what each de-identification level does, how that maps to
DICOM PS3.15 Annex E (Basic Application Level Confidentiality Profile), and what is
**not** covered. It is the reference for `src/dicomforge/deidentify.py`; the tests in
`tests/test_deid_policy.py` check each rule.

!!! warning "Scope"
    De-identification here is **header-only risk reduction**. It is not a HIPAA, GDPR
    or other regulatory certification, and it has not been clinically validated.
    **Pixel data is never analysed or modified.** Series whose metadata signals
    burned-in annotation are rejected; text burned into any other image survives.
    Review output before it leaves a controlled environment.

## Where it applies

The pipeline de-identifies the DICOM datasets **in memory**, then converts them to
NRRD/NIfTI. Source files are never modified, and no de-identified DICOM is written.
The converted volume contains **no DICOM header fields at all**: only voxels and
geometry. The header policy below therefore governs:

- the in-memory datasets, for API users
- everything derived from them: the audit record (`PipelineResult`), QC report and logs

The voxels in the output are always identical to the source pixels, at every level.

## Rules applied at every level

| Category | Action | PS3.15 action |
|---|---|---|
| Person names: **every PN element** at any depth (patient, physicians, operators…), also when stored with VR UN | removed | X |
| Patient identifiers and demographics: birth date/time (also in alternative calendars), address, phone and telecom, other IDs and names, issuer of patient ID, ethnic group, occupation, religion, residence and current location, insurance, medical alerts, allergies | removed | X |
| Contact details of any person (`PersonAddress`, `PersonTelephoneNumbers`, `PersonTelecomInformation`), at any depth | removed | X |
| **Overlays (60xx) and curves (50xx)**: whole repeating groups, including `OverlayData` bitmaps and overlay descriptions/labels | removed | X |
| **Public tags outside the DICOM dictionary** (cannot be interpreted, so cannot be checked) | removed | (conservative) |
| Institution name, address, department, institution code sequence | removed | X |
| Identifying sequences: `OtherPatientIDsSequence`, `ReferencedPatientSequence`, `RequestAttributesSequence`, `ReferencedStudySequence`, `ReferencedPerformedProcedureStepSequence`, physician/operator identification sequences | removed with all contents | X |
| Order and visit IDs and descriptions: requested/scheduled/performed procedure step IDs and descriptions, admission, service episode | removed | X |
| Free-text comments: `ImageComments`, `StudyComments`, `AcquisitionComments`, `PatientComments`, `AdditionalPatientHistory`, `InterpretationText`, request comments | removed | X |
| `AccessionNumber`, `StudyID` | kept, zero-length | Z |
| **All private tags** (creators and data), at any depth | removed | X (no "Retain Safe Private" option) |
| **Instance UIDs** at any depth and in file meta (Study, Series, SOP Instance, Frame of Reference, referenced instances…) | replaced with `2.25.<n>` | U |
| `PatientID`, wherever it appears | replaced with a keyed pseudonym `DF-…` | (pseudonymisation) |
| Remaining text (LO/SH/ST/LT/UT/UC) containing one of **this dataset's own** identifiers | blanked | (Clean Descriptors, limited) |

**Rules apply recursively.** Every sequence item is processed with the same rules,
however deeply nested.

**UID replacement** uses HMAC-SHA256 under the pseudonymisation secret, so it is:

- **consistent**: the same original UID always maps to the same replacement. Slices of
  a series keep one Series UID, and references between instances still resolve.
- **unlinkable** without the secret.

UIDs defined by the DICOM standard (`1.2.840.10008.*`) are kept. So are class,
transfer-syntax and implementation UIDs (e.g. `SOPClassUID`, `ReferencedSOPClassUID`,
`TransferSyntaxUID`), because they identify a *kind* of object, not a patient.

**Known-identifier screening** collects, before scrubbing:

- every person-name component of 3+ characters
- the values of PatientID, other patient IDs, issuer, AccessionNumber, StudyID, birth
  date, requested-procedure and admission IDs, medical record locator and institution
  name
- every original instance UID (so a UID quoted in text is caught)
- at moderate and strict, every date value (`YYYYMMDD`), so a date quoted in text
  doesn't survive when dates are being removed

It then blanks any remaining text element that contains one of them, case-insensitively.
For example, `StudyDescription = "BRAIN FOLLOWUP TEST-12345"` is blanked, while
`SeriesDescription = "T1 AXIAL"` is kept.

**Provenance:**

- `PatientIdentityRemoved = NO`. DICOM defines this attribute as covering the attributes
  **and the pixel data**. dicom-forge never verifies pixel content, so it can't assert
  `YES`, even when the headers are fully de-identified.
- `DeidentificationMethod = "dicom-forge <level>: header de-identified; pixels
  unverified"` records what was actually done.
- `BurnedInAnnotation` is left exactly as the source declared it.
- `LongitudinalTemporalInformationModified` is set to `UNMODIFIED` (basic) or `REMOVED`
  (moderate, strict).
- No `DeidentificationMethodCodeSequence` is written. The Basic Profile code (113100)
  would claim conformance that this subset doesn't meet.

## Per-level differences

| | basic | moderate | strict |
|---|:-:|:-:|:-:|
| Dates and times (DA/DT/TM), at any depth | **kept** (Retain Longitudinal Temporal Information) | blanked | blanked |
| Device identifiers: `StationName`, `DeviceSerialNumber`, `DetectorID`, `GantryID`, and **every AE title** (including file-meta source/sending AE titles) | kept (unless screened) | removed | removed |
| Patient characteristics: `PatientAge`, `PatientSex`, `PatientSize`, `PatientWeight` | **kept** (Retain Patient Characteristics) | **kept** | age/size/weight removed; sex blanked |
| All remaining free text (LO/SH/ST/LT/UT/UC/AS) outside the geometry safe-list | screened only | screened only | **blanked** |
| `PatientID` when pseudonymisation is disabled | raw ID kept (unsafe opt-out) | raw ID kept (unsafe opt-out) | blanked |

The STRICT safe-list (never blanked): `Modality`, `Rows`, `Columns`, `PixelSpacing`,
`SliceThickness`, `ImagePositionPatient`, `ImageOrientationPatient`, `RescaleSlope`,
`RescaleIntercept`, `PixelData`. Numeric (DS/IS/US…) and coded (CS) attributes are not
blanked by the strict text rule. That keeps geometry and conversion identical across
levels.

### What each level guarantees, and what it does not

- **basic:** no names, direct patient identifiers, institution, accession number,
  private tags or original UIDs remain anywhere in the header. Dates, device names,
  descriptions without known identifiers, and age/sex/size/weight remain. Suitable only
  where dates and device information are acceptable to disclose.
- **moderate** (default): basic, plus no dates/times and no device identifiers. Age,
  sex, size and weight remain, as do descriptions without known identifiers
  (e.g. protocol names).
- **strict:** moderate, plus no patient characteristics and no free text beyond
  coded/numeric attributes and the safe-list.

**At no level** are pixel data, overlays (60xx) or encapsulated documents processed.

## Burned-in pixel annotation

dicom-forge **does not detect, remove or mask text in pixel data**, and makes no claim
of automatic pixel de-identification. Instead, before anything is de-identified or
written, it assesses every instance **from metadata only**
(`dicomforge.pixel_privacy.assess_burned_in_risk`) and flags the series if any
instance shows a risk signal:

| Reason code | Signal |
|---|---|
| `burned_in_annotation_yes` | `BurnedInAnnotation` (0028,0301) is `YES` |
| `burned_in_annotation_unrecognised` | `BurnedInAnnotation` holds anything other than `YES`/`NO` |
| `secondary_capture` | a Secondary Capture SOP class (`1.2.840.10008.5.1.4.1.1.7*`), or `ConversionType` present |
| `high_risk_modality` | Modality US, SC, OT, XC, ES, GM or SM, where on-image text and labels are routine |
| `colour_pixels` | `PhotometricInterpretation` not MONOCHROME1/2 (screenshots, rendered captures) |
| `overlay_in_pixel_data` | an overlay (60xx) stored in the pixel bits instead of its own OverlayData plane |

**Policy** (`PipelineConfig.burned_in_policy`, CLI `--allow-burned-in`):

- **`reject` (default):** a flagged series raises `BurnedInAnnotationError` before
  de-identification and before any file is written. The CLI exits with code `3`. One
  flagged instance rejects the whole series. This applies at every level, and also
  with de-identification disabled.
- **`allow`:** the flagged series is processed, a warning is logged, and the audit
  record keeps `status = "flagged"`. Use it only after a person has reviewed the images.

The rejection message and logs carry **only reason codes and counts**: no paths,
UIDs, names or attribute values.

**Unflagged is not clean.** A series without any signal, including one that declares
`BurnedInAnnotation = NO`, is processed with `status = "unverified"`. Every
`PipelineResult.pixel_privacy` record has `pixel_content_verified = false` and
`pixels_modified = false`. The record also counts instances per indicator value
(`YES` / `NO` / `absent` / `other`).

### What the burned-in policy cannot catch

- **Text in CT, MR, PET or other "low-risk" images with no metadata signal.** For
  example, a scanner or post-processing step that stamped the patient name into an MR
  image without setting `BurnedInAnnotation`. This is a tested, documented limitation
  (`test_limitation_unflagged_burned_in_text_is_not_detected`).
- **Incorrect source declarations:** `BurnedInAnnotation = NO` on an image that has
  text, or a modality code that understates the risk.
- **Derived and reformatted images** (`ImageType` DERIVED/SECONDARY, MPRs, MIPs) are
  not flagged on that basis, even though some vendors annotate them.
- **Non-text identifiers** in pixels: faces in 3-D surface renderings of head CT/MR,
  facial features recoverable from volumes (defacing is not performed), and
  identifiable jewellery, implants or tattoos.
- **Multi-frame, colour and compressed objects** are flagged or handled only by the
  signals above. No pixel decoding is used to look for text.

## Audit record

`PipelineResult.deidentification` covers the **whole series**:

- `removed_tags`, `blanked_tags` and `replaced_uids` are unions over every instance,
  with nested paths written `Sequence[].Keyword`
- `instances` is the number of instances covered
- `removed_private_tags` is the total count
- `pseudonymised_patient_ids` lists every pseudonym seen
- `pseudonymised_patient_id` is set only when the series maps to exactly one

The metadata in the record is read after de-identification, its UIDs are the
replacement UIDs, and `source_path` is always `None`. See
[Concepts → Audit records and logs](concepts.md#audit-records-and-logs).

## Converted volumes say what was (not) done

Every NRRD written by the pipeline carries these header fields (`key:=value`). NIfTI has
no place for them; the audit record is the source of truth there.

| Field | Values |
|---|---|
| `dicomforge_version` | engine version, e.g. `0.2.0` |
| `dicomforge_header_deidentification` | `basic` / `moderate` / `strict` (applied to the source DICOM headers), or `none` with `--no-deid` |
| `dicomforge_pixel_data` | `unverified` for every normal run; `flagged-burned-in-risk-allowed` when the series was flagged and processed only because of the explicit override. Never "clean". |

The Slicer extension also sets these values as volume-node attributes
(`DicomForge.PixelData`, `DicomForge.HeaderDeidentification`, `DicomForge.EngineVersion`).
It adds `_UNSAFE_BURNED_IN` to the name of a node loaded through the override.

## What this protects against, and what it does not

**Protects against** (header data, tested with fictional identifiers at every level):
names, patient IDs (pseudonymised), birth dates, addresses and contact details,
institution and staff identifiers, accession/order/visit identifiers, private vendor
tags, overlays and curves, unknown public tags, original UIDs (consistently replaced),
identifiers nested in sequences, and the record's own identifiers quoted in free text.
It also refuses series whose metadata signals burned-in pixel text, unless explicitly
overridden. Identifiers are kept out of logs, audit records, CLI output and error
messages.

**Does not protect against:**

- identifying text in pixel data without a metadata signal
- facial features in head CT/MR
- identifiers in free text that are not this record's own
- re-identification from the quasi-identifiers it deliberately keeps (age, sex, size,
  weight; dates at `basic`)
- anyone holding the pseudonymisation secret
- attributes outside this documented PS3.15 subset

It is not certified for HIPAA, GDPR or any other regulation, and it is not a validated
anonymization tool.

## Known limitations

- **Burned-in annotations** in pixel data are never removed. They're caught only when
  metadata signals them (see above). Overlay and curve groups are removed from the
  header, but encapsulated documents (e.g. PDF) and structured-report content beyond
  person names are not de-identified.
- **Free-text screening is not general PHI detection.** It finds only this dataset's
  own identifiers, and only tokens of 3+ characters, matched literally. A description
  naming a different person, a 2-letter surname, or an ID written differently
  (`TEST12345` for `TEST-12345`) will not be caught. Use `strict` when free text cannot
  be trusted.
- **Quasi-identifier risk is not measured.** No k-anonymity or similar analysis is
  done. Small cohorts, rare conditions or unusual devices can make records
  re-identifiable even with every listed identifier removed.
- **Dates are blanked, not shifted.** Intervals between studies are lost at moderate
  and strict.
- **Retained characteristics** (age, sex, size, weight at basic/moderate; dates at
  basic) are quasi-identifiers. Combined, they can single out individuals in small
  populations.
- **Code sequences** that are not in the removal list are kept, with only their text
  screened. Coded values (CS) are never blanked.
- **The pseudonymisation secret is the single point of trust.** Anyone holding it can
  re-link pseudonyms and replacement UIDs by testing guesses.
- **The policy is a subset of PS3.15 Annex E.** Attributes not named here and not caught
  by the PN/private/UID/date/strict-text rules are kept. Validate against the full
  Table E.1-1 and a reference implementation before relying on this for data release.
