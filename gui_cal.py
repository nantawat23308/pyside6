import logging
import sys
import time
import traceback
from datetime import datetime
from multiprocessing import Manager
from os import system
import threading
from PySide6.QtCore import QTimer, Qt, QObject, Signal, Slot, QRunnable, QThreadPool, QTime
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, \
    QGridLayout, QLineEdit, QFrame, QTextEdit, QFormLayout, QCheckBox, QComboBox, QGroupBox, QScrollArea

from src.initialise_station_configs import STATION_NAME, LOG_Pl_FOLDER, \
    create_log_folders, LOGGING_YAML_CONFIG, Pl_FILE, TOSA_BAY_MAP, Pl_FOLDER
from src.station_equipment import OpticalInstrumentsLock
from gui_settings.setup_logging import start_logging_thread
from src.common_functions import set_console_position, UserDict, load_yaml_file
from src.path_lost_sequence import wait_time, osx_set_channel, read_opm_on_port, \
    crp_get_data, tosa_path_los, read_wlm_on_port, collect_data, setup_instrument_config, plot_by_data, \
    load_limit, power_laser_check
from src.ask_question import display_img, IMG_PATH


SW_VERSION = '2.0'
user_dict = UserDict.keys_user
user_dict['Bay_Available'] = load_yaml_file(TOSA_BAY_MAP)['bay_map']

class CaseTest:
    func = []
    seq_name_list = []
    kwargs = []
    trigger = []

    def __init__(self):
        pass

    def add_step(self, func, name, kwargs=None, trigger=False):
        self.func.append(func)
        self.seq_name_list.append(name)
        self.kwargs.append(kwargs)
        self.trigger.append(trigger)


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    Supported signals are:

    finished
        No data
    error
        tuple (exctype, value, traceback.format_exc() )
    result
        object data returned from processing, anything
    progress
        int indicating % progress

    """
    finished = Signal()
    error = Signal(tuple)
    result = Signal(list)
    progress = Signal(int)
    # chamber_temp = Signal(int)


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback:    The function callback to run on this worker thread. Supplied args and
                        kwargs will be passed through to the runner.
    :type callback:     function
    :param args:        Arguments to pass to the callback function
    :param kwargs:      Keywords to pass to the callback function

    """

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._finished = False
        self.kill = False

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @property
    def is_finished(self) -> bool:
        return self._finished

    @is_finished.setter
    def is_finished(self, finish_bool: bool):
        self._finished = bool(int(finish_bool))

    def kill(self):
        self.kill = True

    @Slot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            self._finished = False
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            logging.error(e)
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


