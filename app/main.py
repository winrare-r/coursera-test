import json
import logging
import sys
from pathlib import Path

from PyQt5.QtCore import QObject, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.analysis.processor import Analyzer, AnalysisResult

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"
HISTORY_FILE = BASE_DIR / "resources" / "history.json"
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)


class AnalysisWorker(QObject):
    finished = pyqtSignal(object)
    progress = pyqtSignal(int)
    stage = pyqtSignal(str)

    def __init__(self, file_path: str, preset: str):
        super().__init__()
        self.file_path = file_path
        self.preset = preset
        self.analyzer = Analyzer(LOG_FILE)

    def run(self) -> None:
        result = self.analyzer.run(
            self.file_path,
            self.preset,
            progress_cb=self.progress.emit,
            stage_cb=self.stage.emit,
        )
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SETI Analyzer")
        self.resize(1200, 800)

        self.history = self._load_history()
        self.analysis_results: AnalysisResult | None = None

        self.central_tabs = QTabWidget()
        self.setCentralWidget(self.central_tabs)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self._build_home_tab()
        self._build_progress_tab()
        self._build_results_tab()
        self._build_settings_tab()

    # region UI builders
    def _build_home_tab(self) -> None:
        container = QWidget()
        layout = QVBoxLayout()

        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        browse_btn = QPushButton("Выбрать файл")
        browse_btn.clicked.connect(self._select_file)
        file_layout.addWidget(QLabel("Файл для анализа:"))
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        preset_layout = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "DBSCAN (быстрый)",
            "DBSCAN (точный)",
            "Локальный поиск",
            "Спектральный анализ",
        ])
        preset_layout.addWidget(QLabel("Пресет анализа:"))
        preset_layout.addWidget(self.preset_combo)
        layout.addLayout(preset_layout)

        self.history_list = QListWidget()
        self.history_list.addItems(self.history)
        layout.addWidget(QLabel("Недавние файлы:"))
        layout.addWidget(self.history_list)

        actions = QHBoxLayout()
        self.analyze_btn = QPushButton("Запустить анализ")
        self.analyze_btn.clicked.connect(self._start_analysis)
        actions.addWidget(self.analyze_btn)
        layout.addLayout(actions)

        self.home_status = QLabel("Готово к запуску")
        layout.addWidget(self.home_status)

        container.setLayout(layout)
        self.central_tabs.addTab(container, "Главный экран")

    def _build_progress_tab(self) -> None:
        container = QWidget()
        layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(QLabel("Прогресс выполнения"))
        layout.addWidget(self.progress_bar)

        self.stage_label = QLabel("Ожидание запуска...")
        layout.addWidget(self.stage_label)

        self.stage_history = QTextEdit()
        self.stage_history.setReadOnly(True)
        layout.addWidget(self.stage_history)

        log_btn = QPushButton("Открыть лог-файл")
        log_btn.clicked.connect(self._open_log_file)
        layout.addWidget(log_btn)

        container.setLayout(layout)
        self.central_tabs.addTab(container, "Прогресс")

    def _build_results_tab(self) -> None:
        container = QWidget()
        main_layout = QVBoxLayout()
        self.results_tabs = QTabWidget()

        self._build_overview_tab()
        self._build_windows_tab()
        self._build_candidates_tab()

        main_layout.addWidget(self.results_tabs)
        container.setLayout(main_layout)
        self.central_tabs.addTab(container, "Результаты")

    def _build_overview_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout()

        meta_group = QGroupBox("Метаданные")
        self.meta_view = QTextEdit()
        self.meta_view.setReadOnly(True)
        meta_layout = QVBoxLayout()
        meta_layout.addWidget(self.meta_view)
        meta_group.setLayout(meta_layout)

        waterfall_group = QGroupBox("Общий водопад")
        self.waterfall_view = QLabel("Превью будет показано после анализа")
        self.waterfall_view.setMinimumHeight(220)
        self.waterfall_view.setScaledContents(True)
        waterfall_layout = QVBoxLayout()
        waterfall_layout.addWidget(self.waterfall_view)
        waterfall_group.setLayout(waterfall_layout)

        activity_group = QGroupBox("Карта активности")
        self.activity_view = QLabel("Карта появится после обработки")
        self.activity_view.setMinimumHeight(220)
        self.activity_view.setScaledContents(True)
        activity_layout = QVBoxLayout()
        activity_layout.addWidget(self.activity_view)
        activity_group.setLayout(activity_layout)

        layout.addWidget(meta_group)
        layout.addWidget(waterfall_group)
        layout.addWidget(activity_group)
        tab.setLayout(layout)
        self.results_tabs.addTab(tab, "Обзор файла")

    def _build_windows_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout()

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Фильтр/поиск:"))
        self.window_filter = QLineEdit()
        controls.addWidget(self.window_filter)
        layout.addLayout(controls)

        self.windows_table = QTableWidget(0, 3)
        self.windows_table.setHorizontalHeaderLabels(["Окно", "Рейтинг", "Кластер"])
        layout.addWidget(self.windows_table)

        self.window_preview = QLabel("Превью водопада с кластерами")
        self.window_preview.setMinimumHeight(240)
        self.window_preview.setScaledContents(True)
        layout.addWidget(self.window_preview)

        tab.setLayout(layout)
        self.results_tabs.addTab(tab, "Окна/Рейтинги")

    def _build_candidates_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout()

        filters = QHBoxLayout()
        self.candidate_filter = QLineEdit()
        filters.addWidget(QLabel("Поиск:"))
        filters.addWidget(self.candidate_filter)
        self.rfi_checkbox = QCheckBox("Только RFI")
        self.interesting_checkbox = QCheckBox("Только интересное")
        filters.addWidget(self.rfi_checkbox)
        filters.addWidget(self.interesting_checkbox)
        layout.addLayout(filters)

        self.candidates_table = QTableWidget(0, 3)
        self.candidates_table.setHorizontalHeaderLabels(["ID", "Частота", "Статус"])
        layout.addWidget(self.candidates_table)

        self.candidate_preview = QLabel("Предпросмотр спектра/водопада")
        self.candidate_preview.setMinimumHeight(240)
        self.candidate_preview.setScaledContents(True)
        layout.addWidget(self.candidate_preview)

        tab.setLayout(layout)
        self.results_tabs.addTab(tab, "Кандидаты")

    def _build_settings_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout()

        dbscan_group = QGroupBox("Пресеты DBSCAN")
        dbscan_layout = QFormLayout()
        self.eps_spin = QDoubleSpinBox()
        self.eps_spin.setRange(0.01, 5.0)
        self.eps_spin.setSingleStep(0.05)
        self.eps_spin.setValue(0.35)
        self.min_samples_spin = QSpinBox()
        self.min_samples_spin.setRange(1, 100)
        self.min_samples_spin.setValue(8)
        dbscan_layout.addRow("EPS", self.eps_spin)
        dbscan_layout.addRow("Min samples", self.min_samples_spin)
        dbscan_group.setLayout(dbscan_layout)

        preprocessing_group = QGroupBox("Предобработка")
        preprocessing_layout = QVBoxLayout()
        self.denoise_checkbox = QCheckBox("Шумоподавление")
        self.normalize_checkbox = QCheckBox("Нормализация по полосам")
        preprocessing_layout.addWidget(self.denoise_checkbox)
        preprocessing_layout.addWidget(self.normalize_checkbox)
        preprocessing_group.setLayout(preprocessing_layout)

        paths_group = QGroupBox("Пути сохранения")
        paths_layout = QFormLayout()
        self.results_path = QLineEdit(str(BASE_DIR / "results"))
        self.logs_path = QLineEdit(str(LOG_DIR))
        paths_layout.addRow("Результаты", self.results_path)
        paths_layout.addRow("Логи", self.logs_path)
        paths_group.setLayout(paths_layout)

        theme_group = QGroupBox("Тема интерфейса")
        theme_layout = QVBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Светлая", "Тёмная", "Системная"])
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)

        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self._save_settings)

        layout.addWidget(dbscan_group)
        layout.addWidget(preprocessing_group)
        layout.addWidget(paths_group)
        layout.addWidget(theme_group)
        layout.addWidget(save_btn)

        tab.setLayout(layout)
        self.central_tabs.addTab(tab, "Настройки")
    # endregion

    # region Actions
    def _select_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "")
        if path:
            self.file_input.setText(path)
            self._add_to_history(path)

    def _start_analysis(self) -> None:
        file_path = self.file_input.text().strip()
        if not file_path:
            QMessageBox.warning(self, "Файл не выбран", "Укажите путь к файлу для анализа")
            return
        preset = self.preset_combo.currentText()
        self.home_status.setText(f"Запуск анализа: {preset}")
        self.stage_history.clear()
        self.progress_bar.setValue(0)
        self.stage_label.setText("Запуск...")
        self.central_tabs.setCurrentIndex(1)

        self.thread = QThread()
        self.worker = AnalysisWorker(file_path, preset)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._analysis_finished)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.stage.connect(self._update_stage)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
        self.analyze_btn.setEnabled(False)

    def _update_stage(self, stage: str) -> None:
        self.stage_label.setText(stage)
        self.stage_history.append(stage)
        self.status_bar.showMessage(stage)

    def _analysis_finished(self, result: AnalysisResult) -> None:
        self.analysis_results = result
        self.analyze_btn.setEnabled(True)
        self.home_status.setText("Анализ завершен")
        self._populate_results()
        self.central_tabs.setCurrentIndex(2)

    def _open_log_file(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_FILE)))

    def _save_settings(self) -> None:
        settings = {
            "dbscan_eps": self.eps_spin.value(),
            "dbscan_min_samples": self.min_samples_spin.value(),
            "denoise": self.denoise_checkbox.isChecked(),
            "normalize": self.normalize_checkbox.isChecked(),
            "results_path": self.results_path.text(),
            "logs_path": self.logs_path.text(),
            "theme": self.theme_combo.currentText(),
        }
        settings_file = BASE_DIR / "resources" / "settings.json"
        settings_file.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status_bar.showMessage("Настройки сохранены", 3000)

    def _populate_results(self) -> None:
        if not self.analysis_results:
            return

        meta_text = "\n".join(f"{k}: {v}" for k, v in self.analysis_results.metadata.items())
        self.meta_view.setPlainText(meta_text)
        self._set_image(self.waterfall_view, self.analysis_results.waterfall_image, "Нет превью водопада")
        self._set_image(self.activity_view, self.analysis_results.activity_image, "Нет карты активности")
        self._set_image(self.window_preview, self.analysis_results.window_preview_image, "Нет превью окон")
        self._set_image(
            self.candidate_preview,
            self.analysis_results.candidate_preview_image,
            "Нет предпросмотра кандидатов",
        )

        self.windows_table.setRowCount(len(self.analysis_results.window_scores))
        for row, item in enumerate(self.analysis_results.window_scores):
            self.windows_table.setItem(row, 0, QTableWidgetItem(item.get("Окно", "")))
            self.windows_table.setItem(row, 1, QTableWidgetItem(item.get("Рейтинг", "")))
            self.windows_table.setItem(row, 2, QTableWidgetItem(item.get("Кластер", "")))

        self.candidates_table.setRowCount(len(self.analysis_results.candidates))
        for row, item in enumerate(self.analysis_results.candidates):
            self.candidates_table.setItem(row, 0, QTableWidgetItem(item.get("ID", "")))
            self.candidates_table.setItem(row, 1, QTableWidgetItem(item.get("Частота", "")))
            self.candidates_table.setItem(row, 2, QTableWidgetItem(item.get("Статус", "")))
    # endregion

    def _set_image(self, label: QLabel, path: str, fallback: str) -> None:
        """Update QLabel with an image if available."""
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            label.setPixmap(pixmap)
            label.setText("")
        else:
            label.setPixmap(QPixmap())
            label.setText(fallback)

    # region History helpers
    def _load_history(self) -> list[str]:
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return []
        return []

    def _add_to_history(self, path: str) -> None:
        if path in self.history:
            self.history.remove(path)
        self.history.insert(0, path)
        self.history = self.history[:10]
        self.history_list.clear()
        self.history_list.addItems(self.history)
        HISTORY_FILE.write_text(json.dumps(self.history, ensure_ascii=False, indent=2), encoding="utf-8")
    # endregion


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
