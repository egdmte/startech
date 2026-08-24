(function exposeSacConfiguration(global) {
  "use strict";

  const defaultPair = {
    kalibrasyon: {
      sema_surumu: 1,
      damga: {
        _aciklama: "Zaman sıralama için, özet benzersizlik için.",
        zaman: "2026-08-05T19:43:46",
        ozet: "e11b19",
        olusturan: "kalibrasyon-arac 0.1",
        not: ""
      },
      kamera: {
        _aciklama: "Kameranın fiziksel gerçekleri. Yanlışsa aşağıdaki her şey anlamsız.",
        genislik: 840,
        yukseklik: 630,
        bgr_cikis: true,
        dondur_180: true
      },
      perspektif: {
        _aciklama: "Yoldaki bir dikdörtgenin kamerada göründüğü dört köşe.",
        olculen_cozunurluk: [840, 630],
        olculen_cozunurluk_not: "kaynak_noktalar SADECE bu çözünürlükte geçerlidir. ayar.py uyuşmazlıkta başlatmayı reddeder.",
        kaynak_noktalar: [[199, 410], [633, 413], [0, 630], [840, 630]],
        nokta_sirasi: "sol-ust, sag-ust, sol-alt, sag-alt",
        roi_ust_oran: 0.55
      },
      serit: {
        _aciklama: "Beyaz şerit çizgisinin tanımı.",
        beyaz_profiller: {
          varsayilan: { alt: [19, 11, 90], ust: [180, 110, 255] },
          karanlik: { alt: [0, 0, 80], ust: [180, 100, 255] },
          normal: { alt: [0, 0, 90], ust: [180, 110, 255] },
          parlak: { alt: [0, 0, 160], ust: [180, 60, 255] }
        },
        profil_esikleri: {
          _aciklama: "Ortalama parlaklığa göre profil seçimi.",
          karanlik_alti: 100,
          parlak_ustu: 200
        },
        min_sinyal: 200,
        min_sinyal_kalite_orani: 1,
        varsayilan_serit_genisligi: 300,
        sureklilik_orani: 0.15,
        clahe_sinir: 2.5,
        clahe_kutucuk: 8
      },
      renkler: {
        _aciklama: "Her nesne için HSV aralıkları ve en küçük geçerli alan (px kare).",
        turuncu_arac: {
          _aciklama: "Sollanacak araç, 20x30x25 cm.",
          araliklar: [{ alt: [5, 120, 100], ust: [20, 255, 255] }],
          min_alan: 1500
        },
        sari_arac: {
          _aciklama: "Sollanmayacak tuzak araçlar. Turuncu H<=20, sarı H>=22 kalmalı.",
          araliklar: [{ alt: [22, 120, 100], ust: [35, 255, 255] }],
          min_alan: 1500
        },
        kirmizi_isik: {
          _aciklama: "Kırmızı renk tekerleğin iki ucundadır, bu yüzden iki aralık.",
          araliklar: [
            { alt: [0, 120, 80], ust: [10, 255, 255] },
            { alt: [160, 120, 80], ust: [180, 255, 255] }
          ],
          min_alan: 300
        },
        yesil_isik: {
          araliklar: [{ alt: [45, 90, 80], ust: [85, 255, 255] }],
          min_alan: 300
        },
        mavi_levha: {
          _aciklama: "Levhaların mavi zemini, 13x20 cm. Alan eşiği düşük.",
          araliklar: [{ alt: [95, 100, 70], ust: [130, 255, 255] }],
          min_alan: 200
        },
        kirmizi_park: {
          _aciklama: "Işıktan AYRI tutulur — farklı ışık altındadır ve zamanla ayrışır.",
          araliklar: [
            { alt: [0, 120, 90], ust: [10, 255, 255] },
            { alt: [160, 120, 80], ust: [180, 255, 255] }
          ],
          min_alan: 3000,
          tetik_alan: 6000
        }
      },
      motor: {
        _aciklama: "Bu araca özel mekanik ölçüler.",
        olculdu: null,
        olculdu_not: "null ise HENÜZ ÖLÇÜLMEDİ. LEGACY'de dört değer de 1.0 kaldı.",
        sol_trim_dusuk: 1,
        sol_trim_yuksek: 1,
        sag_trim_dusuk: 1,
        sag_trim_yuksek: 1,
        olu_bolge_min_pwm: 30,
        olu_bolge_yuzde: 20
      }
    },
    ayarlar: {
      sema_surumu: 1,
      _aciklama: "Bunlar ölçülmez, seçilir. Kalibrasyondan ayrı tutulur. BU DOSYA TEST ÖRNEĞİDİR; doğrudan araca yüklenmez.",
      kontrol: { kp: 0.58, kd: 0.6, ki: 0.2, integral_max: 50, deriv_cap: 150 },
      hiz: {
        hedef: 50,
        min: 25,
        max: 57,
        max_not: "3S pil ile 6 V motorlara ~10 V geliyor. %57 anma gerilimidir. Ölç.",
        k_speed: 0.45
      },
      olay: {
        yakin_roi_orani: 0.75,
        yakin_roi_orani_not: "Desenin ROI'nin bu oranından aşağıda görünmesi = ~30 cm."
      }
    }
  };

  const requiredModules = ["yaren", "arda", "kasim"];

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function defaultBaseline() {
    return clone(defaultPair);
  }

  function parseImportedConfiguration(text) {
    const parsed = JSON.parse(text);
    const errors = validateBaseline(parsed);
    if (errors.length) throw new Error(errors.join("; "));
    return {
      kalibrasyon: clone(parsed.kalibrasyon),
      ayarlar: clone(parsed.ayarlar)
    };
  }

  function validateBaseline(value) {
    const errors = [];
    if (!isObject(value) || value.sema_surumu !== 2) {
      errors.push("Select one merged configuration with sema_surumu 2.");
      return errors;
    }
    if (!isObject(value.kalibrasyon) || value.kalibrasyon.sema_surumu !== 1) {
      errors.push("The merged file does not contain calibration v1.");
    }
    if (!isObject(value.ayarlar) || value.ayarlar.sema_surumu !== 1) {
      errors.push("The merged file does not contain settings v1.");
    }
    return errors;
  }

  function validateSections(sections) {
    const errors = [];
    ["power", "compute", "camera", "drive", "wheel"].forEach((name) => {
      if (!isObject(sections[name])) errors.push(`Missing SAC section: ${name}.`);
    });
    if (errors.length) return errors;
    if (sections.power.minimumSpeedPercent > sections.power.maximumSpeedPercent) {
      errors.push("Minimum speed cannot exceed maximum speed.");
    }
    const enabled = new Set(sections.compute.enabledModules || []);
    const missing = requiredModules.filter((name) => !enabled.has(name));
    if (missing.length) errors.push(`Missing required modules: ${missing.join(", ")}.`);
    if (
      sections.drive.driverOutputMode === "full" &&
      !(sections.drive.fullOutputAcknowledged && sections.drive.prototypeLockAcknowledged)
    ) {
      errors.push("Full output requires both SAC acknowledgements.");
    }
    return errors;
  }

  function buildIntent(sections) {
    return {
      sozlesme_surumu: 1,
      kamera: {
        yon_derecesi: sections.camera.orientationDegrees,
        yakalama_profili: sections.camera.captureProfile,
        tanima_hassasiyeti: sections.camera.recognitionSensitivity,
        raspberry_pi_oncelikli: Boolean(sections.camera.prioritizeRaspberryPi)
      },
      guc: {
        minimum_hiz_yuzde: sections.power.minimumSpeedPercent,
        maksimum_hiz_yuzde: sections.power.maximumSpeedPercent
      },
      hesaplama: {
        baslangic_onlemi: sections.compute.startupPrecaution,
        servis_durumu: sections.compute.serviceStatus,
        m3th_sikiligi: sections.compute.m3thAggressiveness,
        etkin_moduller: [...sections.compute.enabledModules]
      },
      surus: {
        komut_kaybi_eylemi: sections.drive.lossOfCommandAction,
        surucu_cikis_modu: sections.drive.driverOutputMode,
        direksiyon_merkez_yuzde: sections.drive.steeringCentreOffsetPercent,
        direksiyon_azami_hareket_yuzde: sections.drive.maximumSteeringTravelPercent
      },
      tekerlek: {
        sol_duzeltme_yuzde: sections.wheel.leftCorrectionPercent,
        sag_duzeltme_yuzde: sections.wheel.rightCorrectionPercent,
        sol_yon: sections.wheel.leftDirection,
        sag_yon: sections.wheel.rightDirection
      }
    };
  }

  function buildEvidence(sections) {
    return {
      simulasyon: true,
      fiziksel_cikis_aktif: false,
      fiziksel_dogrulama_yapildi: false,
      tam_cikis_onaylandi: Boolean(sections.drive.fullOutputAcknowledged),
      prototip_kilidi_onaylandi: Boolean(sections.drive.prototypeLockAcknowledged),
      mekanik_inceleme: [...sections.wheel.mechanicalReview],
      fiziksel_hizalama_dogrulandi: Boolean(sections.wheel.physicalAlignmentVerified)
    };
  }

  function createIdentifier() {
    const bytes = new Uint8Array(3);
    global.crypto.getRandomValues(bytes);
    return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  function mapSource(source) {
    return {
      default: "DEFAULT",
      "old-version": "PREVIOUS",
      car: "CAR_SIMULATION"
    }[source] || "DEFAULT";
  }

  function buildConfiguration({ baseline, name, source, sections }) {
    const sectionErrors = validateSections(sections);
    if (sectionErrors.length) throw new Error(sectionErrors.join("; "));
    if (!isObject(baseline) || !isObject(baseline.kalibrasyon) || !isObject(baseline.ayarlar)) {
      throw new Error("A complete calibration/settings baseline is required.");
    }

    const settings = clone(baseline.ayarlar);
    const minimum = sections.power.minimumSpeedPercent;
    const maximum = sections.power.maximumSpeedPercent;
    settings.hiz.min = minimum;
    settings.hiz.max = maximum;
    settings.hiz.hedef = Math.min(Math.max(settings.hiz.hedef, minimum), maximum);

    const identifier = createIdentifier();
    const configuration = {
      sema_surumu: 2,
      profil: {
        ad: name,
        is_akisi: "SAC",
        kaynak: mapSource(source),
        olusturuldu_utc: new Date().toISOString(),
        kimlik: identifier
      },
      kalibrasyon: clone(baseline.kalibrasyon),
      ayarlar: settings,
      sac_niyeti: buildIntent(sections),
      oturum_kaniti: buildEvidence(sections)
    };
    return { configuration, identifier };
  }

  global.StartechSacV2 = Object.freeze({
    buildConfiguration,
    defaultBaseline,
    parseImportedConfiguration,
    validateBaseline,
    validateSections
  });
})(window);
