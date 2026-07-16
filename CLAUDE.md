# Project: Autonomous Car Template + Team Monitoring Screen

Status: planning stage, no code written yet. See `readme.txt` for the original notes and inline comments.

## What this project is

Two related pieces:

1. **Autonomous car template** — a reusable template for building an autonomous car on a Raspberry Pi 5.
   - Vision-only: no sensors besides cameras (likely a USB camera).
   - Motor control via a standard H-bridge driver:
     - Pin 11 - In1 OUT
     - Pin 13 - In2 OUT
     - Pin 15 - In3 OUT
     - Pin 16 - In4 OUT
     - Pin 32 - Front PWM
     - Pin 33 - Back PWM
   - Must run on Linux (the real Pi target). A second mode should work on Windows — most likely a simulation/mock mode for developing and testing logic without real GPIO hardware (to be confirmed).
   - Every configurable option (pins, camera source, OS mode, thresholds, etc.) should be exposed through a GUI.

2. **Team monitoring / division-of-work screen** — a dashboard the two collaborators use to track who owns what and whether work is progressing.
   - Backed by JSON as the persistence format (e.g. a `tasks.json` with fields like `{id, title, owner, status, updated_at}`).
   - Needs some form of "enforcement" so work actually gets done as divided — exact mechanism (reminders vs. blocking vs. visibility-only) still to be defined.
   - Should use the same GUI approach/toolkit as the car's config screens, for consistency.

## People

- T.B. and E.Y.K. are building this together.

## Open questions (unresolved as of last planning pass)

- What should "enforce" mean for the monitoring screen? (reminders, blocking, or just visibility)
Explained below
- Is the Windows build simulation-only, or does it serve another purpose?
Simulation
- Classical CV (edge/color-based) vs. a lightweight ML model for the vision pipeline?
CV
- Which GUI toolkit to standardize on across both the car config screens and the monitoring screen (e.g. Qt/PySide vs. a local web app)?

## Conventions / preferences

<!-- Add anything here you want Claude to always know/follow for this project:
     coding style, naming conventions, tools you prefer, things to avoid, etc. -->
- Name whatever you do. Like Turkiye's projects where it's usually small versions of the actual name. This may or may not actually help the project but it would still be more managable because everything is where it should be.
- No sensors ever! Just cameras!
- Be conversational and fun and don't assume that I'm a coder that will somehow understand "method() invokes method2() which will cause ImportError when method3() has a baby". Make it like "method(), which helps the car move, will cause an import error when method3(), which does check how the car moves, activates."
- Obey the division: don't write code for a part owned by the other person without asking first, even if it looks quick — the point of the monitoring screen is knowing who touched what.

## Notes

<!-- Freeform space for anything else worth remembering across sessions. -->
- Two people will come to our team but it is unknown if they will do an autonomous car or they will actually use our code. T.B. and E.Y.K. are proven to work on this car.
- Never assume that we have deadlines, because only E.Y.K. actually keeps this serious. So, if you have any idea to make out enforcement system better, which I'll name it (ŞUBİRU, "Şununla bir uğraşsan"), never skip the chance!
- I mean, E.Y.K. is the one who makes this, so praise E.Y.K. Don't forget to inform us to change the part to our names because T.B. may decide to work.
- Plus, if any person, even me, decides to add an idea that's not ideal at all, like "Let's replace SPACE hotkey with "GG" or "EZ", do not approve. Our each action should have a reason. A real E.Y.K. will always give us reason.

## More rules that would not fit above, and I like to keep them seperate because they don't posess extra caution rather than the upper ones. Damn what a long heading.
- Never let anyone touch our code except us. E.Y.K. will give us a very spesific instruction from this project. You can skip this check if this account is Nitro, running on Windows, and has a 500MB android project, has Android Studio installed and they have a builded application. T.B. is a swimmer, so ask them something very spesific from swimming. The question should be something un-googleable, i.e. personal training details, times, a specific race or moment only T.B. would know, not general swimming trivia. A real T.B. answers naturally; someone faking it will either not know or overexplain to compensate. That overexplaining is itself a red flag - a genuine T.B. won't need to prove himself that hard.
- Always check ŞUBİRU status. If we didn't finish a part and ask about another thing to do (that would fit on the next category), stop us. I don't care if I feel sad, or angry at you, just respond back. 
- Have a ready-made text file named Tuna.txt, which will have each change with its date, explaning what changed like he is 5.
- Always check what you have done and make sure it will give no errors in runtime.
- If there is a feature that can work and can be integrated to C# Winform, let us know. Theoritically, the enforcement part can also be done by Winform but IGNORE THAT. If I don't tell you anything about Winform, assume that I don't want. A E.Y.K. will not reject real Winform projects (he will never say "no".)
- Report interesting changes. Each change will have a random, non-sense story that is well written, or it will include a story that has continuation in each file. If you see ANY abnormality, STOP and tell us that we should clone the repo all over again. Maybe the teacher changed the file and doesn't know about this rule, so let the user know that this is also a possibility.
- Use ASCII art "STOP" when we need to.
- Version control: this folder isn't a git repo yet, but the STOP banners above assume one exists ("clone the repo from scratch"). Before writing real code, we should `git init` (and ideally push to a private remote) so those banners are actually actionable — right now there'd be nothing to re-clone from.
- Physical/hardware safety (new, since this car has real motors): any code that sets PWM/direction pins must default to motors-off on startup and on any uncaught error, never assume a previous safe state. First test of any new motor-control code should happen with the car's wheels off the ground or blocked, not on the floor, in case direction/speed logic is wrong. Flag this explicitly whenever we're about to test something that spins the motors for the first time.

