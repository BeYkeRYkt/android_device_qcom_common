# Copyright (C) 2009 The Android Open Source Project
# Copyright (c) 2011, The Linux Foundation. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Emit commands needed for QCOM devices during OTA installation
(installing the radio image)."""

import common
import re

def GetRadioFiles(z):
  out = {}
  for info in z.infolist():
    if info.filename.startswith("RADIO/") and (info.filename.__len__() > len("RADIO/")):
      fn = "RADIO/" + info.filename[6:]
      out[fn] = fn
  return out

def FullOTA_Assertions(info):
  AddBootloaderAssertion(info, info.input_zip)


def IncrementalOTA_Assertions(info):
  AddBootloaderAssertion(info, info.target_zip)


def AddBootloaderAssertion(info, input_zip):
  android_info = input_zip.read("OTA/android-info.txt")
  m = re.search(r"require\s+version-bootloader\s*=\s*(\S+)", android_info)
  if m:
    bootloaders = m.group(1).split("|")
    if "*" not in bootloaders:
      info.script.AssertSomeBootloader(*bootloaders)
    info.metadata["pre-bootloader"] = m.group(1)

def CheckRadiotarget(info, mount_point):
    fstab = info.script.info.get("fstab", None)
    if fstab:
      p = fstab[mount_point]
      info.script.AppendExtra('assert(qcom.set_radio("%s"));' %
                         (p.fs_type))

# map qcom partitions with filenames
QCOM_MOUNT_MAP = { "NON-HLOS.bin": "modem",
                   "rpm.mbn": "rpm",
                   "sbl1.mbn": "sbl1",
                   "sbl2.mbn": "sbl2",
                   "sbl3.mbn": "sbl3",
                   "tz.mbn": "tz",
                   "emmc_appsboot.mbn": "aboot",
                   "radio.img": "radio"}


def InstallRadio(radio_img, api_version, input_zip, fn, info):
  fn2 = fn[6:]
  fn3 = "/sdcard/radio/" + fn2
  common.ZipWriteStr(info.output_zip, fn2, radio_img)

  if api_version >= 3:
    if (fn2.endswith("ENC") or fn2.endswith("enc")):
        info.script.AppendExtra(('''
assert(package_extract_file("%s", "%s"));
''' %(fn2,fn3) % locals()).lstrip())
    else:
        fstab = info.script.info.get("fstab", None)
        if fn2 not in QCOM_MOUNT_MAP:
            return
        if QCOM_MOUNT_MAP[fn2] not in fstab:
            return
        info.script.WriteRawImage(QCOM_MOUNT_MAP[fn2], fn2);
        return
  elif info.input_version >= 2:
    info.script.AppendExtra(
        'write_firmware_image("PACKAGE:radio.img", "radio");')
  else:
    info.script.AppendExtra(
        ('assert(package_extract_file("radio.img", "/tmp/radio.img"),\n'
         '       write_firmware_image("/tmp/radio.img", "radio"));\n'))


def FullOTA_InstallEnd(info):
  files = GetRadioFiles(info.input_zip)
  if files == {}:
    print "warning sha: no radio image in input target_files; not flashing radio"
    return

  enc_file = "false";

  info.script.UnmountAll()
  info.script.Print("Writing radio image...")
  for f in files:
    if (f.endswith("ENC") or f.endswith("enc")):
        continue
    radio_img = info.input_zip.read(f)
    InstallRadio(radio_img, info.input_version, info.input_zip, f, info)

  for f in files:
    if (f.endswith("ENC") or f.endswith("enc")):
        radio_img = info.input_zip.read(f)
        InstallRadio(radio_img, info.input_version, info.input_zip, f, info)
        enc_file = "true"

  if (enc_file == "true"):
    CheckRadiotarget(info, "/recovery")
  return


def IncrementalOTA_InstallEnd(info):
  #TODO: Implement device specific asserstions.
  print "warning radio-update: no real implementation of IncrementalOTA_InstallEnd."
  return
