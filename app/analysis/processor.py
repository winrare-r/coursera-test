import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


@dataclass
class AnalysisResult:
    metadata: Dict[str, str] = field(default_factory=dict)
    waterfall_image: str = ""
    activity_image: str = ""
    window_preview_image: str = ""
    candidate_preview_image: str = ""
    window_scores: List[Dict[str, str]] = field(default_factory=list)
    candidates: List[Dict[str, str]] = field(default_factory=list)
    error_message: str = ""


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
        try:
            stages = [
                "Загрузка файла",
                "Предобработка",
                "Формирование водопада",
                "Кластеризация окон",
                "Поиск кандидатов",
                "Запись результатов",
            ]
            total = len(stages)
            preview_dir = Path(self.log_path).parent / "previews"
            preview_dir.mkdir(parents=True, exist_ok=True)
            results = AnalysisResult(
                metadata={
                    "Имя": Path(file_path).name,
                    "Размер": "42 MB (демо)",
                    "Пресет": preset,
                },
                waterfall_image=self._safe_heatmap(preview_dir / "waterfall.png", "Общий водопад"),
                activity_image=self._safe_activity_map(preview_dir / "activity.png"),
                window_preview_image=self._safe_cluster_preview(preview_dir / "windows.png"),
                candidate_preview_image=self._safe_candidate_preview(preview_dir / "candidates.png"),
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
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.exception("Ошибка анализа %s", file_path)
            return AnalysisResult(error_message=str(exc))

    def _generate_heatmap(self, path: Path, title: str) -> Path:
        """Create a fake waterfall image."""
        data = np.random.rand(100, 200)
        plt.figure(figsize=(6, 3))
        plt.imshow(data, aspect="auto", origin="lower", cmap="viridis")
        plt.colorbar(label="Мощность")
        plt.title(title)
        plt.xlabel("Время")
        plt.ylabel("Частота")
        plt.tight_layout()
        plt.savefig(path, dpi=120)
        plt.close()
        return path

    def _generate_activity_map(self, path: Path) -> Path:
        """Create a mock activity map showing hot areas."""
        x, y = np.meshgrid(np.linspace(0, 10, 80), np.linspace(0, 10, 80))
        z = np.sin(x) * np.cos(y) + np.random.normal(scale=0.2, size=x.shape)
        plt.figure(figsize=(6, 3))
        plt.contourf(x, y, z, levels=20, cmap="inferno")
        plt.colorbar(label="Активность")
        plt.title("Карта активности")
        plt.xlabel("Смещение по времени")
        plt.ylabel("Смещение по частоте")
        plt.tight_layout()
        plt.savefig(path, dpi=120)
        plt.close()
        return path

    def _generate_cluster_preview(self, path: Path) -> Path:
        """Create a scatter preview for window clusters."""
        rng = np.random.default_rng(42)
        means = np.array([[0.0, 0.0], [3.0, 3.0], [-3.0, 2.0]])
        clusters = []
        for mean in means:
            cluster_points = rng.normal(loc=mean, scale=0.6, size=(60, 2))
            clusters.append(cluster_points)
        colors = ["tab:blue", "tab:orange", "tab:green"]
        plt.figure(figsize=(5, 4))
        for points, color, label in zip(clusters, colors, ["A", "B", "C"]):
            plt.scatter(points[:, 0], points[:, 1], s=25, alpha=0.7, color=color, label=f"Кластер {label}")
        plt.legend()
        plt.xlabel("PC1")
        plt.ylabel("PC2")
        plt.title("Кластеры окон")
        plt.tight_layout()
        plt.savefig(path, dpi=120)
        plt.close()
        return path

    def _generate_candidate_preview(self, path: Path) -> Path:
        """Create a spectrum-like plot for candidate preview."""
        freq = np.linspace(1420, 1425, 500)
        power = -90 + 5 * np.sin(2 * np.pi * freq / 1.2) + np.random.normal(scale=1.5, size=freq.size)
        peaks = [1421.3, 1422.8, 1424.1]
        for peak in peaks:
            power += 12 * np.exp(-((freq - peak) ** 2) / 0.0015)

        plt.figure(figsize=(6, 3))
        plt.plot(freq, power, color="tab:blue")
        for peak in peaks:
            plt.axvline(peak, color="tab:red", linestyle="--", alpha=0.7)
        plt.xlabel("Частота, MHz")
        plt.ylabel("Мощность, дБ")
        plt.title("Предпросмотр кандидатов")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(path, dpi=120)
        plt.close()
        return path

    @staticmethod
    def _simulate_work(progress_cb: Callable[[int], None], current: int, total: int) -> None:
        start_percent = int((current - 1) / total * 100)
        end_percent = int(current / total * 100)
        steps = 5
        for i in range(steps):
            time.sleep(0.2)
            increment = start_percent + int(((i + 1) / steps) * (end_percent - start_percent))
            progress_cb(increment)

    # region safe wrappers
    def _safe_heatmap(self, path: Path, title: str) -> str:
        try:
            return str(self._generate_heatmap(path, title))
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Не удалось построить водопад")
            return ""

    def _safe_activity_map(self, path: Path) -> str:
        try:
            return str(self._generate_activity_map(path))
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Не удалось построить карту активности")
            return ""

    def _safe_cluster_preview(self, path: Path) -> str:
        try:
            return str(self._generate_cluster_preview(path))
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Не удалось построить превью кластеров")
            return ""

    def _safe_candidate_preview(self, path: Path) -> str:
        try:
            return str(self._generate_candidate_preview(path))
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Не удалось построить превью кандидатов")
            return ""
    # endregion
