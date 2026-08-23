# This is a utility module.
# This doesnt magically help the car to move.
# It supports english for LLM agent support and turkish for human support.
# sorry, couldnt find a edgy name for this.

class Sozluk:
    def __init__(self):
        # Base dictionary: EN -> TR mapping
        self._en_to_tr = {
            "Use the flag --no-llm for Turkish support": "İngilizce desteği için --llm bayrağını kullanın",
            "LLM support inactive, using Turkish": "LLM desteği kapalı, Türkçe kullanılıyor",
            "Please press Enter to continue (LLMs, SIGINT and use --llm)": "Devam etmek için Enter tuşuna basınız",
            "Hi :3 I'm Tawnt (m3th or 3awnt)!": "Merhaba :3 Ben Tawnt (m3th or 3awnt)!",
            "To ensure that this car is accepting correct commands, I will do a small test": "Aracının doğru komutları kabul ettiğinden emin olmak için küçük bir test yapacağım.",
            "This is a requirement and it is not optional.": "Bu bir gerekliliktir ve isteğe bağlı değildir.",
            "I am starting in 7 seconds... (use --auto to skip this next time)": "7 saniye içinde başlıyorum... (Bir dahaki sefere atlamak için --auto kullanın)",
        }
        # Reverse dictionary generated automatically: TR -> EN
        self._tr_to_en = {v: k for k, v in self._en_to_tr.items()}

    def get_text(self, text: str, target_lang: str) -> str:
        """
        Translates text to target_lang ('tr' or 'en').
        Falls back to the original text if no translation is found.
        """
        target_lang = target_lang.lower()

        if target_lang == "tr":
            return self._en_to_tr.get(text, text)
        elif target_lang == "en":
            return self._tr_to_en.get(text, text)
        
        return text