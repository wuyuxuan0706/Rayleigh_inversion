import sys

from PySide6 import QtCore

from Window.ui_main import *

basedir = os.path.dirname(__file__)

try:
    from ctypes import windll  # Only exists on Windows.

    myappid = 'mycompany.myproduct.subproduct.version'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass


class MainWindow(QMainWindow):
    def __init__(self):

        super().__init__()

        self.read_button_clicked = False

        self.ui = UI_MainWindow()
        self.ui.initUI(self)

        self.settings = Settings()

        self.file_path = self.ui.file_path_line_edit.text() + '/'
        self.save_path = self.ui.save_path_line_edit.text()
        self.Meridian_path = self.ui.Meridian_path_line_edit.text() + '/'
        self.SABER_path = self.ui.SABER_path_line_edit.text() + '/'
        self.station = self.ui.station_select.currentText()
        self.den_refer = self.ui.drh_line_edit.value()
        self.temp_refer = self.ui.trh_line_edit.value()

        self.station_info = self.settings.items["Station"][self.station]["station_info"]
        self.file_header = self.settings.items["Station"][self.station]["File_header"]
        self.coordinates = self.settings.items["Station"][self.station]["Coordinates"]
        self.error_threshold = self.settings.items["Station"][self.station]["Error_threshold"]
        self.altitude = self.settings.items["Station"][self.station]["Altitude"]

        self.Photon = None
        self.Height = None
        self.date_time_obj = None
        self.H_standard = None
        self.Density = None
        self.Temperature = None
        self.hour_time = None

        self._plot_ref_photon = None
        self._plot_ref_density = None
        self._plot_ref_temperature = None

        self.current_column_photon = 0
        self.current_column_density = 0
        self.current_column_temperature = 0

        self.timer_photon = QtCore.QTimer()
        self.timer_density = QtCore.QTimer()
        self.timer_temperature = QtCore.QTimer()

        self.timer_photon.setInterval(200)
        self.timer_density.setInterval(1000)
        self.timer_temperature.setInterval(1000)

        self.ui.file_path_line_edit.textEdited.connect(self.update_file_path)

        self.ui.file_path_button.clicked.connect(self.btn_clicked)
        self.ui.save_path_button.clicked.connect(self.btn_clicked)
        self.ui.Meridian_path_button.clicked.connect(self.btn_clicked)
        self.ui.SABER_path_button.clicked.connect(self.btn_clicked)

        self.ui.drh_line_edit.valueChanged.connect(self.update_den_refer)
        self.ui.trh_line_edit.valueChanged.connect(self.update_temp_refer)
        self.ui.read_data.clicked.connect(self.btn_clicked)

        self.timer_photon.timeout.connect(self.update_plot_photon)
        self.ui.play_button1.clicked.connect(self.start_plotting_photon)
        self.ui.pause_button1.clicked.connect(self.pause_plotting_photon)

        self.timer_density.timeout.connect(self.update_plot_density)
        self.ui.play_button2.clicked.connect(self.start_plotting_density)
        self.ui.pause_button2.clicked.connect(self.pause_plotting_density)

        self.timer_temperature.timeout.connect(self.update_plot_temperature)
        self.ui.play_button3.clicked.connect(self.start_plotting_temperature)
        self.ui.pause_button3.clicked.connect(self.pause_plotting_temperature)

        self.show()

    def update_file_path(self):
        self.file_path = self.ui.file_path_line_edit.text() + '/'

    def update_den_refer(self):
        self.den_refer = self.ui.drh_line_edit.value()

    def update_temp_refer(self):
        self.temp_refer = self.ui.trh_line_edit.value()

    def btn_clicked(self):
        if not is_valid_path(self.file_path):
            path_message_box()
            return
        sender = self.sender()
        if sender == self.ui.read_data:
            self.ui.progress_bar.setVisible(True)
            self.ui.progress_bar.setValue(0)

            if self.read_button_clicked:
                if self.timer_photon.isActive():
                    self.timer_photon.stop()
                if self.timer_density.isActive():
                    self.timer_density.stop()
                if self.timer_temperature.isActive():
                    self.timer_temperature.stop()

                self.Photon = None
                self.Height = None
                self.date_time_obj = None
                self.H_standard = None
                self.Density = None
                self.Temperature = None
                self.hour_time = None
                while self.ui.plot1.axes.lines:
                    self.ui.plot1.axes.lines[0].remove()
                while self.ui.plot2.axes.lines:
                    self.ui.plot2.axes.lines[0].remove()
                while self.ui.plot3.axes.lines:
                    self.ui.plot3.axes.lines[0].remove()

                self.ui.plot1.axes.set_title('')
                self.ui.plot2.axes.set_title('')
                self.ui.plot3.axes.set_title('')

                self.ui.plot1.draw()
                self.ui.plot2.draw()
                self.ui.plot3.draw()

                self._plot_ref_photon = None
                self._plot_ref_density = None
                self._plot_ref_temperature = None
                self.current_column_photon = 0
                self.current_column_density = 0
                self.current_column_temperature = 0

            self.read_button_clicked = True
            self.read_data_in_background()

        if sender == self.ui.file_path_button:
            self.file_path = self.ui.file_path_line_edit.text()
            self.settings.items['File_path'] = self.file_path
            self.settings.serialize()

        if sender == self.ui.save_path_button:
            self.save_path = self.ui.save_path_line_edit.text()
            self.settings.items['Save_path'] = self.save_path
            self.settings.serialize()

        if sender == self.ui.Meridian_path_button:
            self.Meridian_path = self.ui.Meridian_path_line_edit.text()
            self.settings.items['Meridian_path'] = self.Meridian_path
            self.settings.serialize()

        if sender == self.ui.SABER_path_button:
            self.SABER_path = self.ui.SABER_path_line_edit.text()
            self.settings.items['SABER_path'] = self.SABER_path
            self.settings.serialize()

    def start_plotting_photon(self):
        if self.file_path is None or self.file_path == "":
            path_message_box()
        elif self.timer_photon.isActive():
            self.timer_photon.stop()
            if process_message_box():
                self.reset_plotting_photon()
        else:
            self.timer_photon.start()

    def start_plotting_density(self):
        if self.file_path is None or self.file_path == "":
            path_message_box()
        elif self.timer_density.isActive():
            self.timer_density.stop()
            if process_message_box():
                self.reset_plotting_density()
        else:
            self.timer_density.start()

    def start_plotting_temperature(self):
        if self.file_path is None or self.file_path == "":
            path_message_box()
        elif self.timer_temperature.isActive():
            self.timer_temperature.stop()
            if process_message_box():
                self.reset_plotting_temperature()
        else:
            self.timer_temperature.start()

    def update_plot_photon(self):
        axes = self.ui.plot1.axes
        current_column = self.current_column_photon
        plot_ref = self._plot_ref_photon
        column_data = [row[current_column] for row in self.Photon]
        title_data = self.date_time_obj[current_column]
        if plot_ref is None:
            plot_refs = axes.semilogy(self.Height, column_data, '-b')
            self._plot_ref_photon = plot_refs[0]
        else:
            plot_ref.set_ydata(column_data)
            axes.set_title(title_data)

        self.current_column_photon = current_column + 1 if current_column < len(self.Photon[0]) - 1 else current_column
        if self.current_column_photon == current_column:
            self.timer_photon.stop()
        self.ui.plot1.draw()

    def update_plot_density(self):
        axes = self.ui.plot2.axes
        current_column = self.current_column_density
        plot_ref = self._plot_ref_density
        column_data = [row[current_column] for row in self.Density]
        title_data = self.hour_time[current_column]
        if plot_ref is None:
            plot_refs = axes.plot(column_data, self.H_standard, '-b')
            axes.set_title(title_data)
            self._plot_ref_density = plot_refs[0]
        else:
            plot_ref.set_xdata(column_data)
            axes.set_title(title_data)

        self.current_column_density = current_column + 1 if current_column < len(
            self.Density[0]) - 1 else current_column
        if self.current_column_density == current_column:
            self.timer_density.stop()
        self.ui.plot2.draw()

    def update_plot_temperature(self):
        axes = self.ui.plot3.axes
        current_column = self.current_column_temperature
        plot_ref = self._plot_ref_temperature
        column_data = [row[current_column] for row in self.Temperature]
        title_data = self.hour_time[current_column]
        if plot_ref is None:
            plot_refs = axes.plot(column_data, self.H_standard, '-b')
            axes.set_title(title_data)
            self._plot_ref_temperature = plot_refs[0]
        else:
            plot_ref.set_xdata(column_data)
            axes.set_title(title_data)

        self.current_column_temperature = current_column + 1 if current_column < len(
            self.Density[0]) - 1 else current_column
        if self.current_column_temperature == current_column:
            self.timer_temperature.stop()
        self.ui.plot3.draw()

    def pause_plotting_photon(self):
        if self.timer_photon.isActive():
            self.timer_photon.stop()
        else:
            self.timer_photon.start()

    def pause_plotting_density(self):
        if self.timer_density.isActive():
            self.timer_density.stop()
        else:
            self.timer_density.start()

    def pause_plotting_temperature(self):
        if self.timer_temperature.isActive():
            self.timer_temperature.stop()
        else:
            self.timer_temperature.start()

    def reset_plotting_photon(self):
        self.current_column_photon = 0
        self._plot_ref_photon = None
        while self.ui.plot1.axes.lines:
            self.ui.plot1.axes.lines[0].remove()
        self.update_plot_photon()
        self.timer_photon.start()

    def reset_plotting_density(self):
        self.current_column_density = 0
        self._plot_ref_density = None
        while self.ui.plot2.axes.lines:
            self.ui.plot2.axes.lines[0].remove()
        self.update_plot_density()
        self.timer_density.start()

    def reset_plotting_temperature(self):
        self.current_column_temperature = 0
        self._plot_ref_temperature = None
        while self.ui.plot3.axes.lines:
            self.ui.plot3.axes.lines[0].remove()
        self.update_plot_temperature()
        self.timer_temperature.start()

    def read_data_in_background(self):
        self.thread = DataLoaderThread(self.file_path, self.den_refer, self.temp_refer, self.coordinates, self.altitude)
        self.thread.progress_changed.connect(self.update_progress_bar)
        self.thread.finished.connect(self.on_task_completed)
        self.thread.start()

    def update_progress_bar(self, value):
        self.ui.progress_bar.setValue(value)

    def on_task_completed(self, result):
        (self.Photon, self.Height, self.date_time_obj, self.Temperature, self.Density, self.hour_time,
         self.H_standard, self.Absolute_error_temp, self.Absolute_error_density) = result
        self.ui.progress_bar.setVisible(True)
        read_message_box()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(basedir, 'favicon.ico')))
    window = MainWindow()
    sys.exit(app.exec())