class TestLED(QFrame):
    def __init__(self, label_str, parent=None, total_num=4):
        super().__init__(parent)
        led_height = 30
        led_width = int(480 / total_num)

        self.setFixedSize(led_width, led_height)
        self.setStyleSheet("background-color: gray; border: 1px solid black;")

        self.number_label = QLabel(label_str, self)
        self.number_label.setStyleSheet("color: white")
        self.number_label.setAlignment(Qt.AlignCenter)
        self.number_label.setGeometry(0, 0, led_width, led_height)

    def led_pass(self):
        self.setStyleSheet("background-color: green; border: 1px solid black;")

    def led_fail(self):
        self.setStyleSheet("background-color: red; border: 1px solid black;")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialise all gui features

        self.result = []
        self.case = CaseTest()
        self.func = self.case.func
        self.seq_name_list = self.case.seq_name_list
        self.kwargs = self.case.kwargs
        self.trigger = self.case.trigger

        self.check_test_equipment_button = QPushButton("Check Test Equipment")
        self.led_grid = QGridLayout()
        # self.progress_bar = QProgressBar()
        # self.check_tosa_bays_button = QPushButton("Path Loss Calibration")
        self.crp_label = QLabel("dB")
        self.start_button = QPushButton("Start Path Loss")
        self.abort_button = QPushButton("Abort")
        self.log_text_edit = QTextEdit()
        self.operator_input = QLineEdit()
        self.station_id_input = QLabel()
        self.software_version_input = QLabel()
        self.data_time = QLabel()

        # change path cord
        self.abort = False
        self.pl_worker = None
        self.led = None
        self.dummy = None
        self.path_cord = list()
        self.path_cord_dia = dict()
        for i in user_dict['Bay_Available']:
            box = QCheckBox(text=f"{i}")
            box.setObjectName(f"{i}")
            self.path_cord.append(box)
        self.path_cord_dia = [self.path_cord[x:x+14] for x in range(0, len(self.path_cord), 14)]
        self.scroll = QScrollArea()
        self.wid = QWidget()
        self.group_box = QGroupBox()
        self.lock = threading.Lock()
        self.label_list = []
        user_dict['Bay ID'] = 0
        user_dict['Label_count'] = 0
        # lcf
        self.lcf = QComboBox()
        # start call per board
        self.group_out = QGroupBox("Path Cord Change")

        self.timer = QTimer()
        self.timer_date = QTimer()
        self.threadpool = QThreadPool()
        self.threads_q = []

        # Define Main window settings
        self.setFixedSize(600, 800)
        self.setWindowTitle("Path Loss TOSA Calibration")

        # Create required variables
        self.leds = []
        self.tosa_worker = None
        self.equipment_worker = None
        self.calibration_worker = None
        self.threads = []
        self.equipment_leds = dict()
        self.equipment_serials = dict()
        self.elapsed_time = 0
        self._tosa_dict_list = []
        self._equipment_flag = False
        self._main_queue = Manager().Queue()
        self._logging_thread = None
        self.log_filename = None
        self._instr_dict = {'OPM': {'State': False, 'IDN': ''}, 'WLM': {'State': False, 'IDN': ''},
                            'OSW': {'State': False, 'IDN': ''}}

        # Path loss Vars

        self.crp_channel = None
        self.lcf_pow = None
        self.line = None
        user_dict['fail'] = False
        user_dict['Iteration(#)'] = None
        user_dict['Station_ID(#)'] = STATION_NAME
        user_dict['Operator_ID(#)'] = None
        user_dict['Datetime(#)'] = time.strftime('%Y-%m-%d_%H-%M-%S')
        user_dict['PatchCordChange(bool)'] = False
        user_dict['CRP(dB)'] = None
        user_dict['WLM_freq'] = None
        user_dict['WLM_SMSR'] = None
        user_dict['Channel LCF(#)'] = None
        for bay_num in range(1, 70):
            user_dict[f'WLM_Bay{bay_num:02d}(dB)'] = "0"
            user_dict[f'OPM_Bay{bay_num:02d}(dB)'] = "0"
            user_dict[f'Path_Cord_Change_Bay{bay_num:02d}(bool)'] = False

        # Setup calibration, UI, and console
        self.setup_calibration_path_loss_log()
        self.setup_ui()
        self.setup_console()

    def add_step(self, func, name, kwargs=None):

        self.func.append(func)
        self.seq_name_list.append(name)
        self.kwargs.append(kwargs)

    def log_message(self, message):
        logging.info(message)
        # time_now = time.strftime('%Y-%m-%d_%H:%M:%S')
        # self.log_text_edit.append(f"[{time_now}] {message}")

    def setup_ui(self):
        main_layout = QVBoxLayout()

        # Create the input fields
        form_layout = QFormLayout()

        # Set white background and black border for the QLabel widgets
        self.operator_input.setStyleSheet("background-color: white; border: 1px solid black;")
        self.station_id_input.setStyleSheet("background-color: white; border: 1px solid black;")
        self.software_version_input.setStyleSheet("background-color: white; border: 1px solid black;")
        self.data_time.setStyleSheet("background-color: white; border: 1px solid black;")

        self.station_id_input.setText(STATION_NAME)
        self.timer_date.timeout.connect(self.show_time_now)
        self.timer_date.start(1000)
        self.software_version_input.setText(SW_VERSION)

        # self.lcf.setStyleSheet("background-color: white; border: 1px solid black;")
        # self.lcf.setPlaceholderText("Select Line from Splitter 11-16")
        # self.lcf.addItems(['11', '12', '13', '14', '15', '16'])
        # self.lcf.currentTextChanged.connect(self.status_lcf)

        for path_cord in self.path_cord:
            path_cord.stateChanged.connect(self.status_patch_cord)

        form_layout.addRow("Operator:", self.operator_input)
        form_layout.addRow("Station ID:", self.station_id_input)
        form_layout.addRow("Software Version:", self.software_version_input)
        form_layout.addRow("Date Time:", self.data_time)

        v_dia_pl = QVBoxLayout()
        for key in self.path_cord_dia:
            lcf_slow = QHBoxLayout()
            for pl in key:
                lcf_slow.addWidget(pl)
            v_dia_pl.addLayout(lcf_slow)
        main_layout.addLayout(form_layout)
        self.group_out.setLayout(v_dia_pl)
        # Create the log text edit widget
        self.log_text_edit.setReadOnly(True)
        # main_layout.addWidget(self.log_text_edit)
        main_layout.addWidget(self.group_out)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        timer_layout = QHBoxLayout()
        self.start_button.setFixedSize(200, 40)
        self.start_button.setStyleSheet("QPushButton{font-size: 16pt;}")
        self.start_button.clicked.connect(self.start_cal)
        timer_layout.addWidget(self.start_button)

        self.abort_button.setFixedSize(120, 40)
        self.abort_button.setStyleSheet("QPushButton{font-size: 16pt;}")
        self.abort_button.clicked.connect(self.abort_cal)
        self.abort_button.setEnabled(False)
        timer_layout.addWidget(self.abort_button)

        self.crp_label.setStyleSheet("QLabel{font-size: 16pt; background-color: white; border: 1px solid black;}")
        self.crp_label.setAlignment(Qt.AlignCenter)
        self.crp_label.setFixedSize(240, 40)
        timer_layout.addWidget(self.crp_label)
        main_layout.addLayout(timer_layout)

        bays_and_progress_bar = QHBoxLayout()
        main_layout.addLayout(bays_and_progress_bar)
        layout_bay = QHBoxLayout()

        # self.group_out.setFixedWidth(400)
        self.led_grid.setSpacing(10)
        layout_bay.addLayout(self.led_grid)
        # ----------------------------------------------------------------------------------------------
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        for seq in range(len(self.seq_name_list)):
            les = LabelBOX(f"{self.seq_name_list[seq]}")
            les.setFixedHeight(50)
            self.label_list.append(les)
            form_layout.addRow(les)
        self.group_box.setLayout(form_layout)
        self.scroll.setWidget(self.group_box)
        self.scroll.setWidgetResizable(True)
        layout_bay.addWidget(self.scroll)
        main_layout.addLayout(layout_bay)
        self.check_test_equipment_button.clicked.connect(self.check_test_equipment)
        main_layout.addWidget(self.check_test_equipment_button)

        equipment_layout = QHBoxLayout()
        equip_list = ["WLM", "OPM", "OSW", "LS"]

        for name in equip_list:
            equipment_box = QVBoxLayout()

            equipment_led = TestLED(label_str=name, total_num=len(equip_list))
            self.equipment_leds[name] = equipment_led
            equipment_box.addWidget(equipment_led)

            equipment_serial = QLineEdit()
            equipment_serial.setPlaceholderText(f"{name} Serial")
            equipment_serial.setReadOnly(True)
            self.equipment_serials[name] = equipment_serial
            equipment_box.addWidget(equipment_serial)
            equipment_layout.addLayout(equipment_box)

        main_layout.addLayout(equipment_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def abort_cal(self):
        logging.info("Press Abort")
        self.abort = True
        self.abort_button.setEnabled(False)
        self.threadpool.globalInstance().waitForDone()
        self.threadpool.deleteLater()
        logging.info("Aborted")

    def start_cal(self):
        if self.operator_input.text() == '':
            self.log_message('Can not start calibration until an Operator Id has been entered.')
            return
        user_dict['Channel LCF(#)'] = self.line
        user_dict['Operator_ID(#)'] = self.operator_input.text()
        logging.info(f"Operator: {user_dict['Operator_ID(#)']}")
        self.log_message("Start Calibration Patch Loss")
        self.operator_input.setEnabled(False)
        self.start_button.setEnabled(False)
        self.abort_button.setEnabled(True)

        work = Worker(self.start_cal_seq)
        work.signals.progress.connect(self.running_path_loss_cal)
        work.signals.finished.connect(self.finish_seq)
        work.signals.error.connect(self.handle_error)
        self.pl_worker = work
        self.threads_q.append(self.pl_worker)
        self.threadpool.start(work)

    def handle_error(self, error_tup):
        logging.error(error_tup)
        self.log_message(f'Failure occured: {error_tup}')

    def finish_seq(self):
        logging.info("End Sequence")
        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)

    def ret_finish_seq(self):
        if False in self.result:
            user_dict['fail'] = True
        if self.abort is True or self.result[user_dict['Label_count']] is False or False in self.result:
            self.label_list[user_dict['Label_count']].failed()
        else:
            self.label_list[user_dict['Label_count']].passed()

        if user_dict['Label_count'] != (len(self.label_list) - 1):
            self.label_list[user_dict['Label_count'] + 1].running()
        user_dict['Label_count'] += 1

    def finish_path_loss_cal(self):
        to_sa_bay = user_dict['Bay ID']
        if self.abort is True:
            self.leds[to_sa_bay // 7][to_sa_bay % 7].failed()
        else:
            self.log_message(f"Run Cal PASS at TOSA BAY: {to_sa_bay + 1}")
            self.leds[to_sa_bay // 7][to_sa_bay % 7].passed()
            if to_sa_bay % 7 == 6 and to_sa_bay != 69:
                self.leds[to_sa_bay // 7 + 1][0].running()
            elif to_sa_bay == 69:
                pass
            else:
                self.leds[to_sa_bay // 7][to_sa_bay % 7 + 1].running()
        user_dict['Bay ID'] += 1

    def running_path_loss_cal(self):
        to_sa_bay = user_dict['Bay ID']
        self.leds[to_sa_bay // 7][to_sa_bay % 1].running()

    def start_cal_seq(self, progress_callback=None):
        for ite in range(len(self.func)):
            if user_dict['CRP(dB)'] is not None:
                self.crp_label.setText(f"{user_dict['CRP(dB)']} dB")
            if self.abort is False:
                time.sleep(0.01)
                try:
                    if self.kwargs[ite] is None:
                        self.func[ite]()
                    else:
                        self.func[ite](**self.kwargs[ite])

                    self.result.append(True)
                except Exception as e:
                    logging.error(e)
                    self.result.append(False)

            else:
                self.result.append(False)
            self.ret_finish_seq()

    def setup_calibration_path_loss_log(self):
        # Ensure Log & Data folders exist
        create_log_folders()
        # Start logging thread
        self.log_filename = LOG_Pl_FOLDER.joinpath(f'MainLog_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log')
        self._logging_thread = start_logging_thread(log_cfg_yaml=LOGGING_YAML_CONFIG, q_in=self._main_queue,
                                                    log_filename=self.log_filename.as_posix())

    @staticmethod
    def setup_console():
        # Add caption to window
        title = f'TOSA Calibration V{SW_VERSION} - {STATION_NAME}'
        system("title " + title)
        set_console_position(0, 0)

    def show_time_now(self):
        current_time = QTime.currentTime()
        label_time = current_time.toString('hh:mm:ss')
        self.data_time.setText(label_time)

    def check_test_equipment(self):
        self.log_message("Checking that all the test equipment is present...")
        self.check_test_equipment_button.setEnabled(False)
        self.start_button.setEnabled(False)

        # Pass the function to execute
        worker = Worker(self.check_test_equipment_worker)
        worker.signals.finished.connect(self.check_test_equipment_finished)
        self.equipment_worker = worker
        # Execute
        self.threadpool.start(worker)

    def check_test_equipment_worker(self, progress_callback=None):
        self._equipment_flag = True
        try:
            with OpticalInstrumentsLock(tosa_snr='CalStationCheck', tosa_bay=1) as opt_instr:
                self._instr_dict = opt_instr.check_instruments(out_dict=self._instr_dict)
        except Exception as e:
            logging.error(e)
            traceback.print_exc()
            self._equipment_flag = False
            self.log_message('All optical instruments not found. Please check that they are powered on and connected.')

    def check_test_equipment_finished(self):
        for name, info in self._instr_dict.items():
            led = self.equipment_leds[name]
            serial = self.equipment_serials[name]

            if info['State']:
                led.led_pass()
                text_str = f'{name} found:'.ljust(30)
                self.log_message(f'{text_str}{info["IDN"]}')
                serial.setText(info['IDN'])
            else:
                led.led_fail()
        self.check_test_equipment_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.equipment_worker.is_finished = True

    def status_patch_cord(self):
        for path_cord in self.path_cord:
            path_cord.text()
            if path_cord.stateChanged:
                if path_cord.isChecked():
                    user_dict[f'Path_Cord_Change_Bay{int(path_cord.text()):02d}(bool)'] = True
                else:
                    user_dict[f'Path_Cord_Change_Bay{int(path_cord.text()):02d}(bool)'] = False

    def status_lcf(self, line):
        self.lcf.setEnabled(False)
        self.line = line
        self.log_message(f"Laser Calibration Fiber Line: {line}")

    def status_information(self):
        user_dict['Operator_ID(#)'] = self.operator_input.text()




class ButtonTestBoard(QFrame):
    def __init__(self, number, **kwargs):
        super().__init__(**kwargs)
        self.setFixedSize(50, 20)
        self.setStyleSheet("background-color: gray; border: 1px solid black;")

        self.number_label = QLabel(f"{number:02d}", self)
        self.number_label.setStyleSheet("color: white")
        self.number_label.setGeometry(0, 0, 50, 20)

    def running(self):
        self.number_label.setStyleSheet("color: black")
        self.setStyleSheet("background-color: yellow; border: 1px solid black;")

    def passed(self):
        self.number_label.setStyleSheet("color: white")
        self.setStyleSheet("background-color: green; border: 1px solid black;")

    def failed(self):
        self.setStyleSheet("background-color: red; border: 1px solid black;")


class LabelBOX(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedHeight(50)
        self.setStyleSheet("color: white;"
                           "background-color: gray; "
                           "border: 1px solid black;")

    def running(self):
        self.setStyleSheet("background-color: yellow; border: 1px solid black;")

    def passed(self):
        self.setStyleSheet("background-color: green; border: 1px solid black;")

    def failed(self):
        self.setStyleSheet("background-color: red; border: 1px solid black;")


def main():
    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print('running in a PyInstaller bundle')
    else:
        print('running in a normal Python process')
    import faulthandler
    faulthandler.enable()
    # load bay config
    bay = load_yaml_file(TOSA_BAY_MAP)
    app = QApplication(sys.argv)
    case = CaseTest()
    # sequence measure reference power
    case.add_step(load_limit, name="Initial Station")
    case.add_step(display_img, name="Turn On Laser Source Module",
                  kwargs={"question": "Turn On Laser Source Module",
                          'picture': IMG_PATH.joinpath('LS_module.JPG')})
    case.add_step(display_img, name="Turn On Laser Source Application",
                  kwargs={"question": "Turn On Laser Source Application",
                          'picture': IMG_PATH.joinpath('LS_cont.JPG')})
    case.add_step(wait_time, name="Wait for Laser Source Stable 15 minutes", kwargs={'wait': 0})  # stable 15
    case.add_step(display_img, name="Connect Power Meter With LC line to Calibration",
                  kwargs={"question": "Connect Power Meter With LC line to Calibration",
                          'picture': IMG_PATH.joinpath('PWM_LC.JPG')})
    case.add_step(setup_instrument_config, name="Setup Instrument")
    case.add_step(crp_get_data, name="Read CRP (Calibration reference power)")
    case.add_step(display_img, name="Disconnect LC Cable and use for calibration",
                  kwargs={"question": "Disconnect LC Cable and use for calibration",
                          'picture': IMG_PATH.joinpath('PWM_LC.JPG')})
    case.add_step(display_img, name="Connect Power Meter FC line back to OPM",
                  kwargs={"question": "Connect Power Meter FC line back to OPM",
                          'picture': IMG_PATH.joinpath('PWM_FC.JPG')})
    # sequence measure path loss
    for i in user_dict['Bay_Available']:
        case.add_step(display_img, name="Bay {}: Clean and Inspect Source ".format(i),
                      kwargs={"question": "Clean and Inspect Optic Cable {}".format(i),
                              'picture': IMG_PATH.joinpath('CLEAN.JPG')})
        case.add_step(display_img, name="Bay {}: Use LC Calibration fiber connect".format(i),
                      kwargs={"question": f"Use LC Calibration fiber connect {i}",
                              'picture': IMG_PATH.joinpath('LCF_toBay.JPG')})
        case.add_step(osx_set_channel, name="Bay {}: Set OSW to TOSA Bay number".format(i), kwargs={"channel": i})
        case.add_step(read_wlm_on_port, name="Bay {}: Set WLM measure on Port".format(i), kwargs={"bay": i})
        case.add_step(read_opm_on_port, name="Bay {}: Set OPM measure on Port".format(i), kwargs={"bay": i})
        case.add_step(tosa_path_los, name="Bay {}: Collect Data From Port".format(i), kwargs={"bay": i})
    case.add_step(display_img, name="Confirm power End",
                  kwargs={"question": "Connect Power Meter With LC Confirm power End",
                          'picture': IMG_PATH.joinpath('PWM_LC.JPG')})
    case.add_step(power_laser_check, name="Verify Power End", kwargs={"tolerance": 1})  # tolerance 1 %
    case.add_step(collect_data, name="Collect Data File Patch Loss", kwargs={"filename": Pl_FILE})
    case.add_step(plot_by_data, name="Collect Data File Patch Loss", kwargs={"bay": user_dict['Bay_Available'],
                                                                             "pl_file": Pl_FILE,
                                                                             "pl_folder": Pl_FOLDER})
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
