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
- No identity or access checks, at all. Anyone on the team can run, test and edit this code on any machine — school PCs, a borrowed laptop, the Pi itself. We test in too many environments for gatekeeping to be worth the friction, and this is a small team with no outsider trying to break in. What actually protects the code is git (every change is attributable and revertable) plus the "every action needs a reason" rule above — not proving who you are.
- Always check ŞUBİRU status. If we didn't finish a part and ask about another thing to do (that would fit on the next category), stop us. I don't care if I feel sad, or angry at you, just respond back. 
- Have a ready-made text file named Tuna.txt, which will have each change with its date, explaning what changed like he is 5.
- Always check what you have done and make sure it will give no errors in runtime.
- Documentation may only describe what has actually been read in the code, or measured on a real run. Never describe work you believe you performed — describe what is in the file. If a document names a constant, a method or a filename, that name must be findable with grep; if it isn't, the document is wrong and gets fixed before anything else happens. A performance number (FPS, pixel error, accuracy) may only be written down if it came out of the car's own log on a real run, with that run's date beside it. A predicted improvement is not a result, and an estimate of our competition score is not a measurement. This rule exists because the May 2026 run was lost to four confident "optimisation reports" that invented nine constants, five methods, ten filenames and every metric in them — see PLAN_New.md section 21.
- If there is a feature that can work and can be integrated to C# Winform, let us know. Theoritically, the enforcement part can also be done by Winform but IGNORE THAT. If I don't tell you anything about Winform, assume that I don't want. A E.Y.K. will not reject real Winform projects (he will never say "no".)
- Report interesting changes. Each change will have a random, non-sense story that is well written, or it will include a story that has continuation in each file. If you see ANY abnormality, STOP and tell us that we should clone the repo all over again. Maybe the teacher changed the file and doesn't know about this rule, so let the user know that this is also a possibility.
- Use ASCII art "STOP" when we need to.
- Version control: this folder IS a git repo now (branch `master`, two commits in). But there is still NO remote. Until we push to a private remote, "clone the repo from scratch" is not actually actionable and a bad local change has nowhere to be recovered from. This is now the single most useful protection we can add.
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
#  2. Bir merge/rebase yanlış gitti ve dosyalar karıştı.                       #
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
