# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

# boot.py - 一个干净、安全的启动脚本

# 这个脚本会在设备启动时自动运行。
# 它的唯一任务是尝试执行 main.py。

# === FILE: boot.py ===
# boot.py
# Runs on boot. Initializes the system and starts main.py

# import sys
# import time
# import machine

# --- Optional: Enable WebREPL for wireless debugging ---
# If you want to enable WebREPL, uncomment the following two lines.
# Make sure to set a password first by running: 'import webrepl_setup' in the REPL
#
# import webrepl
# webrepl.start()

# --- Main Boot Logic with Error Handling ---
# try:
#     # Print a clear message to indicate the boot process has started
#     print("--- ESP32-S3 Sun Lamp: Booting ---")
# 
#     # Importing main.py will trigger the execution of the code
#     # inside the 'if __name__ == "__main__":' block.
#     import main
# 
# except Exception as e:
#     # This block will catch any FATAL errors that are not caught
#     # by your main.py script. This prevents the device from hanging.
#     print("\n!!! FATAL ERROR IN BOOT.PY !!!")
#     sys.print_exception(e)
# 
#     # Wait a moment to ensure the error message is fully transmitted
#     time.sleep(2)
# 
#     print("\n-> Resetting device to attempt recovery... <-")
#     machine.reset()

