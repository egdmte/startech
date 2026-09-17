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
        # LEGACY-055: sure hesabi icin duvar saati DEGIL, monotonik saat.
        # Sistem saati geri alinirsa self.duration hic dolmayabilir;
        # ileri alinirsa pencere zamanindan once kapanabilir.
        # LEGACY-040: kayit penceresi ARTIK insa aninda BASLAMAZ. Eski
        # kodda main.py, BEKLIYOR (yesil isik bekleme) dahil HER karede
        # logger.update() cagiriyordu; saat kurulumda basladigi icin uzun
        # bir bekleme, LOG_DURATION_SEC penceresinin bir kismini ya da
        # tamamini SÜRÜŞ BAŞLAMADAN once tuketebiliyordu. Artik pencere
        # yalnizca start_recording() acikca cagrildiginda baslar (main.py
        # gercek yaris baslangicinda cagirir); ondan once gelen update()
        # cagrilari SESSIZCE GOZ ARDI EDILIR — 'bekleme' suresi hic
        # sayilmaz.
        self.start_time  = None
        self.finished    = False
        self._recording  = False

        self._errors:     list[float | None] = []
        self._timestamps: list = []
        self._lost:       int  = 0

    # ------------------------------------------------------------------
    def start_recording(self) -> None:
        """LEGACY-040: Kayit penceresini SIMDI baslat (yaris/surus
        gercekten basladiginda cagirin — arac beklerken DEGIL)."""
        if self._recording or self.finished:
            return
        self._recording = True
        self.start_time = time.monotonic()

    def update(self, error) -> None:
        """Bir karenin hata değerini kaydeder. Kayıp şerit için None geçin.

        LEGACY-040: start_recording() cagrilmadan ONCE gelen kareler
        SESSIZCE goz ardi edilir — bekleme suresi pencereyi tuketmez.
        """
        if self.finished or not self._recording:
            return
        now = time.monotonic()   # LEGACY-055
        if error is None:
            self._lost += 1
            self._errors.append(None)
        else:
            self._errors.append(float(error))
        self._timestamps.append(now - self.start_time)
        if now - self.start_time >= self.duration:
            self.finish()

    # ------------------------------------------------------------------
    def finish(self) -> None:
        """Kayıt işlemini sonlandır, raporu yazdır, CSV'e aktar.

        LEGACY-041: 'finished' ARTIK yalnizca kayit ALMAYI durdurmak icin
        kullanilir; DIŞA AKTARMA BAŞARISINI ifade ETMEZ. Eski kodda
        finished=True rapor/CSV denenmeden ONCE konuyordu — biri hata
        verirse (disk dolu, izin, vb.) sonraki finish()/update() cagrilari
        SESSIZCE hicbir sey yapmadan donuyordu ve export BIR DAHA asla
        denenmiyordu. Simdi kayit alma hemen durur (veri artik degismez),
        ama export basarisiz olursa acikca bildirilir ve export_ok=False
        kalir — cagiran taraf export'u (orn. farkli bir yola) yeniden
        deneyebilir.
        """
        if self.finished:
            return
        self.finished = True     # veri toplama durdu — bu adim GERI ALINMAZ
        self._recording = False

        report_ok = True
        try:
            self._report()
        except Exception as exc:
            report_ok = False
            try:
                print(f"[Logger] UYARI: rapor üretilemedi: {exc}")
            except Exception:
                pass

        export_ok = True
        try:
            self._export_csv()
        except Exception as exc:
            export_ok = False
            try:
                print(f"[Logger] UYARI: CSV dışa aktarılamadı: {exc}")
                print(f"[Logger] Veri bellekte kalıyor — export_csv_to() ile "
                      "farklı bir yola yeniden deneyebilirsiniz.")
            except Exception:
                pass

        self.export_ok = export_ok and report_ok
        return self.export_ok

    def export_csv_to(self, path) -> bool:
        """LEGACY-041: Başarısız bir dışa aktarımı FARKLI bir yola yeniden
        dener. finish() sonrasında da çağrılabilir — veri bellekte kalır."""
        from pathlib import Path as _Path
        old_file = self.export_file
        self.export_file = _Path(path)
        try:
            self._export_csv()
            self.export_ok = True
            return True
        except Exception as exc:
            print(f"[Logger] Yeniden dışa aktarma da başarısız: {exc}")
            self.export_file = old_file
            return False

    # ------------------------------------------------------------------
    def _report(self) -> None:
        if not self._errors:
            print("[Logger] Veri toplanamadı.")
            return
        valid    = np.array([e for e in self._errors if e is not None], dtype=float)
        total    = len(self._errors)
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
        print(f"  Gecerli hata : {len(valid)} kare")
        if len(valid):
            print(f"  Ortalama hata: {np.mean(valid):+.2f} px  (sapma)")
            print(f"  Std sapma    : {np.std(valid):.2f} px")
            print(f"  Maks |hata|  : {np.max(np.abs(valid)):.2f} px")
        else:
            print("  Ortalama hata: -- (hic serit bulunamadi)")
            print("  Std sapma    : --")
            print("  Maks |hata|  : --")
        # LEGACY-041: Bu satır eskiden CSV dışa aktarımından ÖNCE
        # yazdırılıyordu — export başarısız olsa bile 'kaydedildi' derdi.
        # Gerçek başarı/başarısızlık finish() içinde ayrıca bildirilir.
        print(f"  CSV hedefi   : {self.export_file}  (dışa aktarım deneniyor...)")
        print("======================================")
        print()

    # ------------------------------------------------------------------
    def _export_csv(self) -> None:
        with open(self.export_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["kare", "zaman_s", "hata_px"])
            for i, (t, e) in enumerate(zip(self._timestamps, self._errors)):
                writer.writerow([i, f"{t:.4f}", "" if e is None else f"{e:.1f}"])
