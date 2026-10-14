from pathlib import Path
from pandas import DataFrame, ExcelFile

XLSX_PATH = Path(__file__).parent / "gams" / "input_UC_IEEE24.xlsx"
# XLSX_PATH = Path(__file__).parent / "gams" / "input_UC.xlsx"

class Data():
    def __init__(self, max_periods: int = 24):
        excel_file: ExcelFile = ExcelFile(XLSX_PATH)
        self.lines: DataFrame = excel_file.parse('line_admittance', index_col=0)
        self.generators: DataFrame = excel_file.parse('gen', index_col=0)
        self.gen_cost: DataFrame = excel_file.parse('gen_cost', index_col=0)
        self.gen_su_cost: DataFrame = excel_file.parse('gen_su_cost', index_col=0)
        self.loads: DataFrame = excel_file.parse('load', index_col=0)
        self.wind: DataFrame = excel_file.parse('wind', index_col=0)
        self.bess: DataFrame = excel_file.parse('bess', index_col=0)
        
        # sets
        self.s_lines: list = list(self.lines.index)
        self.s_generators: list = list(self.generators.index)
        self.s_blocks: list = [f'b{i}' for i in range(1, 4)]
        self.s_segments: list = [f'j{i}' for i in range(1, 9)]
        self.s_bus: list = list(self.loads.columns)
        self.s_wind: list = list(self.wind.columns)
        self.s_periods: list = list(self.loads.index[:max_periods])
        self.s_bess: list = list(self.bess.index)

        # Assert every block is within the colums of generatoros
        for block in self.s_blocks:
            assert block in self.generators.columns, f"Block {block} is not in generator columns"

        # Assert every segment is within the colums of generatoros
        for segment in self.s_segments:
            assert segment in self.generators.columns, f"Segment {segment} is not in generator columns"

if __name__ == "__main__":
    data = Data()