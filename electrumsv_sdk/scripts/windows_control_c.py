import ctypes
import sys

# This passes on Windows, but not MacOS or Linux.
kernel = ctypes.windll.kernel32 # type: ignore

pid = int(sys.argv[1])
kernel.FreeConsole()
kernel.AttachConsole(pid)
kernel.SetConsoleCtrlHandler(None, 1)
kernel.GenerateConsoleCtrlEvent(0, 0)
sys.exit(0)
