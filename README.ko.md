# TOTEM

[English](README.md) | 한국어

TOTEM 키보드용 ZMK 펌웨어 저장소입니다. 옵션으로 OLED 동글, 블루투스 OTA 부트로더, 블루투스 호스트 이름 표시 및 편집을 지원합니다.

## 키맵 및 페어링

[`config/totem.keymap`](config/totem.keymap)을 수정하면 GitHub Actions가 키맵 다이어그램을 자동으로 갱신합니다. 이 브랜치의 좌우 독립 레이어와 홈로우 모디파이어는 [KEYMAP.md](KEYMAP.md)를 참고하세요. 기기에서 ZMK Studio로 수정한 내용은 다이어그램에 반영되지 않습니다.

![TOTEM keymap layers](keymap-drawer/totem.svg)

- **동글 페어링**: 동글을 사용할 경우, 좌·우 하프는 동글에 자동 연결됩니다. 블루투스로 입력할 때만 호스트 기기에서 `TOTEM-Dongle`을 페어링하면 되며, USB 유선 연결 시에는 별도 페어링이 필요 없습니다.
- **프로필 관리**: 동글은 최대 5개의 호스트 프로필을 지원합니다. BT1~5 버튼으로 페어링된 기기 바꿀 수 있고 `BT_CLR` 키로 저장된 페어링 삭제할 수 있습니다.

## 빌드