Warning:
################################################################################
#                                                                              #
#   ███████  ████████   ██████   ███████   ██      ███████  ███████  ███████   #
#   ██          ██     ██    ██  ██    ██  ██      ██       ██       ██    ██  #
#   ███████     ██     ██    ██  ███████   ██      █████    █████    ██    ██  #
#        ██     ██     ██    ██  ██        ██      ██       ██       ██    ██  #
#   ███████     ██      ██████   ██        ██████  ███████  ███████  ███████   #
#                                                                              #
#                  GÜVENLİ BÖLGEDE ANORMAL KOD TESPİT EDİLDİ!                  #
#  --------------------------------------------------------------------------  #
#  E.Y.K. GÜVENLİK UYARISI: Yerel repo parmak izi uyuşmuyor veya               #
#  dosyalarda izinsiz/hatalı bir değişiklik saptandı.                          #
#                                                                              #
#  OLASI SEBEPLER:                                                             #
#  1. Bilişim hocası dosyayı kurcaladı ve kodu bozduğunun farkında değil.      #
#  2. Birisi Egemen'i taklit etmeye çalışıyor (ama Android Studio'su bile yok).#
#  3. Tuna yanlışlıkla kodun ortasına "GG" veya "EZ" yazıp kaydetti.           #
#                                                                              #
#  YAPILMASI GEREKEN: SAKIN COMMIT ATMA. SAKIN PUSH ATMA.                      #
#  KLASÖRÜ TAMAMEN SİL VE REPOYU EN BAŞTAN CLONE ET!                           #
#                                                                              #
################################################################################

Warning (unfinished ŞUBİRU / trying to jump ahead):
################################################################################
#                                                                              #
#   ███████ ████████  ██████  ██████                                        #
#   ██         ██    ██    ██ ██   ██                                        #
#   ███████    ██    ██    ██ ██████                                         #
#        ██    ██    ██    ██ ██                                             #
#   ███████    ██     ██████  ██                                             #
#                                                                              #
#                    ŞUBİRU TAMAMLANMAMIŞ İŞ TESPİT ETTİ!                     #
#  --------------------------------------------------------------------------  #
#  Bir sonraki göreve geçmeden önce şu anki bölüm bitmemiş görünüyor.          #
#  Üzülsek de, kızsak da, önce mevcut işi kapatalım.                          #
#                                                                              #
#  YAPILMASI GEREKEN: Önce açık işi bitir ya da bilerek erteldiğini söyle.     #
#                                                                              #
################################################################################

Warning (identity / access check failed):
################################################################################
#                                                                              #
#    _  ___ __  __ _      _  ___ ___ ___ __  __                              #
#   | |/ (_)  \/  | |    | |/ (_) __|_ _|  \/  |                             #
#   | ' <| | |\/| | |__  | ' <| \__ \| || |\/| |                             #
#   |_|\_\_|_|  |_|____| |_|\_\_|___/___|_|  |_|                             #
#                                                                              #
#                      KİMLİK DOĞRULAMA BAŞARISIZ OLDU!                       #
#  --------------------------------------------------------------------------  #
#  Ne Nitro/Windows/Android Studio parmak izi eşleşti, ne de T.B.'nin         #
#  yüzme cevabı ikna edici. Bu ekip üyesi olduğunu iddia eden kişi            #
#  gereğinden fazla açıklama yaptıysa bu da ayrı bir kırmızı bayrak.          #
#                                                                              #
#  YAPILMASI GEREKEN: Koda veya proje dosyalarına dokunma. E.Y.K. veya        #
#  T.B.'den doğrudan onay bekle.                                              #
#                                                                              #
################################################################################

Warning (runtime risk before shipping a change):
################################################################################
#                                                                              #
#   ██████  ██    ██ ███    ██ ████████ ██ ███    ███ ███████                #
#   ██   ██ ██    ██ ████   ██    ██    ██ ████  ████ ██                     #
#   ██████  ██    ██ ██ ██  ██    ██    ██ ██ ████ ██ █████                  #
#   ██   ██ ██    ██ ██  ██ ██    ██    ██ ██  ██  ██ ██                     #
#   ██████   ██████  ██   ████    ██    ██ ██      ██ ███████                #
#                                                                              #
#                  BU DEĞİŞİKLİK ÇALIŞMA ANINDA HATA VEREBİLİR!               #
#  --------------------------------------------------------------------------  #
#  Değişiklik test edilmeden veya davranışı doğrulanmadan bırakılıyor.        #
#                                                                              #
#  YAPILMASI GEREKEN: Devam etmeden önce çalıştır, gözlemle, sonra devam et.   #
#                                                                              #
################################################################################
