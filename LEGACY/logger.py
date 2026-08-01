# =============================================================================
# logger.py  —  Gerçek zamanlı hata kayıt sistemi (CSV + stabilite raporu)
# =============================================================================
import csv
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from config import LOG_DURATION_SEC, LOG_FILE


class ErrorLogger:
    """Sürüş sırasında yanal piksel hatalarını kaydeder, stabilite raporu üretir.

    Kullanım
    --------
    logger = ErrorLogger()
    while calisıyor:
        logger.update(error)   # kayıp şerit kareler için None geçin
    logger.finish()            # süre dolmadan önce de dışa aktarır
    """

    def __init__(
        self,
        duration_sec: float = LOG_DURATION_SEC,
        export_file: str    = LOG_FILE,
    ):
        self.duration    = duration_sec
        self.export_file = Path(export_file)
        self.start_time  = time.time()
        self.finished    = False

        self._errors:     list = []
        self._timestamps: list = []
        self._lost:       int  = 0

    # ------------------------------------------------------------------
    def update(self, error) -> None:
        """Bir karenin hata değerini kaydeder. Kayıp şerit için None geçin."""
        if self.finished:
            return
        now = time.time()
        if error is None:
            self._lost += 1
            error = 0.0
        self._errors.append(float(error))
        self._timestamps.append(now - self.start_time)
        if now - self.start_time >= self.duration:
            self.finish()

    # ------------------------------------------------------------------
    def finish(self) -> None:
        """Kayıt işlemini sonlandır, raporu yazdır, CSV'e aktar."""
        if self.finished:
            return
        self.finished = True
        self._report()
        self._export_csv()

    # ------------------------------------------------------------------
    def _report(self) -> None:
        if not self._errors:
            print("[Logger] Veri toplanamadı.")
            return
        arr      = np.array(self._errors)
        total    = len(arr)
        run_secs = self._timestamps[-1] if self._timestamps else 0
        fps_avg  = total / run_secs if run_secs > 0 else 0
        lost_pct = 100.0 * self._lost / total if total else 0.0

        print()
        print("======================================")
        print("       ŞERİT TAKİP STABİLİTE RAPORU  ")
        print("======================================")
        print(f"  Tarih/saat   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Süre         : {run_secs:.1f} s")
        print(f"  Kare sayısı  : {total}  ({fps_avg:.1f} fps ortalama)")
        print(f"  Kayıp şerit  : {self._lost} kare  ({lost_pct:.1f} %)")
        print(f"  Ortalama hata: {np.mean(arr):+.2f} px  (sapma)")
        print(f"  Std sapma    : {np.std(arr):.2f} px")
        print(f"  Maks |hata|  : {np.max(np.abs(arr)):.2f} px")
        print(f"  CSV kaydedil : {self.export_file}")
        print("======================================")
        print()

    # ------------------------------------------------------------------
    def _export_csv(self) -> None:
        with open(self.export_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["kare", "zaman_s", "hata_px"])
            for i, (t, e) in enumerate(zip(self._timestamps, self._errors)):
                writer.writerow([i, f"{t:.4f}", f"{e:.1f}"])