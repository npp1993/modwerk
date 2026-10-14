# SPDX-License-Identifier: MIT
"""Host C flags the SDK tests share. MinGW (the Windows CI) links no ASan/UBSan runtime, so the sanitizers run where the
compiler has them (Linux, macOS) and the same host programs run without them on Windows."""
import os

SANITIZE = () if os.name == 'nt' else ('-fsanitize=address,undefined',)
