import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List


@dataclass
class AnalysisResult:
    metadata: Dict[str, str] = field(default_factory=dict)
    waterfall_preview: str = ""
    activity_map: str = ""
    window_scores: List[Dict[str, str]] = field(default_factory=list)
    candidates: List[Dict[str, str]] = field(default_factory=list)


class Analyzer:
    """Stub analyzer that simulates long-running work and produces structured data."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.logger = logging.getLogger("analyzer")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_path, encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def run(
        self,
        file_path: str,
        preset: str,
        progress_cb: Callable[[int], None],
        stage_cb: Callable[[str], None],
    ) -> AnalysisResult:
        stages = [
            "Загрузка файла",
            "Предобработка",
            "Формирование водопада",
            "Кластеризация окон",
            "Поиск кандидатов",
            "Запись результатов",
        ]
        total = len(stages)
        results = AnalysisResult(
            metadata={
                "Имя": Path(file_path).name,
                "Размер": "42 MB (демо)",
                "Пресет": preset,
            },
            waterfall_preview="Симуляция общего водопада",
            activity_map="Симуляция карты активности",
            window_scores=[
                {"Окно": f"{i:03d}", "Рейтинг": f"{90 - i}%", "Кластер": "A"}
                for i in range(5)
            ],
            candidates=[
                {
                    "ID": f"C-{i:02d}",
                    "Частота": f"{1420 + i * 0.5} MHz",
                    "Статус": "RFI" if i % 2 == 0 else "Интересно",
                }
                for i in range(8)
            ],
        )

        for index, stage in enumerate(stages, start=1):
            self.logger.info("%s: %s", stage, file_path)
            stage_cb(stage)
            self._simulate_work(progress_cb, index, total)

        progress_cb(100)
        stage_cb("Готово")
        self.logger.info("Анализ завершен для %s", file_path)
        return results

    @staticmethod
    def _simulate_work(progress_cb: Callable[[int], None], current: int, total: int) -> None:
        start_percent = int((current - 1) / total * 100)
        end_percent = int(current / total * 100)
        steps = 5
        for i in range(steps):
            time.sleep(0.2)
            increment = start_percent + int(((i + 1) / steps) * (end_percent - start_percent))
            progress_cb(increment)
