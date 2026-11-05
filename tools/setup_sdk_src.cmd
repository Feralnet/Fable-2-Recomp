@echo off
rem ===========================================================================
rem Fetch the ReXGlue SDK *source* into thirdparty\rexglue-sdk-src\ (relative
rem to the repo root) at the exact commit this project was built with, pin
rem its submodules to the recorded SHAs, and apply this project's local SDK
rem patch. No-op if already present.
rem
rem This is only needed for the optional Vulkan GPU plugin (see
rem tools/build_sdk_vulkan.cmd); the prebuilt-SDK game build does not use it.
rem
rem WARNING: this is a LONG clone (several GB of submodules).
rem
rem Pinned inputs (all in thirdparty/, tracked in this repo):
rem   rexglue-sdk-local.patch            - local SDK modifications (main-menu
rem                                        crash fix, Vulkan + FPS work)
rem   rexglue-sdk-fsr1-raster.patch      - gated FSR 1 / CAS raster present pass
rem   rexglue-sdk-perf-csv-and-vc-dump.patch - perf CSV recorder wiring + the
rem                                        Fable 2 vertex constant dump probe
rem   rexglue-sdk-submodule-pins.txt     - submodule SHAs the current DLLs
rem                                        were built against
rem ===========================================================================
setlocal
set "REPO=%~dp0.."
set "SRC=%REPO%\thirdparty\rexglue-sdk-src"
set "PATCH=%REPO%\thirdparty\rexglue-sdk-local.patch"
set "PATCH_FSR1=%REPO%\thirdparty\rexglue-sdk-fsr1-raster.patch"
set "PINS=%REPO%\thirdparty\rexglue-sdk-submodule-pins.txt"
set "PIN_COMMIT=f5337cdc947ff6d4c4196737e2c807a48f2a1fc2"

if exist "%SRC%\.git" (
    echo ReXGlue SDK source already present: %SRC%
    exit /b 0
)

where git >nul 2>nul
if errorlevel 1 (
    echo Error: git not found on PATH. Install Git for Windows first. 1>&2
    exit /b 1
)
if not exist "%PATCH%" (
    echo Error: missing %PATCH%; this file is tracked in the repo. 1>&2
    exit /b 1
)
if not exist "%PINS%" (
    echo Error: missing %PINS%; this file is tracked in the repo. 1>&2
    exit /b 1
)

if not exist "%REPO%\thirdparty" mkdir "%REPO%\thirdparty"

echo Cloning rexglue/rexglue-sdk (LONG: several GB of submodules)...
git clone https://github.com/rexglue/rexglue-sdk.git "%SRC%"
if errorlevel 1 (
    echo Error: SDK source clone failed. 1>&2
    exit /b 1
)

pushd "%SRC%"
git checkout -q %PIN_COMMIT%
if errorlevel 1 (
    echo Error: checkout of pinned commit %PIN_COMMIT% failed. 1>&2
    popd
    exit /b 1
)
git submodule update --init --recursive
if errorlevel 1 (
    echo Error: submodule update failed. 1>&2
    popd
    exit /b 1
)
rem Pin each submodule to the exact SHA this project's DLLs were built with.
for /f "usebackq tokens=1,2" %%a in (`findstr /v /c:"#" "%PINS%"`) do (
    echo   pin %%a -^> %%b
    git -C "%%a" checkout -q %%b
    if errorlevel 1 (
        echo Error: cannot pin %%a to %%b. 1>&2
        popd
        exit /b 1
    )
)
git apply --check "%PATCH%"
if errorlevel 1 (
    echo Error: local SDK patch does not apply cleanly. 1>&2
    popd
    exit /b 1
)
git apply "%PATCH%"
if errorlevel 1 (
    echo Error: applying local SDK patch failed. 1>&2
    popd
    exit /b 1
)
rem Optional second patch: the gated FSR 1 raster present pass (see
rem docs/FABLE2_UPSCALING_SPIKE.md). Applied only when present, and only when it
rem applies cleanly, so an older pinned SDK does not block the clone.
if exist "%PATCH_FSR1%" (
    git apply --check "%PATCH_FSR1%" >nul 2>&1
    if errorlevel 1 (
        echo Note: %PATCH_FSR1% does not apply to this SDK pin - skipping.
    ) else (
        git apply "%PATCH_FSR1%"
        if errorlevel 1 (
            echo Error: applying the FSR 1 raster SDK patch failed. 1>&2
            popd
            exit /b 1
        )
    )
)
rem Optional third patch: the perf CSV recorder wiring + the Fable 2 vertex
rem constant dump probe (see docs/FABLE2_UPSCALING_SPIKE.md section 8). These
rem were carried as undocumented local modifications before; without them the
rem tree at the pin is not reproducible. Same rule: only apply when it fits.
set "PATCH_PERF=%REPO%\thirdparty\rexglue-sdk-perf-csv-and-vc-dump.patch"
if exist "%PATCH_PERF%" (
    git apply --check "%PATCH_PERF%" >nul 2>&1
    if errorlevel 1 (
        echo Note: %PATCH_PERF% does not apply to this SDK pin - skipping.
    ) else (
        git apply "%PATCH_PERF%"
        if errorlevel 1 (
            echo Error: applying the perf CSV / vertex constant probe SDK patch failed. 1>&2
            popd
            exit /b 1
        )
    )
)
rem Optional fourth patch: make Presenter's layout independent of the rexui-
rem PRIVATE REX_HAS_FIDELITYFX_SDK define, and move OnGuestVblank() out of the
rem header into the exported table (see docs/FABLE2_UPSCALING_SPIKE.md section
rem 12). Without this the GPU plugin writes guest_vblank_count_ at the option-OFF
rem offset, which is ui_draw_next_iterator_ in the armed runtime. Must come after
rem the FSR patch, which introduces the conditional members it hoists.
set "PATCH_LAYOUT=%REPO%\thirdparty\rexglue-sdk-presenter-layout-invariant.patch"
if exist "%PATCH_LAYOUT%" (
    git apply --check "%PATCH_LAYOUT%" >nul 2>&1
    if errorlevel 1 (
        echo Note: %PATCH_LAYOUT% does not apply to this SDK pin - skipping.
    ) else (
        git apply "%PATCH_LAYOUT%"
        if errorlevel 1 (
            echo Error: applying the presenter layout-invariance SDK patch failed. 1>&2
            popd
            exit /b 1
        )
    )
)
popd

echo OK: ReXGlue SDK source at %SRC% (commit %PIN_COMMIT% + local patch)
endlocal