미리 빌드된 UF2 파일과 OTA ZIP 패키지는 [GitHub Actions](https://github.com/80ROkWOC4j/totem/actions) 실행 결과의 **Artifacts**에서 내려받을 수 있습니다.

로컬 빌드는 devcontainer 구성되어 있어 `"dev.containers.dockerPath": "podman"` 설정 하면 간단하게 할 수 있습니다.

```sh
./scripts/container.sh ./scripts/setup.sh
./scripts/container.sh python3 scripts/build.py all
./scripts/container.sh python3 scripts/build-bootloader.py all
```

특정 타깃만 빌드하려면 `all` 대신 타깃 이름을 지정합니다:

- **펌웨어** ([`build.yaml`](build.yaml)): `totem_dongle_central_oled`, `totem_dongle_left`, `totem_dongle_right`(동글 사용) 또는 `totem_left`, `totem_right`(단독 사용)
- **부트로더**: `totem_dongle`, `totem_left_ble`, `totem_right_ble`, `totem_left_ble_sense`, `totem_right_ble_sense`

결과물은 `build/artifacts/`(부트로더는 `build/artifacts/bootloader/`)에 생성됩니다.

### 자동 빌드와 다운로드

| 아티팩트 접두어 | 포함 내용 | 생성 조건 |
| --- | --- | --- |
| `firmware-uf2` | USB 설치용 펌웨어 UF2 | 펌웨어 빌드 |
| `firmware-ota` | 폰 업데이트용 펌웨어 OTA ZIP | 펌웨어 빌드 |
| `bootloader-uf2` | USB 설치용 부트로더 UF2 | 부트로더 빌드 |
| `bootloader-ota` | 부트로더 업데이트·펌웨어 복원 ZIP 쌍, 안내와 검증 정보 | 부트로더 빌드 |
| `firmware-recovery` | 펌웨어 HEX·메타데이터·의존성 잠금 파일·OLED 미리보기 | 수동 전체 빌드 |
| `bootloader-recovery` | 부트로더 HEX·메타데이터·OLED 미리보기 | 수동 전체 빌드 |

해당 실행에 필요한 아티팩트만 생성합니다. 자동 다운로드는 **7일**, 수동
다운로드는 **30일** 보관합니다. 실제 이름 뒤에는 워크플로의 묶음 이름,
실행 번호와 소스 커밋이 붙습니다. 기존 다운로드의 만료일은 유지됩니다.
폰에서는 서로 다른 빌드의 파일이 섞이지 않도록 폴더를 나눠 보관하세요.

6종이 모두 필요하면 **Actions → Build All Firmware → Run workflow**에서
`main` 또는 `home-row`를 선택해 실행하세요. 선택한 브랜치의 키맵이 펌웨어와
부트로더 OTA 복원 파일에 적용됩니다. **Build Left Firmware**와
**Build Dongle Central**은 해당 타깃의 펌웨어 UF2·OTA만 생성합니다.

자동 빌드 범위는 다음과 같습니다.

- 문서·이미지·키맵 그림만 변경: 펌웨어·부트로더 빌드 생략
- 키맵·레이아웃 변경: 대표 타깃 2종(단독 왼쪽·OLED 동글)
- 펌웨어·설정·의존성 변경: 펌웨어 5종
- 부트로더 변경: 부트로더 5종과 OTA 복원용 동글 구성 펌웨어 3종.
  별도의 펌웨어 변경이 없다면 부트로더 아티팩트만 게시합니다.
- 공통 도구 또는 분류되지 않은 빌드 입력 변경: 펌웨어·부트로더 모두

겹치는 타깃은 한 번만 빌드합니다. 새 브랜치는 `main`과의 공통 조상부터 비교합니다.

| 대상 | 애플리케이션 OTA 파일 |
| --- | --- |
| 동글 | `dongle-ota.zip` |
| 동글용 왼쪽 / 오른쪽 | `left-ota.zip` / `right-ota.zip` |
| 단독 왼쪽 / 오른쪽 | `left-solo-ota.zip` / `right-solo-ota.zip` |

자동·단일 타깃 수동 다운로드는 `left.uf2`, `left-solo.uf2`처럼 짧은 UF2
이름을 씁니다. 부트로더는 `dongle-boot.uf2`, `left-boot.uf2`, `right-boot.uf2`,
`left-sense-boot.uf2`, `right-sense-boot.uf2`로 구분합니다.
**수동 전체 빌드는 원래 UF2 파일명을 유지**합니다. 예를 들어
`totem_dongle_left.uf2`, `update-totem_right_ble_sense_bootloader-2.6.0-totem2_nosd.uf2`입니다.
OTA ZIP 이름은 모든 빌드에서 짧게 유지됩니다.

미리 생성된 `bootloader-ota`를 사용할 때는 recovery 묶음이 필요 없습니다.
수동 전체 빌드 결과로 패키지를 로컬에서 다시 만들려면 같은 실행의
`firmware-uf2`·`firmware-recovery`를 `build/artifacts/`에,
`bootloader-uf2`·`bootloader-recovery`를 `build/artifacts/bootloader/`에 풉니다.
소스 잠금 정보가 일치하도록 저장소도 해당 빌드의 커밋으로 맞추세요.

## 부트로더 및 OTA

커스텀 부트로더(`2.6.0-totem2`)는 ZMK 펌웨어와 독립적으로 동작합니다.

| 조작 | 동작 |
| --- | --- |
| **리셋 1회** | 500 ms 후 BLE OTA 모드 진입 (대기 중 리셋 1회 또는 6분간 무입력 시 일반 펌웨어로 복귀) |
| **더블 리셋** (500 ms 이내) | USB UF2 드라이브 모드 진입 |
| **유효한 펌웨어 없이 전원 인가** | USB 데이터 호스트 연결 시 USB UF2 진입(단순 충전기 제외), 미연결 시 BLE OTA 진입 |

동글 OLED에는 부트로더 모드·버전·전송 진행률 또는 `NO FIRMWARE` / `WRONG FILE`이 표시됩니다(좌·우 하프에는 화면 없음). 전송이 중단되면 이전 이미지로 롤백되지 않으므로 처음부터 다시 전송해야 합니다.

### 1. 최초 USB 부트로더 설치

플래싱 전에 반드시 `INFO_UF2.TXT`, USB VID:PID, SoftDevice 버전을 대조하세요. 일반 XIAO 보드에 Sense 부트로더가 설치되어 출고되는 경우가 있으므로 기판 인쇄명이 아닌 **설치된 `INFO_UF2.TXT` 식별자**를 기준으로 맞추세요.

| 설치된 `INFO_UF2.TXT` (`VID:PID`) | 부트로더 타깃 | SoftDevice |
| --- | --- | --- |
| `nRF52840-nicenano` (`239a:00b3`) | `totem_dongle` | S140 6.1.1 |
| `nRF52840-SeeedXiao-v1` (`2886:0044`) | `totem_left_ble` / `totem_right_ble` | S140 7.3.0 |
| `Seeed_XIAO_nRF52840_Sense` 또는 `nRF52840-SeeedXiaoSense-v1` (`2886:0045`) | `totem_left_ble_sense` / `totem_right_ble_sense` | S140 7.3.0 |

1. 기기를 하나씩 USB로 연결하고 버튼을 두번 눌러서 플래시 준비.
2. `bootloader-uf2` 압축을 풀고 기기에 맞는 파일을 드라이브에 복사합니다. 자동 빌드는 `<device>-boot.uf2`, 수동 전체·로컬 빌드는 `update-<target>_bootloader-2.6.0-totem2_nosd.uf2`입니다.
3. 재부팅 후 다시 더블 리셋하여 `INFO_UF2.TXT`에 `2.6.0-totem2`가 표시되는지 확인한 뒤, 실제 zmk 펌웨어 `<firmware>.uf2`를 설치.

### 2. Android BLE OTA 업데이트

Nordic [nRF Device Firmware Update](https://play.google.com/store/apps/details?id=no.nordicsemi.android.dfu) 앱을 설치하고 설정에서 **Packets Receipt Notifications (PRN) = 켜기(12)**, **Request high MTU = 끄기**로 맞춥니다. 바깥 `firmware-ota` 다운로드 압축을 푼 뒤, 안에 있는 기기별 `*-ota.zip` 파일은 풀지 않고 휴대폰으로 옮깁니다.

| 기기 | BLE OTA 이름 | 동글 사용 | 단독 사용 |
| --- | --- | --- | --- |
| 동글 | `TOTEM_DFU` | `dongle-ota.zip` | — |
| 좌측 | `TOTEM_L_DFU` | `left-ota.zip` | `left-solo-ota.zip` |
| 우측 | `TOTEM_R_DFU` | `right-ota.zip` | `right-solo-ota.zip` |

업데이트할 기기에서 리셋을 1회 누르고 DFU 앱에서 해당 OTA 이름을 선택한 뒤(OS 블루투스 설정에서는 페어링하지 마세요) 맞는 `<firmware>-ota.zip`을 전송합니다. 각 기기는 개별적으로 업데이트하며, 좌·우 하프는 하드웨어 ID가 같아 잘못된 파일을 걸러내지 못하므로 파일명을 꼭 확인하세요.

### 3. BLE로 부트로더 업데이트 (2회 연속 전송)

부트로더를 빌드할 때 **bootloader-ota** 다운로드도 제공합니다(자동 7일,
수동 30일 보관). 폰에서 바깥 압축파일을 풀고 설치된 보드 식별자에 맞는
`dongle`, `left`, `left-sense`, `right`, `right-sense` 폴더를 선택하세요.
각 폴더에는 `*-01-boot.zip`, `*-02-app.zip`, `README.txt`, 검증 정보가
들어 있습니다. 01 전송 후 다시 연결해 02를 전송하며, 안쪽 ZIP 두 개는
풀지 않습니다. 복원 파일은 단독 구성이 아닌 **동글 구성 펌웨어**입니다.
두 패키지는 같은 CI 소스에서 생성합니다.

로컬에서 펌웨어와 부트로더를 빌드한 뒤 5종을 한 번에 만들 수도 있습니다:

```sh
./scripts/container.sh python3 scripts/bootloader-ota.py all
```

BLE로 부트로더를 올리면 펌웨어 영역 일부가 덮어써지므로 **부트로더를 OTA로 업데이트 할 경우 펌웨어도 재설치**해야 합니다:

```sh
./scripts/container.sh python3 scripts/bootloader-ota.py totem_right_ble_sense \
  --application-hex build/artifacts/totem_dongle_right.hex
```

`all`의 결과는 `build/bootloader-ota/all/<device>/`, 단일 타깃의 결과는 `build/bootloader-ota/<target>/`에 생성됩니다. `<device>-01-boot.zip`을 전송하고, DFU 모드로 재부팅되면 다시 스캔하여 `<device>-02-app.zip`을 전송합니다.

## OLED 및 블루투스 호스트 이름

동글 OLED는 선택된 블루투스 프로필에 대해 **`저장된 별칭 → 자동 호스트 이름 → BT 1 … BT 5`** 순서로 이름을 표시합니다(USB 출력 중에도 선택된 프로필 기준으로 표시). 이름은 **영문 ASCII 최대 24자**를 지원하며, 길면 스크롤되고 한글 등 미지원 문자는 `?`로 표시됩니다. 이름과 별칭은 전원을 껐다 켜도 유지되며 `BT_CLR` 실행 시 삭제됩니다.

### 키보드에서 별칭 직접 편집

OLED 동글과 페어링된 프로필이 필요합니다(호스트가 오프라인이어도 가능):

1. `DEVICE` 레이어에서 편집할 프로필을 선택하고 모든 키에서 손을 뗍니다.
2. 왼쪽 바깥쪽·가운데 엄지 키(`L_AUX` + `L_FN`)를 50 ms 이내에 함께 누르고 유지해 `DEVICE`를 연 다음 **`R`(`BT name`)를 0.8초 이상 홀드**한 뒤 모든 키를 떼면 `BT n NAME` 편집 화면이 열립니다(ZMK Studio로 키맵을 덮어쓴 경우 `Edit BT host name (hold)`를 할당).
3. OS 언어/키맵과 무관하게 물리 QWERTY 배열로 입력합니다(좌측 끝 Shift 위치는 `-`/`_`, 빈 값으로 저장 시 자동 이름 복원, 60초 무입력 시 취소):

| 엄지 키 (좌 → 우) | 편집 기능 | OLED 표시 |
| --- | --- | --- |
| L_AUX | 취소 | `ESC` |
| L_FN | 백스페이스 | `<` |
| Space (홀드) | 상단열 숫자 `1–0` | `#` |
| Enter / R_NUM | 공백 | `_` |
| Tab / R_NAV (홀드) | 대문자 / `_` | `^` |
| Backspace | 저장 | `OK` |

![Connection states and host-name editor](images/oled-status.png)

![Bootloader modes, transfer progress and errors](images/oled-bootloader.png)

위 미리보기는 펌웨어 렌더링 코드로 생성한 이미지입니다. 기본 로컬 빌드는 `images/`를 갱신하고 `build/artifacts/`에 전체 PNG 세트를 생성합니다. CI에서는 수동 전체 빌드만 미리보기를 생성해 recovery 아티팩트에 포함합니다(단독 추출: `python3 scripts/export-oled.py`, `python3 scripts/export-status-oled.py`).

## 소스 출처 및 의존성 관리

[`Keycoon/zmk-config-totem`](https://github.com/Keycoon/zmk-config-totem)(`b66b405`)과 [`a741725193/zmk-sofle-dongle`](https://github.com/a741725193/zmk-sofle-dongle)(`d3f2f76`)의 Totem/동글 설정을 병합해 시작했습니다.

| 서브모듈 | 포크 저장소 | 비고 |
| --- | --- | --- |
| `zmk/` | [`80ROkWOC4j/zmk`](https://github.com/80ROkWOC4j/zmk) | ZMK 0.3 / Zephyr 3.5 + 배터리 커브(`f181b36`) + 호스트 이름 훅(로컬 모듈 `firmware/host-names/`) |
| `zmk-dongle-display/` | [`80ROkWOC4j/zmk-dongle-display`](https://github.com/80ROkWOC4j/zmk-dongle-display) | 업스트림 v0.3(`c6c4be1`) + 이름 위젯 훅 |
| `bootloader/` | [`80ROkWOC4j/nRF52_Bootloader`](https://github.com/80ROkWOC4j/nRF52_Bootloader) | [`meshtastic/nRF52_Bootloader` 2.6.0](https://github.com/meshtastic/nRF52_Bootloader/releases/tag/2.6.0)(`e75ad3f`, ARM GCC `12.3.Rel1`) 포크, Adafruit `nice_nano` 0.6.0 및 Seeed XIAO 보드 정의(`bootloader-config/LICENSE.upstream`), `0x20008010` NOLOAD RAM 기반 단일 리셋 OTA 정책 적용 |

### 상세 제품 정보
- `Keycoon/zmk-config-totem`
  - store: https://aliexpress.com/item/1005009718551409.html
  - doc: https://suns-shave-80u.craft.me/NDKH6lhuW8BzBi
  - repo: https://github.com/Keycoon/zmk-config-totem
  - base commit: `b66b405ff4aef822955360d705966ebfa996ea2c`
- `a741725193/zmk-sofle-dongle`
  - store: https://aliexpress.com/item/1005011640674919.html
  - doc: https://ae-pic-a1.aliexpress-media.com/kf/Se2ead0612b7448f2b4678e32ee36c0ecD.pdf
  - repo: https://github.com/a741725193/zmk-sofle-dongle
  - base commit: `d3f2f764d5324af0dbac1a680fabf33d930e6026`

### 의존성 업데이트

1. 포크 저장소에 변경 사항을 푸시한 뒤 새 커밋을 스테이징합니다(`git add zmk`, `zmk-dongle-display`, 또는 `bootloader`). `zmk/` 베이스 변경 시 배터리 커브 커스터마이징을 유지하세요.
2. `bootloader/` 업데이트 시 [`bootloader-config/source.json`](bootloader-config/source.json)의 `revision`과 `version`도 함께 맞춥니다.
3. [`config/west.lock.yml`](config/west.lock.yml)은 Zephyr 및 하위 west 모듈만 고정합니다. ZMK의 `app/west.yml`이 변경되면 [`config/west.yml`](config/west.yml)에 반영한 뒤 `./scripts/container.sh` 내부에서 잠금 파일을 갱신합니다:

```sh
west config manifest.file west.yml
west update --fetch-opt=--filter=tree:0
python3 scripts/freeze.py
west config manifest.file west.lock.yml
./scripts/setup.sh
```
