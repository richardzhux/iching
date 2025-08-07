import sys
import os
import io


class TeeLogger(io.StringIO):
    def __init__(self, output_dir="/User/rx/Documents/Hexarchive"):
        super().__init__()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.original_stdout = sys.stdout

    def write(self, s):
        # Write both to buffer and to terminal
        super().write(s)
        self.original_stdout.write(s)
        self.original_stdout.flush()

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_value, tb):
        sys.stdout = self.original_stdout

    def save(self):
        files = [f for f in os.listdir(self.output_dir) if f.endswith('.txt') and f[:6].isdigit()]
        nums = sorted([int(f[:6]) for f in files]) if files else []
        idx = nums[-1] + 1 if nums else 1
        fname = os.path.join(self.output_dir, f"{idx:06d}.txt")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(self.getvalue())
        print(f"\n【本次占卜已自动保存到文件】: {fname}")
        return fname
