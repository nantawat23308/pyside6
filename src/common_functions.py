import ctypes
import logging
from pathlib import Path
import yaml
from typing import Dict
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def set_console_position(x, y):
    ctypes.windll.user32.SetWindowPos(ctypes.windll.kernel32.GetConsoleWindow(), 0, x, y, 0, 0, 0x0001)


def load_yaml_file(yaml_file) -> dict:
    """ Loads yaml file using safe_load and returns the data as dictionary"""
    if type(yaml_file) is Path:
        yaml_file = yaml_file.as_posix()
    with open(yaml_file, 'r') as fp_yaml:
        file_data = yaml.safe_load(fp_yaml)
    return file_data


class UserDict:
    def __init__(self):
        """create dict"""
        pass

    keys_user: Dict = {}


def to_fwf(df_in, fname: str | Path, tablefmt: str = "plain", append: bool = False):
    from tabulate import tabulate
    content = tabulate(df_in.values.tolist(), list(df_in.columns), tablefmt=tablefmt)
    if isinstance(fname, Path):
        fname = fname.as_posix()
    if append:
        write_config = 'a'
    else:
        write_config = 'w'
    with open(fname, write_config) as fp:
        fp.write(content)


def create_optical_cal_file(file_path):
    if type(file_path) is not Path:
        file_path = Path(file_path)
    wlm_cols = [f'WLM_Bay{bay_num:02d}(dB)' for bay_num in range(1, 71)]
    opm_cols = [f'OPM_Bay{bay_num:02d}(dB)' for bay_num in range(1, 71)]
    cal_cols = ['Iteration(#)', 'Station_ID(#)', 'Operator_ID(#)', 'Datetime(#)', 'PatchCordChange(bool)'] + \
               [val for pair in zip(wlm_cols, opm_cols) for val in pair]
    df_cal = pd.DataFrame(columns=cal_cols)
    to_fwf(df_cal, file_path.as_posix())


def write_date(file):
    df_in = pd.read_csv(file)
    df_in['DateTime(#)'] = pd.to_datetime(df_in['DateTime(#)'])


def plot_control_chart(bay, pl_file, file_c):
    df = pd.read_fwf(pl_file)
    df.fillna(0, inplace=True)
    df['Datetime(#)'] = pd.to_datetime(df['Datetime(#)'], format='%Y-%m-%d_%H-%M-%S')
    fig = plt.figure(figsize=(10, 10))
    for bay_num in bay:
        rgb = (np.random.random(), np.random.random(), np.random.random())
        plt.plot(df['Datetime(#)'], df[f'OPM_Bay{bay_num:02d}(dB)'], label=f'OPM_Bay{bay_num:02d}(dB)',
                 marker='o', linestyle='-', c=rgb)
    plt.style.use('ggplot')
    plt.grid(True)
    plt.legend(loc=(1.01, 0.7), fancybox=1)
    plt.title("Optical Power Meter by Date", pad=10)
    plt.xticks(rotation=45)
    plt.xlim(df['Datetime(#)'][0] - np.timedelta64(3, 'D'), df['Datetime(#)'].iloc[-1] + np.timedelta64(3, 'D'))
    plt.xlabel("Datetime(#)")
    plt.ylabel("Optical Power Meter (dB)")
    fig.savefig(f"{file_c}", dpi=fig.dpi, bbox_inches='tight')


def verify_limit(value, high, low, limit_name: str):
    if low <= value <= high:
        print(f"Pass Verify limit {limit_name}: {low} <= {value} <= {high}")
    else:
        raise ValueError(f"Fail Verify limit {limit_name}: {low} <= {value} <= {high}")


if __name__ == '__main__':
    ROOT_DIR = Path(__file__).parent.parent
    GUI_SETTINGS_DIR = ROOT_DIR.joinpath('gui_settings')
    INSTR_YAML_CONFIG = GUI_SETTINGS_DIR.joinpath('tosa_bay.yaml')
    data = load_yaml_file(INSTR_YAML_CONFIG)
    print(data)
