"""Read-only future preflight clock probe. Does not write or change services."""
import json
from pathlib import Path
import time

if __name__ == '__main__':
    print(json.dumps({'monotonic': time.monotonic(),
                      'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
