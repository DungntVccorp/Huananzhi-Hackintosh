# Huananzhi X99-TF Hackintosh (OpenCore)

Tài liệu khảo sát phần cứng và cách build USB cài macOS từ Windows. Dữ liệu phần cứng lấy từ Windows (WMI) ngày 2026-11-06.

## 1. Phần cứng

| Thành phần | Model (ID) | macOS | Ghi chú |
|---|---|---|---|
| Mainboard | Huananzhi X99-TF, BIOS AMI 5.11 (2019-10-28) | OK | Chipset C612/X99 (HEDT) |
| CPU | Xeon E5-2678 v3, 12C/24T, Haswell-E | OK | Cần quirk HEDT (xem mục 4) |
| RAM | 1× 16GB Micron 36ASF2G72PZ DDR4-2133 ECC RDIMM | OK | ECC chạy được |
| GPU | AMD RX 5600 XT Gigabyte (1002:731F, Navi 10) | **Native** | Cần `agdpmod=pikera` |
| Ổ NVMe | Samsung PM981 512GB (144D:A808) | **KHÔNG hỗ trợ** | Xem mục 2 |
| LAN | Realtek RTL8111 (10EC:8168) | Cần kext | RealtekRTL8111.kext |
| LAN USB | Realtek RTL8153 (0BDA:8153) | Chưa rõ | Kiểm tra khi boot lần đầu |
| Audio | Realtek ALC892 (10EC:0892) trên 8086:8D20 | AppleALC | Hỏng trên Tahoe 26 (xem mục 2) |
| Audio HDMI/DP | GPU (1002:AB38) | Native | |
| USB | XHCI 8086:8D31, EHCI 8086:8D26 / 8D2D | Cần map | Map bằng USBToolBox từ Windows |
| Wi-Fi/BT | Không có | — | |

## 2. Vấn đề chặn và quyết định cần chốt

### 2.1 Ổ PM981 không dùng được cho macOS — cần ổ thứ hai
Samsung PM981 nằm trong danh sách **không hỗ trợ** của Dortania: kernel panic liên tục (IONVMe) kể cả khi có NVMeFix. Đây cũng là ổ duy nhất và đang chứa Windows.

- Board có 2 khe M.2 2280 NVMe (PM981 đang chiếm 1 khe, nối thẳng lane CPU qua root port 8086:2F03) + 1 khe M.2 Wi-Fi + 8 cổng SATA III.
- Mua thêm ổ cho macOS: **SSD SATA** (rẻ, an toàn nhất) hoặc NVMe controller Phison / WD (vd WD SN750/SN770, Sabrent Rocket).
- **Đã chọn:** PNY CS1311b 128GB SATA (controller Phison S11), cắm cổng SATA (AHCI 8086:8D02). Đã thử và loại: Intel 600p SSDPEKKW128G7 (main không nhận), WD Green WDS240G2G0B (M.2 SATA, khe M.2 chỉ NVMe).
- Không cài macOS lên PM981, không chia phân vùng với Windows trên ổ này.
- Nếu installer bị panic/treo khi PM981 vẫn gắn: tháo PM981 ra trong lúc cài.

### 2.2 Chọn phiên bản macOS
| Phiên bản | Audio ALC892 | SMBIOS | Ghi chú |
|---|---|---|---|
| **Sequoia 15 (khuyến nghị)** | Chạy (AppleALC) | iMacPro1,1 | Mọi thứ hoạt động |
| Tahoe 26 | **Mất** analog — AppleHDA bị Apple gỡ | MacPro7,1 (+RestrictEvents) | Chỉ còn audio HDMI/DP hoặc USB DAC; VoodooHDA là phương án tạm |

Tahoe 26 là macOS Intel cuối cùng — không có bản nào mới hơn cho máy này.

## 3. Cài đặt BIOS

**Tắt:** Fast Boot, Secure Boot, CSM, Serial/COM port, VT-d (hoặc bật quirk `DisableIoMapper`), CFG Lock (nếu BIOS có mục này — Huananzhi thường ẩn, khi đó dùng quirk `AppleXcpmCfgLock`).

**Bật:** VT-x, Above 4G Decoding, Hyper-Threading, Execute Disable Bit, EHCI/XHCI Hand-off, SATA mode AHCI, OS type: Windows UEFI.

> Secure Boot không kiểm tra được từ Windows (thiếu quyền admin) — xác nhận trực tiếp trong BIOS.

## 4. Nội dung EFI (OpenCore 1.0.8 RELEASE)

