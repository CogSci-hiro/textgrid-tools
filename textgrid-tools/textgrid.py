import os
from pathlib import Path
import re
from typing import Tuple

import pandas as pd


class TextGrid:
    def __init__(self, file_path: Path | str, names: Tuple[str] = ("tier", "start", "end", "annotation")):
        """
        Read annotation data from either Textgrid file (`TextGrid` or `textgrid`) or CSV file (`csv` or `CSV`)
        :param file_path:
        :type file_path: Path | str
        :param names: column names, defaults are (`tier`, `start`, `end`, `annotation`)
        :type names: Tuple[str]
        """

        self.file_path = Path(file_path)
        self.file_type = None
        self.object_class = None
        self.xmin = None
        self.xmax = None
        self.tiers = None
        self.n_tiers = None
        self.tier_list = []
        self.content = {"tier": [], "start": [], "end": [], "annotation": []}

        # Read file
        fname, extension = os.path.splitext(file_path)
        if extension in ["textgrid", "TextGrid"]:
            self._parse_textgrid()
        elif extension in ["csv", "CSV"]:
            self._parse_csv(names)
        else:
            raise ValueError(f"Unsupported file extension '{extension}'")

    def _parse_textgrid(self) -> None:
        """
        Parse textgrid file
        :return: None
        :rtype: None
        """

        with open(self.file_path, "r") as f:
            text = f.read()

        tier_header, tier_name = True, None
        for line in text.splitlines():

            # Header ###################################################################################################

            # File type = "ooTextFile"
            match = re.match(r"File\stype\s=\s\"(\w+)\"", line)
            if match:
                self.file_type = match.group(1)

            # Object class = "TextGrid"
            match = re.match(r"Object\sclass\s=\s\"(\w+)\"", line)
            if match:
                self.object_class = match.group(1)

            # xmin = 0.0
            match = re.match(r"xmin\s=\s(\d+\.\d+)", line)
            if match and tier_name is None:
                self.xmin = float(match.group(1))

            # xmax = 177.54
            match = re.match(r"xmax\s=\s(\d+\.\d+)", line)
            if match and tier_name is None:
                self.xmax = float(match.group(1))

            # tiers? <exists>
            match = re.match(r"tiers\?\s<(.*)>", line)
            if match:
                self.tiers = match.group(1)

            # size = 2
            match = re.match(r"size\s=\s(\d+)", line)
            if match:
                self.n_tiers = int(match.group(1))

            # Tier #####################################################################################################

            # item[1]:
            match = re.match(r"\s+item\s\[(\d+)]", line)
            if match:
                idx = int(match.group(1))
                tier_idx = idx - 1

                if tier_idx >= self.n_tiers:
                    raise ValueError(f"There are too many tiers, expected {self.n_tiers} but got {tier_idx}")

                tier_header = True

            # name = "phones"
            match = re.match(r"\s+name\s=\s\"(.*)\"", line)
            if match:
                tier_name = match.group(1)
                
            # intervals: size = 1882
            match = re.match(r"\s+intervals:\ssize\s=\s(\d+)", line)
            if match:
                n = int(match.group(1))
                self.content["tier"].extend([tier_name] * n)
                tier_header = False

            # xmin = 0.0
            match = re.match(r"\s+xmin\s=\s(\d*\.*\d*)", line)
            if match and not tier_header:
                start = float(match.group(1))
                self.content["start"].append(start)

            # xmax = 0.0
            match = re.match(r"\s+xmax\s=\s(\d*\.*\d*)", line)
            if match and not tier_header:
                end = float(match.group(1))
                self.content["end"].append(end)

            # text = "sil"
            match = re.match(r"\s+text\s=\s\"(.*)\"", line)
            if match and not tier_header:
                annotation = match.group(1)
                self.content["annotation"].append(annotation)

        self.tier_list = list(set(self.content["tier"]))

    def _parse_csv(self, names: Tuple[str]) -> None:
        """
        Read CSV file

        :param names: names of columns, defaults are
        :type names: Tuple[str]
        :return: None
        :rtype: None
        """

        df = pd.DataFrame(self.file_path)
        self.content["tier"] = list(df[names[0]])
        self.content["start"] = list(df[names[1]])
        self.content["end"] = list(df[names[2]])
        self.content["annotation"] = list(df[names[3]])

    def to_csv(self, file_path: str | Path) -> None:
        """
        Save the content to CSV

        :param file_path: path to save the result to
        :type file_path: str | Path
        :return: None
        :rtype: None
        """

        # Check extension
        fname, extension = os.path.splitext(file_path)
        if extension in ["textgrid", "TextGrid"]:
            raise ValueError(f"Invalid file extension for CSV '{extension}'")
        elif extension in ["csv", "CSV"]:
            pass
        else:
            raise ValueError(f"Unsupported file extension '{extension}'")

        df = pd.DataFrame(self.content)
        df.to_csv(file_path)

    def to_textgrid(self, file_path: str | Path) -> None:
        """
        Save the content to TextGrid

        :param file_path: path to save the result to
        :type file_path: str | Path
        :return: None
        :rtype: None
        """

        # Check extension
        fname, extension = os.path.splitext(file_path)
        if extension in ["textgrid", "TextGrid"]:
            pass
        elif extension in ["csv", "CSV"]:
            raise ValueError(f"Invalid file extension for textgrid '{extension}'")
        else:
            raise ValueError(f"Unsupported file extension '{extension}'")

        # Header
        text = ""
        text += f"File type = \"{self.file_type}\"\n"
        text += f"Object class = \"{self.object_class}\"\n"
        text += "\n"
        text += f"xmin {self.xmin}\n"
        text += f"xmax {self.xmax}\n"
        text += f"tiers? <{self.tiers}>\n"
        text += f"size = {self.n_tiers}\n"
        text += "item[]\n"

        last_tier, tier_idx, interval_idx = None, 1, 1
        for tier, start, end, annotation in zip(self.content["tier"], self.content["start"],
                                                self.content["end"], self.content["annotation"]):

            if last_tier != tier or last_tier is None:

                # Number of intervals in the tier
                tier_size = len([el for el in self.content["tier"] if el == tier])

                # Tier header
                text += f"\titem [{tier_idx}]\n"
                text += f"\t\tclass = \"IntervalTier\"\n"
                text += f"\t\tname = \"{tier}\"\n"
                text += f"\t\txmin = {self.xmin}\n"
                text += f"\t\txmax = {self.xmax}\n"
                text += f"\t\tintervals: size = {tier_size}\n"

                # Update
                last_tier = tier
                tier_idx += 1
                interval_idx = 1

            # Interval
            text += f"\t\t\tintervals [{interval_idx}]:\n"
            text += f"\t\t\t\txmin = {start}\n"
            text += f"\t\t\t\txmax = {end}\n"
            text += f"\t\t\t\ttext = \"{annotation}\"\n"

            interval_idx += 1

        with open(file_path, "w") as f:
            f.write(text)
