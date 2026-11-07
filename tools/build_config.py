"""Build OpenCore config.plist for Huananzhi X99-TF (Haswell-E, Dortania HEDT guide).

Usage: python -I tools/build_config.py <Sample.plist> <smbios.json> <EFI/OC dir>
Writes <EFI/OC dir>/config.plist, enumerating ACPI/Drivers/Kexts/Tools from that dir.
"""
import json
import os
import plistlib
import sys

# Lilu first, then its plugins; anything not listed is appended after.
KEXT_ORDER = ["Lilu", "VirtualSMC", "SMCProcessor", "SMCSuperIO", "WhateverGreen",
              "AppleALC", "RestrictEvents", "RealtekRTL8111", "CpuTscSync", "NVMeFix",
              "USBToolBox", "UTBMap"]

BOOTER_TRUE = {"AvoidRuntimeDefrag", "EnableSafeModeSlide", "EnableWriteUnprotector",
               "ProvideCustomSlide", "SetupVirtualMap"}

KERNEL_QUIRKS = {
    "AppleCpuPmCfgLock": False, "AppleXcpmCfgLock": True, "AppleXcpmExtraMsrs": True,
    "CustomSMBIOSGuid": False, "DisableIoMapper": True, "DisableIoMapperMapping": False,
    "DisableLinkeditJettison": True, "DisableRtcChecksum": False, "IncreasePciBarSize": False,
    "LapicKernelPanic": False, "LegacyCommpage": False, "PanicNoKextDump": True,
    "PowerTimeoutKernelPanic": True, "SetApfsTrimTimeout": -1, "XhciPortLimit": False,
}

# npci=0x2000: Huananzhi BIOS hides Above 4G Decoding; Dortania's substitute for X99 PCI hangs
BOOT_ARGS = "-v keepsyms=1 debug=0x100 npci=0x2000"
BOOT_ARGS_RELEASE = "npci=0x2000"  # after a stable install: no verbose, no debug
# extra args only make sense when their kext is in the EFI (Tahoe build drops WhateverGreen)
KEXT_ARGS = {"WhateverGreen": "agdpmod=pikera", "RestrictEvents": "revpatch=sbvmm"}


def kext_entry(oc, name):
    bundle = f"{name}.kext"
    exe = f"Contents/MacOS/{name}"
    if not os.path.isfile(os.path.join(oc, "Kexts", bundle, *exe.split("/"))):
        exe = ""  # plist-only kext (UTBMap)
    return {"Arch": "Any", "BundlePath": bundle, "Comment": name, "Enabled": True,
            "ExecutablePath": exe, "MaxKernel": "", "MinKernel": "",
            "PlistPath": "Contents/Info.plist"}