Theo [Dortania Haswell-E](https://dortania.github.io/OpenCore-Install-Guide/config-HEDT/haswell-e.html).

### Drivers
`OpenRuntime.efi`, `HfsPlus.efi`

### ACPI
| SSDT | Tác dụng |
|---|---|
| SSDT-PLUG | Quản lý điện năng CPU |
| SSDT-EC-USBX | EC giả + nguồn USB |
| SSDT-RTC0-RANGE | Sửa RTC cho X99 (bắt buộc Big Sur+) |
| SSDT-UNC | Sửa thiết bị UNC cho X99 (bắt buộc Big Sur+) |

Tạo từ DSDT của máy bằng [SSDTTime](https://github.com/corpnewt/SSDTTime) chạy trên Windows; mục nào SSDTTime không có thì lấy bản prebuilt của Dortania.

### Kexts (thứ tự load: Lilu trước tiên)
| Kext | Phiên bản | Tác dụng |
|---|---|---|
| Lilu | 1.7.2 | Nền tảng cho các kext khác |
| VirtualSMC (+SMCProcessor, SMCSuperIO) | 1.3.8 | Giả lập SMC |
| WhateverGreen | 1.7.1 | GPU Navi |
| AppleALC | 1.9.8 | Audio ALC892 (Sequoia) |
| RealtekRTL8111 | 3.0.0 | LAN — **bắt buộc** vì recovery tải ~12GB qua mạng khi cài |
| CpuTscSync | 1.1.2 | Đồng bộ TSC trên X99 |
| NVMeFix | mới nhất | Giảm lỗi khi PM981 vẫn gắn trong máy |
| USBToolBox + UTBMap | 1.2.0 | USB map — **chưa có trên USB cài**, thêm sau khi cài (USBToolBox chỉ có tác dụng khi kèm UTBMap) |
| RestrictEvents | mới nhất | Chỉ cần nếu dùng SMBIOS MacPro7,1 |

### Quirk quan trọng
- **Booter:** `AvoidRuntimeDefrag`, `EnableSafeModeSlide`, `EnableWriteUnprotector`, `ProvideCustomSlide`, `SetupVirtualMap` = YES
- **Kernel:** `AppleXcpmCfgLock` = YES (nếu CFG Lock không tắt được), `AppleXcpmExtraMsrs` = YES (bắt buộc HEDT), `DisableIoMapper` = YES (nếu VT-d bật), `XhciPortLimit` = NO
- **boot-args:** `-v keepsyms=1 debug=0x100 agdpmod=pikera`. Thêm `npci=0x2000` nếu treo ở `PCI Start Configuration`.
- **SMBIOS:** iMacPro1,1 (Sequoia) — sinh serial bằng [GenSMBIOS](https://github.com/corpnewt/GenSMBIOS), kiểm tra serial *không hợp lệ* trên checkcoverage.apple.com.

Sửa `config.plist` bằng [ProperTree](https://github.com/corpnewt/ProperTree) (dùng OC Snapshot sau khi chép xong ACPI/Kexts/Drivers). Kiểm tra bằng `ocvalidate.exe` trong gói OpenCore.

## 5. Build USB cài đặt trên Windows

### Bước 0 — Chuẩn bị
- USB ≥ 4GB (sẽ bị xoá sạch).
- Cài **Python 3** từ [python.org](https://www.python.org/downloads/windows/) (tick "Add to PATH"). Hiện máy chưa có Python; lệnh `python` đang trỏ tới alias Microsoft Store.
- Tải [OpenCorePkg 1.0.8](https://github.com/acidanthera/OpenCorePkg/releases) (bản RELEASE).
- Cắm dây LAN vào cổng Realtek on-board.

### Bước 1 — Tải macOS Recovery
Trong `OpenCore\Utilities\macrecovery\`:
```bat
:: Sequoia 15
python macrecovery.py -b Mac-937A206F2EE63C01 -m 00000000000000000 download
:: Tahoe 26 (nếu chọn)
python macrecovery.py -b Mac-CFF7D910A743CAAF -m 00000000000000000 -os latest download
```
Kết quả: thư mục `com.apple.recovery.boot` chứa `BaseSystem.dmg` + `BaseSystem.chunklist`.

### Bước 2 — Format USB
Disk Management (hoặc `diskpart`): xoá hết phân vùng, chuyển **GPT**, tạo 1 phân vùng **FAT32**.

> Kiểm tra kỹ số disk trước khi xoá — disk 0 là ổ Windows.

### Bước 3 — Chép file vào USB
```
USB:\
├── com.apple.recovery.boot\   (BaseSystem.dmg, BaseSystem.chunklist)
└── EFI\
    ├── BOOT\BOOTx64.efi
    └── OC\ (ACPI, Drivers, Kexts, Tools, OpenCore.efi, config.plist)
```
Lấy `EFI` từ `OpenCorePkg\X64\EFI`, xoá driver/tool thừa, thêm SSDT/kext ở mục 4.

### Bước 4 — USB map (làm ngay trên Windows)
Chạy [USBToolBox tool](https://github.com/USBToolBox/tool) → Discover Ports → cắm thiết bị USB 2.0 và 3.0 vào từng cổng → Select Ports (≤15 cổng / controller) → Build UTBMap.kext. Chép `UTBMap.kext` + `USBToolBox.kext` vào `EFI\OC\Kexts`.

### Bước 5 — Boot
Boot menu BIOS → chọn USB (UEFI) → OpenCore picker → "macOS Base System" → Disk Utility xoá ổ macOS mới thành **APFS / GUID** → Reinstall macOS.

Sau khi cài xong: chép thư mục `EFI` từ USB sang phân vùng EFI của ổ macOS (dùng MountEFI hoặc `diskutil mount`).

## 6. Dựng lại EFI (cách đã làm)

1. Tải OpenCore 1.0.8 (dùng bản **DEBUG** cho `BOOTx64.efi`, `OpenCore.efi`, `OpenRuntime.efi`, `ResetNvramEntry.efi`), kext RELEASE, `HfsPlus.efi` (OcBinaryData) vào `downloads/` (gitignored).
2. SSDT: dùng 4 file prebuilt của Dortania — đã đối chiếu với DSDT máy (dump bằng SSDTTime + iasl 20251212, vì iasl 20260408 bị SSDTTime blacklist):
   `\_SB.SCK0.CP00` là `Processor` → SSDT-PLUG-DRTNIA; không có EC → SSDT-EC-USBX-DESKTOP (EC giả dưới `LPC0`); `LPC0.RTC` thiếu 0x72-0x73 → SSDT-RTC0-RANGE-HEDT; có `UNC0` + `PRBM` → SSDT-UNC.
3. SMBIOS iMacPro1,1: serial từ `macserial.exe`, lưu ở `smbios.json` (gitignored — **không commit serial**). ROM = MAC Realtek PCIe.
4. `python -I tools/build_config.py <Sample.plist> smbios.json <EFI/OC>` rồi `ocvalidate.exe <config.plist>` phải báo "No issues found".

## 7. Đọc log debug từ Windows

- OpenCore (`Misc/Debug/Target = 67`) ghi `opencore-YYYY-MM-DD-HHMMSS.txt` vào **gốc phân vùng EFI đã boot** (USB → `E:\`). Không đổi được thư mục.
- `SysReport = true` (chỉ bản DEBUG) dump ACPI, audio codec… vào `E:\SysReport\`.
- Log của macOS (verbose `-v`, kernel panic) **không** ghi ra USB được — chụp ảnh màn hình chỗ dừng/panic.
- Sau khi boot ổn định: chuyển về bản RELEASE, `Target = 3`, `SysReport = false` (log file làm boot chậm).

## 8. Lỗi đã gặp

- **Ổ PNY CS1311b hỏng firmware**: Windows báo model rác, macOS thấy 74 PB, GPT ghi ra không hợp lệ → thay bằng Netac SSD 120GB. OpenCore + recovery nằm ở ESP 1,5GB trên chính ổ Netac (không cần USB).
- **Cài lặp reboot ở giai đoạn 2 (`-restore`)**: `patchd` báo `img4_firmware_execute failed: 13`, `MSU 1130 Failed to verify against canonical metadata`, `Failed to seal system volume`. Sửa: `Misc/Security/SecureBootModel = Disabled`. Log đọc từ Windows bằng 7-Zip (tách phân vùng APFS) + `dissect.apfs`, file `restore.log`/`patchd-*.log` nằm ở volume **Update**.

## 9. Trạng thái & bản EFI (2026-11-07)

| Bản | Thư mục (`downloads/`, gitignored) | SMBIOS | Kext | Ghi chú |
|---|---|---|---|---|
| Sequoia 15.8.2 — **đã cài & boot OK** | `EFI-on-netac-before-tahoe` | iMacPro1,1 | + WhateverGreen, AppleALC | SecureBootModel Disabled |
| **Tahoe 26 — đã cài & boot OK (2026-11-07)** | `EFI-tahoe` | MacPro7,1 | + RestrictEvents, bỏ WhateverGreen/AppleALC | `revpatch=sbvmm` cho OTA; không có audio analog |

Serial: `downloads/smbios-*.json` (không commit). `tools/build_config.py` tự thêm `agdpmod=pikera` / `revpatch=sbvmm` khi WhateverGreen / RestrictEvents có trong EFI.

### Cài Tahoe không phải chờ tải (offline)
Recovery chỉ ~1GB, phần còn lại (~15GB) recovery tải lúc cài. Để tải trước, từ macOS đang chạy (đã boot bằng EFI MacPro7,1):
```sh
softwareupdate --list-full-installers
softwareupdate --fetch-full-installer --full-installer-version 26.x   # -> /Applications/Install macOS Tahoe.app
sudo "/Applications/Install macOS Tahoe.app/Contents/Resources/startosinstall" --eraseinstall --agreetolicense --newvolumename "Macintosh HD"
```
`--eraseinstall` xoá volume macOS hiện tại và cài sạch, không cần USB, không tải gì thêm.

## Cần kiểm tra khi boot lần đầu
- RTL8153 (LAN USB) có nhận không.
- NVRAM native có hoạt động không (X99 thường OK).
- Nếu reboot bị reset BIOS / vào safe mode: bật `DisableRtcChecksum`.

## Nguồn
- [Dortania – Haswell-E config](https://dortania.github.io/OpenCore-Install-Guide/config-HEDT/haswell-e.html)
- [Dortania – macOS 26 Tahoe](https://dortania.github.io/OpenCore-Install-Guide/extras/tahoe.html)
- [Dortania – Storage không hỗ trợ (PM981)](https://dortania.github.io/Anti-Hackintosh-Buyers-Guide/Storage.html)
- [AppleHDA trên Tahoe](https://github.com/perez987/AppleHDA-back-on-macOS-26-Tahoe)
- [macrecovery recovery_urls.txt](https://github.com/acidanthera/OpenCorePkg/blob/master/Utilities/macrecovery/recovery_urls.txt)

## 10. USB map & bản release (2026-11-07)
- USBToolBox 0.2 trên Windows (`downloads/usbtoolbox`, lịch sử ở `usb.json`): N → P (bật cổng từng có thiết bị, binding companions bật) → K. XHCI 8D31 giữ 15 cổng: 1–6, 12–14, 16–21; EHCI giữ cổng 1 (hub). Kext: `USBToolBox.kext` + `UTBMap.kext`.
- `python -I tools/build_config.py <Sample.plist> <smbios.json> <EFI/OC> --release`: bỏ `-v keepsyms debug`, `Target=3`, không SysReport, `Timeout=5`, ẩn mục phụ (Space để hiện Recovery/Reset NVRAM). Dùng file .efi từ gói OpenCore RELEASE.
- Đang trên ESP Netac: `downloads/EFI-tahoe-release`. Bản debug đã cài được Tahoe: `downloads/EFI-on-netac-tahoe-debug-working`.

## 11. Dùng EFI có sẵn trong repo (`EFI/`)

Bản **Tahoe 26, OpenCore 1.0.8 RELEASE**, đã chạy trên máy này. **PlatformInfo để trống** — phải tự điền trước khi boot:

1. Sinh serial MacPro7,1: `macserial -m MacPro7,1 -g -n 1` (trong gói OpenCore, `Utilities/macserial`) hoặc [GenSMBIOS](https://github.com/corpnewt/GenSMBIOS).
2. Điền vào `smbios.example.json` (ROM = MAC card mạng, 12 ký tự hex; SystemUUID = UUID ngẫu nhiên) rồi sinh lại config:
   ```sh
   python -I tools/build_config.py <OpenCore>/Docs/Sample.plist smbios.example.json EFI/OC --release
   <OpenCore>/Utilities/ocvalidate/ocvalidate EFI/OC/config.plist
   ```
   Hoặc sửa trực tiếp `PlatformInfo > Generic` bằng ProperTree.
3. Chép `EFI/` vào phân vùng EFI (FAT32) của USB/ổ cứng.

Lưu ý:
- `UTBMap.kext` là USB map của **đúng board X99-TF này**; board khác hãy xoá `UTBMap.kext` + `USBToolBox.kext` và tự map.
- SSDT là bản prebuilt Dortania, đã đối chiếu DSDT của X99-TF (BIOS 5.11).
- Không có audio analog trên Tahoe; muốn dùng Sequoia thì thêm WhateverGreen + AppleALC, SMBIOS iMacPro1,1 (script tự thêm `agdpmod=pikera`).
- Bản RELEASE không có log/verbose. Khi gỡ lỗi, chạy script **không** có `--release` và thay các file `.efi` bằng bản DEBUG.
