import sys
import os
import io

class TeeLogger(io.StringIO):
    def __init__(self, output_dir):
        super().__init__()
        self._output_dir = os.path.expanduser(output_dir)
        os.makedirs(self._output_dir, exist_ok=True)
        self.original_stdout = sys.stdout

    @property
    def output_dir(self):
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value):
        # Always expand ~ and create directory
        self._output_dir = os.path.expanduser(value)
        os.makedirs(self._output_dir, exist_ok=True)

    # ...rest unchanged...
    def write(self, s):
        super().write(s)
        self.original_stdout.write(s)
        self.original_stdout.flush()

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_value, tb):
        sys.stdout = self.original_stdout

    def save(self):
        files = [f for f in os.listdir(self._output_dir) if f.endswith('.txt') and f[:4].isdigit()]
        nums = sorted([int(f[:4]) for f in files]) if files else []
        idx = nums[-1] + 1 if nums else 1
        fname = os.path.join(self._output_dir, f"{idx:04d}.txt")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(self.getvalue())
        print(f"【本次占卜已自动保存到文件】: {fname}\n")
        return fname