def build(sample, smbios, oc, release=False):
    with open(sample, "rb") as f:
        c = plistlib.load(f)

    acpi = sorted(x for x in os.listdir(os.path.join(oc, "ACPI")) if x.endswith(".aml"))
    c["ACPI"]["Add"] = [{"Comment": x, "Enabled": True, "Path": x} for x in acpi]
    c["ACPI"]["Delete"] = []
    c["ACPI"]["Patch"] = []

    c["Booter"]["MmioWhitelist"] = []
    c["Booter"]["Patch"] = []
    for k, v in c["Booter"]["Quirks"].items():
        if isinstance(v, bool):
            c["Booter"]["Quirks"][k] = k in BOOTER_TRUE

    c["DeviceProperties"]["Add"] = {}
    c["DeviceProperties"]["Delete"] = {}

    present = [x[:-5] for x in os.listdir(os.path.join(oc, "Kexts")) if x.endswith(".kext")]
    order = [k for k in KEXT_ORDER if k in present] + sorted(set(present) - set(KEXT_ORDER))
    c["Kernel"]["Add"] = [kext_entry(oc, k) for k in order]
    c["Kernel"]["Block"] = []
    c["Kernel"]["Force"] = []
    c["Kernel"]["Patch"] = []
    c["Kernel"]["Quirks"].update(KERNEL_QUIRKS)

    m = c["Misc"]
    if release:
        # Space shows Recovery/Reset NVRAM; auto-boot the default (last macOS) after 5s
        m["Boot"].update({"HideAuxiliary": True, "Timeout": 5})
        m["Debug"].update({"AppleDebug": False, "ApplePanic": True, "DisableWatchDog": True,
                           "Target": 3, "SysReport": False})
    else:
        # show "macOS Base System" without pressing Space; Timeout 0 = wait, never auto-boot Windows
        m["Boot"].update({"HideAuxiliary": False, "Timeout": 0})
        m["Debug"].update({"AppleDebug": True, "ApplePanic": True, "DisableWatchDog": True,
                           # 67 = enable + onscreen + file (opencore-*.txt on ESP root);
                           # SysReport dumps ACPI/audio/etc to ESP\SysReport (DEBUG build only)
                           "Target": 67, "SysReport": True})
    m["Security"].update({"AllowSetDefault": True, "BlacklistAppleUpdate": True,
                          "DmgLoading": "Signed", "ExposeSensitiveData": 6,
                          "ScanPolicy": 0, "SecureBootModel": "Disabled", "Vault": "Optional"})
                          # Disabled: with Default, Sequoia install fails sealing the system volume (patchd MSU 1130, img4_firmware_execute 13)
    m["Entries"] = []
    tools = sorted(x for x in os.listdir(os.path.join(oc, "Tools")) if x.endswith(".efi"))
    m["Tools"] = [{"Arguments": "", "Auxiliary": True, "Comment": t, "Enabled": True,
                   "Flavour": "Auto", "FullNvramAccess": False, "Name": t[:-4],
                   "Path": t, "RealPath": False, "TextMode": False} for t in tools]

    nv = c["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]
    base = BOOT_ARGS_RELEASE if release else BOOT_ARGS
    nv["boot-args"] = " ".join([base] + [a for k, a in KEXT_ARGS.items() if k in present])
    nv["csr-active-config"] = bytes(4)
    nv["prev-lang:kbd"] = b""

    with open(smbios) as f:
        s = json.load(f)
    g = c["PlatformInfo"]["Generic"]
    g.update({"SystemProductName": s["SystemProductName"],
              "SystemSerialNumber": s["SystemSerialNumber"], "MLB": s["MLB"],
              "SystemUUID": s["SystemUUID"], "ROM": bytes.fromhex(s["ROM"]),
              "SpoofVendor": True, "AdviseFeatures": False, "MaxBIOSVersion": False,
              "ProcessorType": 0, "SystemMemoryStatus": "Auto"})
    c["PlatformInfo"]["UpdateSMBIOSMode"] = "Create"

    drivers = sorted(x for x in os.listdir(os.path.join(oc, "Drivers")) if x.endswith(".efi"))
    # OpenRuntime must load first
    drivers.sort(key=lambda d: d != "OpenRuntime.efi")
    c["UEFI"]["Drivers"] = [{"Arguments": "", "Comment": d, "Enabled": True,
                             "HideVerbose": False, "LoadEarly": False, "Path": d} for d in drivers]
    c["UEFI"]["Quirks"].update({"IgnoreInvalidFlexRatio": True, "RequestBootVarRouting": True,
                                "UnblockFsConnect": False})

    # self-check: every referenced file exists
    for e in c["ACPI"]["Add"]:
        assert os.path.isfile(os.path.join(oc, "ACPI", e["Path"])), e
    for e in c["Kernel"]["Add"]:
        assert os.path.isfile(os.path.join(oc, "Kexts", e["BundlePath"], "Contents", "Info.plist")), e
    assert c["Kernel"]["Add"][0]["BundlePath"] == "Lilu.kext"

    out = os.path.join(oc, "config.plist")
    with open(out, "wb") as f:
        plistlib.dump(c, f)
    print("wrote", out, "| ACPI", acpi, "| Kexts", order, "| Drivers", drivers, "| Tools", tools)


if __name__ == "__main__":
    build(*sys.argv[1:4], release="--release" in sys.argv[4:])
