// fable_2 - Guest-frame capture hotkey (Release-safe).
//
// WHY
// The presenter and the guest both touch the final picture, so "the frame looks
// wrong" is ambiguous until the guest's own output is separated from the
// presenter's scale/letterbox. Presenter::CaptureGuestOutput reads the guest
// output texture straight off the GPU - the guest's frame BEFORE any host-side
// scaling - and src/diagnostics/fable2_frame_capture.h turns it into a PNG.
// Until now the only caller was the TCP remote-control server, which is
// #ifdef'd out of Release builds (CMakeLists.txt, FABLE2_REMOTE_CONTROL), so a
// shipped build could not produce this diagnostic at all.
//
// WHAT
// One keypress -> one PNG of the current guest frame, next to the exe (or in
// [screenshot] dir). No socket, no Debug build, no ImGui.
//
// HOW
//   * `screenshot_key` is polled per frame from the host input driver, exactly
//     like the F5 Lua hotkey (edge-detected, window must be focused).
//   * The readback itself runs on a short-lived detached thread. That is the
//     same shape as the proven remote-control path: D3D12Presenter::
//     CaptureGuestOutput takes the guest-output mailbox consumer lock and does
//     a fence-waited copy, so it is safe off the UI thread - and it must NOT
//     run on the guest thread, which is where the hotkey poll happens.
//
// OFF BY DEFAULT: `screenshot_key` is empty, so a normal run installs no
// thread and writes no file. Enable per run:
//     --screenshot_key F9            (or REX_SCREENSHOT_KEY=F9)
//     --screenshot_dir screenshots   (default "screenshots")
//
// The file name carries the guest frame size and a counter, e.g.
// screenshots/guest-2560x1440-001.png.

#pragma once

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <mutex>
#include <string>
#include <system_error>
#include <thread>
#include <filesystem>

#include <rex/cvar.h>
#include <rex/logging/macros.h>
#include <rex/runtime.h>
#include <rex/ui/presenter.h>
#include <rex/ui/virtual_key.h>
#include <rex/ui/window.h>

#include "fable2_frame_capture.h"

REXCVAR_DEFINE_STRING(
    screenshot_key, "",
    "Diagnostics",
    "Host key that writes a PNG of the guest's own rendered frame (the guest "
    "output, before the presenter scales or letterboxes it). Empty = off. "
    "Any key name rex::ui::ParseVirtualKey understands, e.g. F9.");
REXCVAR_DEFINE_STRING(
    screenshot_dir, "screenshots",
    "Diagnostics",
    "Directory for screenshot_key captures, relative to the exe directory.");

namespace fable2::screenshot {

// Window keeps presenter() protected; Window is a non-final polymorphic base
// with Window as its only/first base and presenter() is a non-virtual inline,
// so the derived-class accessor idiom reads the member safely (same idiom as
// Fable2App::GetWindowPresenter).
class WindowPresenterAccessor final : public rex::ui::Window {
 public:
  rex::ui::Presenter* PresenterPtr() const { return presenter(); }
};

inline rex::ui::Window* GameWindow() {
  auto* rt = rex::Runtime::instance();
  return rt ? rt->display_window() : nullptr;
}

inline std::atomic<bool>& Pending() {
  static std::atomic<bool> pending{false};
  return pending;
}

// Per-frame, host input thread. Edge-detects `screenshot_key` and latches a
// request; the capture itself happens on its own thread.
inline void poll_hotkey() {
  static bool down_prev = false;
  const std::string key = REXCVAR_GET(screenshot_key);
  if (key.empty()) {
    down_prev = false;
    return;
  }
  const uint16_t vk =
      static_cast<uint16_t>(rex::ui::ParseVirtualKey(key));
  if (vk == 0) return;  // unknown key name: stay off, do not spam
#ifdef _WIN32
  // Gate on the game window being foreground, like every other hotkey here, so
  // a capture cannot fire from an alt-tabbed desktop.
  rex::ui::Window* win = GameWindow();
  const HWND hwnd =
      win ? reinterpret_cast<HWND>(win->GetNativeWindowHandle()) : nullptr;
  const bool focused =
      hwnd != nullptr && (GetForegroundWindow() == GetAncestor(hwnd, GA_ROOT));
  const bool down = focused && (GetAsyncKeyState(vk) & 0x8000) != 0;
#else
  const bool down = false;
#endif
  if (down && !down_prev) Pending().store(true);
  down_prev = down;
}

// Writes one PNG of the guest output now. Returns the path on success.
inline std::string CaptureNow(const std::string& dir_hint) {
  rex::ui::Window* win = GameWindow();
  if (!win) return {};
  auto* presenter =
      reinterpret_cast<const WindowPresenterAccessor*>(win)->PresenterPtr();
  if (!presenter) return {};

  static std::mutex counter_mtx;
  static int counter = 0;
  int index;
  {
    std::lock_guard<std::mutex> lock(counter_mtx);
    index = ++counter;
  }

  std::filesystem::path dir(dir_hint.empty() ? "screenshots" : dir_hint);
  std::error_code ec;
  std::filesystem::create_directories(dir, ec);

  char name[64];
  std::snprintf(name, sizeof name, "guest-%03d.png", index);
  const std::string path = (dir / name).string();
  const auto result = framecapture::CaptureGuestOutputToPng(presenter, path);
  if (!result.ok) {
    REXSYS_WARN("[screenshot] capture failed: {}", result.error);
    return {};
  }
  REXSYS_INFO("[screenshot] guest frame {}x{} -> {} ({} bytes, luma {})",
              result.width, result.height, path, result.bytes, result.avg_luma);
  return path;
}

// Consumes a latched request on its own thread. Call once per guest frame
// (cheap: one atomic load when nothing is pending).
inline void poll_capture() {
  if (!Pending().exchange(false)) return;
  const std::string dir = REXCVAR_GET(screenshot_dir);
  std::thread([dir] { CaptureNow(dir); }).detach();
}

}  // namespace fable2::screenshot
