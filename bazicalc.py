import os


class Hexagram:
    """Represents a hexagram and its related calculations."""

    def __init__(self, lines, hexagrams_dict):
        self.lines = lines  # List of 6 integers (6-9)
        self.hexagrams_dict = hexagrams_dict
        self.binary = "".join(["1" if x in [7, 9] else "0" for x in self.lines])
        self.name, self.explanation = hexagrams_dict.get(
            self.binary, ("未知卦", "未找到解释")
        )
        self.changed_hexagram = self.calculate_changed_hexagram()
        self.inverse_hexagram = self.calculate_inverse_hexagram()
        self.reverse_hexagram = self.calculate_reverse_hexagram()
        self.mutual_hexagram = self.calculate_mutual_hexagram()

    @staticmethod
    def load_hexagrams(file_path):
        hexagrams = {}
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines[1:]:
                parts = line.strip().split(", ")
                if len(parts) == 3:
                    gua, binary, jieshi = parts
                    hexagrams[binary] = (gua, jieshi)
        return hexagrams

    def calculate_changed_hexagram(self):
        changed_lines = []
        has_moving_line = False
        for x in self.lines:
            if x == 9:
                changed_lines.append(8)  # Old Yang changes to Yin
                has_moving_line = True
            elif x == 6:
                changed_lines.append(7)  # Old Yin changes to Yang
                has_moving_line = True
            else:
                changed_lines.append(x)
        if has_moving_line:
            return Hexagram(changed_lines, self.hexagrams_dict)
        else:
            return None  # No changing lines

    def calculate_inverse_hexagram(self):
        inverse_binary = "".join(["1" if b == "0" else "0" for b in self.binary])
        name, explanation = self.hexagrams_dict.get(
            inverse_binary, ("未知卦", "未找到解释")
        )
        return name, explanation

    def calculate_reverse_hexagram(self):
        reverse_binary = self.binary[::-1]
        name, explanation = self.hexagrams_dict.get(
            reverse_binary, ("未知卦", "未找到解释")
        )
        return name, explanation

    def calculate_mutual_hexagram(self):
        if len(self.binary) == 6:
            mutual_binary = self.binary[1:4] + self.binary[2:5]
            name, explanation = self.hexagrams_dict.get(
                mutual_binary, ("未知卦", "未找到解释")
            )
            return name, explanation
        else:
            return None, None

    def find_explanation_file(self, folder="guaci"):
        """Find the file corresponding to this hexagram's name in the given folder."""
        for file_name in os.listdir(folder):
            if self.name in file_name:
                file_path = os.path.join(folder, file_name)
                return file_path
        return None

    def output_explanation(self, file_type="本卦", folder="guaci"):
        """Output the explanation from the corresponding file."""
        file_path = self.find_explanation_file(folder)
        if file_path:
            print(f"\n{file_type}: {self.name} 对应的文件: {file_path}")
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                print(f"内容:\n{content}\n")
        else:
            print(f"未找到 {file_type} 对应的文件: {self.name}")


    def to_text(self):
        """Build EXACTLY what display() shows, but as a string."""
        out = []
        out.append("\n您的卦象:")
        reversed_lines = self.lines[::-1]
        for i, line in enumerate(reversed_lines):
            symbol = "---" if line in [7, 9] else "- -"
            moving = " O" if line == 9 else " X" if line == 6 else ""
            out.append(f"第 {6 - i} 爻: {symbol}{moving}")

        out.append(f"\n本卦: {self.name} - 解释: {self.explanation}")

        if self.changed_hexagram:
            out.append(f"变卦: {self.changed_hexagram.name} - 解释: {self.changed_hexagram.explanation}")
            # embed file contents instead of printing:
            out.append(self._explanation_file_text(file_type="本卦"))
            out.append(self.changed_hexagram._explanation_file_text(file_type="变卦"))
        else:
            out.append("变卦：没有动爻，故无变卦 - 404 Not Found。")
            out.append(self._explanation_file_text(file_type="本卦"))

        inverse_name, inverse_explanation = self.inverse_hexagram
        out.append(f"错卦: {inverse_name} - 解释: {inverse_explanation}")

        reverse_name, reverse_explanation = self.reverse_hexagram
        out.append(f"综卦: {reverse_name} - 解释: {reverse_explanation}")

        mutual_name, mutual_explanation = self.mutual_hexagram
        if mutual_name:
            out.append(f"互卦: {mutual_name} - 解释: {mutual_explanation}")
        else:
            out.append("互卦未找到。")

        return "\n".join(out)
    
    def _explanation_file_text(self, file_type="本卦", folder="guaci"):
        file_path = self.find_explanation_file(folder)
        if not file_path:
            return f"未找到 {file_type} 对应的文件: {self.name}\n"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"\n{file_type}: {self.name} 对应的文件: {file_path}\n内容:\n{content}\n"

    def display(self):
        print("\n您的卦象:")
        reversed_lines = self.lines[::-1]
        for i, line in enumerate(reversed_lines):
            symbol = "---" if line in [7, 9] else "- -"
            moving = " O" if line == 9 else " X" if line == 6 else ""
            print(f"第 {6 - i} 爻: {symbol}{moving}")

        print(f"\n本卦: {self.name} - 解释: {self.explanation}")
        # Output the explanation from file

        if self.changed_hexagram:
            print(
                f"变卦: {self.changed_hexagram.name} - 解释: {self.changed_hexagram.explanation}"
            )
            # Output the explanation for the changed hexagram
            self.output_explanation(file_type="本卦")
            self.changed_hexagram.output_explanation(file_type="变卦")
        else:
            print("变卦：没有动爻，故无变卦 - 404 Not Found。")
            self.output_explanation(file_type="本卦")

        inverse_name, inverse_explanation = self.inverse_hexagram
        print(f"错卦: {inverse_name} - 解释: {inverse_explanation}")

        reverse_name, reverse_explanation = self.reverse_hexagram
        print(f"综卦: {reverse_name} - 解释: {reverse_explanation}")

        mutual_name, mutual_explanation = self.mutual_hexagram
        if mutual_name:
            print(f"互卦: {mutual_name} - 解释: {mutual_explanation}")
        else:
            print("互卦未找到。")
