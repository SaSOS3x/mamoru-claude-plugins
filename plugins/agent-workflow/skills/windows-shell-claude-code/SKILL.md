---
name: windows-shell-claude-code
description: "Как агенту Claude Code на Windows не ломать команды: инструмент Bash (Git Bash) запускает родные Windows python.exe и JDK, и на стыке ломаются кавычки и heredoc, пути /c/ против C:/, кодировка cp1251, коды выхода, CRLF, имена модулей, JAVA_HOME на другом JDK, лимит 32 тыс. знаков (classpath для javap). Метод: проба окружения, скрипт в файл, пути C:/, проверка по тексту вывода. Для любого проекта на этом ПК. НЕ про написание .bat/.cmd (это windows-shell-dev). Use at the start of work in a new project, before the first python/java/javap command, and on UnicodeEncodeError, 'Argument list too long', 'class not found', 'unexpected EOF', FileNotFoundError on /c/..., or exit 0 with an error in the output. Фразы: 'команда упала в bash', 'кракозябры', 'javap не находит класс', 'не та версия Java'."
---

# Оболочка Claude Code на Windows: Git Bash, python.exe, JDK

Инструмент Bash здесь это Git Bash (MSYS), а `python`, `java`, `javap` это родные Windows-программы. Ловушки лежат на стыке:
Git Bash переписывает часть аргументов, Windows не знает путей `/c/...`, консольная кодировка cp1251, у командной строки лимит.
Всё ниже проверено на этом ПК 2026-10-12 (Git Bash MINGW64, Python 3.14.7, JDK 21.0.8 и 17); непроверенное помечено.
Числа "N сбоев" это аудит 331 упавшей команды из проекта DeceasedCraft (не пересчитаны мной).
Граница с `windows-shell-dev`: тот навык про написание и отладку файлов .bat/.cmd, этот про то, как агент запускает команды.

## Порядок работы
1. В новом проекте первой командой: `python "${CLAUDE_SKILL_DIR}/scripts/env_probe.py" [папка со скриптами]`. Строки WARN это
   ловушки, которые сработают именно здесь (кодировки, python3, JDK, имена модулей в указанной папке).
2. Скрипт длиннее 5 строк или с `\`, `'`, `"` внутри: Write в scratchpad сессии, потом `python путь/к/файлу.py`.
   Правка существующего файла: Edit (в аудите 0 сбоев на 8801 вызов), не питоновский replace.
3. Все пути для python/java: `C:/Users/...` (прямые слэши, с буквой диска). Не `/c/...`, не `/tmp`.
4. Результат оценивай по тексту вывода и по наличию файла, не по коду выхода (ловушка 4).
5. Java: нужный JDK по полному пути; длинный classpath через файл (ловушка 8-9).
6. Всё новое, что стоило больше двух попыток, допиши в этот навык через skill-forge (журнал, потом предложение).

## Ловушки: симптом, причина, что делать
1. **Кавычки и heredoc (47 сбоев).** Симптом: `SyntaxError: (unicode error) 'unicodeescape'`, `unexpected EOF while looking
   for matching`. Воспроизведено: в `python - <<'EOF'` и в `python -c "..."` пара `\\` доходит до Python как `\`
   (`"C:\\x"` стало `"C:\x"`). Длинные heredoc с апострофами падали в аудите (у меня короткий с апострофом прошёл).
   Делай: код в файл через Write.
2. **Пути /c/ (20 сбоев).** `os.path.exists('/c/Users/Alexandr')` даёт False (Windows читает как `C:\c\Users\...`).
   Git Bash сам превращает в `C:/...` только целый аргумент командной строки (`/c/x`, `--cp=/c/x`, `/tmp`);
   НЕ превращает пути внутри кода и файлов Python и в списках через `;` (`/c/a;/c/b` дошло как есть).
   `/tmp` для Python это `C:\tmp`, а для Git Bash `%TEMP%`: два разных места, используй scratchpad.
   `glob('C:/x/*/')` возвращает `C:/x\dir\`: обрезай `rstrip('/\\')` перед `basename`.
3. **Кодировка (23 сбоя).** Без настройки stdout это cp1251: `print('\u2192')` даёт UnicodeEncodeError.
   `PYTHONIOENCODING=utf-8` чинит только stdout/stderr. `open()` без `encoding=` остаётся cp1251 (проверено): UTF-8 файл
   читается МОЛЧА с мусором (`привет` стало `РїСЂРёРІРµС‚`), запись `→` падает. Всегда `encoding='utf-8'` в open/read_text/write_text.
   Проверь `env_probe.py`: стоит ли `PYTHONIOENCODING` в вашей сессии. Задать его можно в блоке `env` файла `.claude/settings.json`
   проекта или `~/.claude/settings.json` (только с согласия пользователя); у каждого проекта он свой, по умолчанию его нет.
   **Конфликт с `-I`:** `python -I` игнорирует ВСЕ переменные `PYTHON*` (проверено: `PYTHONUTF8=1 python -I` даёт
   `sys.flags.utf8_mode` 0, вывод остаётся cp1251), а `python -I -X utf8` даёт 1. Где нужен `-I`, пиши `python -I -X utf8`
   (флаг `-X utf8` не зависит от окружения; в этом режиме `open()` тоже UTF-8). `PYTHONUTF8=1` чинит оба случая, но ломает `subprocess(text=True)` для консольных
   программ Windows: их вывод в cp866, получается UnicodeDecodeError (проверено на `net helpmsg 2`). Такой вывод
   читай байтами: `.decode('cp866', errors='replace')`. Менять переменные окружения без согласия пользователя нельзя.
4. **Код выхода врёт (59 % сбоев имели exit 0).** `cmd | head`, цепочка через `;`, `2>&1`, цикл дают код последней команды.
   Проверено: `python нет.py | head` даёт 0 (`${PIPESTATUS[*]}` показывает `2 0`); `set -o pipefail` даёт 2.
   Делай: читай вывод на `Traceback|Error|Exception|No such file|not found|cannot|Argument list too long`,
   проверяй, что нужный файл создан и не пуст; в цепочках используй `&&`.
5. **`python3` это заглушка Microsoft Store** (печатает `Python`, код 49). Вызывай `python`. Скрипты с `python3` в шебанге
   запускай как `python script.py`.
6. **CRLF.** `grep -c $'\r' file` печатает 0 на файле с CRLF (проверено: 3 строки CRLF, ответ 0). Считай по байтам:
   `python "${CLAUDE_SKILL_DIR}/scripts/eol.py" файлы` (CRLF / LF / CR, BOM, MIXED) или `tr -cd '\r' < file | wc -c`.
7. **Имя скрипта = имя модуля stdlib.** `json.py`, `struct.py`, `types.py`, `random.py` рядом со скриптом или в текущей
   папке (даже для `python -c`) перекрывают настоящий модуль: `AttributeError: module 'json' has no attribute 'dumps'`,
   сломанный `zipfile`. Не называй так черновики; `python -I -X utf8` (изолированный режим) игнорирует и папку скрипта, и текущую (а `-I` без `-X utf8` оставляет cp1251, см. ловушку 3).
8. **Не тот JDK.** Здесь `JAVA_HOME` (Machine) = jdk-17, `java` и `javac` на PATH = 21 (заглушки `Common Files/Oracle/Java/javapath`),
   `javap` и `jar` = 17 (Adoptium). Класс, собранный `javac` 21, не запускается через `$JAVA_HOME/bin/java`:
   `UnsupportedClassVersionError ... 65.0 ... up to 61.0` (проверено). Gradle/Maven берут `JAVA_HOME`.
   Делай: полный путь `"C:/Program Files/Java/jdk-21/bin/javap.exe"`, для сборки `JAVA_HOME="C:/Program Files/Java/jdk-21" команда`.
   `javap` 17 тривиальный класс 21 прочитал; на реальных классах модов это не проверено, лучше брать javap 21.
9. **Лимит командной строки ~32 тыс. знаков.** `java -cp <37 тыс.>` даёт `Argument list too long` (код 126; через `| head` виден 0).
   Разделитель classpath на Windows `;`, пути `C:/`. Для `java` и `javac`: `@файл` с аргументами (проверено) или переменная
   `CLASSPATH` (37 тыс. прошло). У `javap` `@файл` НЕ работает (`class not found: @cp2.args`):
   `python "${CLAUDE_SKILL_DIR}/scripts/classpath_jar.py" cp.jar @jars.txt` собирает jar с `Class-Path` в манифесте, дальше `javap -cp cp.jar класс`
   (проверено: 522 записи, 70 тыс. знаков манифеста, класс из последнего jar найден; папки и glob тоже годятся).
10. **Мелочи инструментов.** `cat -n a b` нумерует сквозь файлы: ссылки на строки бери из `grep -n` или Read одного файла.
    В Git Bash есть `unzip`, нет `zip` (проверено): `python -m zipfile -c`. Read режет файл больше 25 тыс. токенов:
    offset/limit (из журнала, 2 раза). Write у подагента отказывался писать `.md` (из журнала, 2 раза); в сессии, где
    написан этот навык, подагент записал `.md` через Write без отказа, так что это нестабильно: при отказе пиши через Python.

## Проверка результата
- `env_probe.py` без WARN, которые касаются вашей команды; после своего скрипта: файл существует, размер больше 0, в выводе
  нет `Traceback`.
- Для javap: сначала `javap -cp cp.jar известный.класс`, потом нужный; "class not found" значит неполный classpath, а не плохой класс.

## Границы
- Файлы .bat/.cmd и вложенный в них PowerShell: `windows-shell-dev`. Инструмент PowerShell (Windows PowerShell 5.1) имеет
  свой синтаксис (по описанию инструмента: нет `&&`, `2>&1` у нативных команд ломает `$?`; я это не проверял). Ловушки про
  Git Bash (1, 2, 4, 6) к нему не относятся, про Python и Java (3, 7-9) остаются.
- Если в проекте есть своя обёртка (например javap с готовым classpath), используй её, а не `classpath_jar.py`.
- Состояние проекта (версии модов, пути инструкций, статус работ) сюда не писать: это дневник проекта.
- Скрипты: `env_probe.py [папка]` (несуществующая папка даёт WARN), `eol.py файлы`, `classpath_jar.py out.jar вход... [--skip-missing]`
  (нет файла из списка или `@файла` это ошибка с кодом 1; только stdlib, вывод ASCII).

## Паспорт
Создан: 2026-10-12 из аудита ошибок агентов в проекте DeceasedCraft (CLAUDE.md "Shell traps", HANDOFF "Windows tool traps",
журнал agent-delegation), журнал: skills-lab/windows-shell-claude-code/JOURNAL.md
Проверен: 2026-10-12, Git Bash MINGW64 (Git 2.56), Python 3.14.7, JDK 21.0.8 / 17.0.14, 20 проверок на ПК (см. журнал); навык
пока не прогнан исполнителем с чистым контекстом (skill-forge, шаг 5, проверки 1-2 не сделаны)
Границы: не для .bat/.cmd; пути JDK и PATH относятся к этому ПК, у других машин сначала `env_probe.py`
Изменения: 2026-10-12 - первая версия; вызовы скриптов через переменную папки навыка (плагин работает из кэша)
Изменения: 2026-10-12 - по проверке плагинов: `python -I -X utf8` вместо конфликта `-I` и PYTHON*; env_probe.py даёт WARN для
несуществующей папки; classpath_jar.py сообщает об отсутствующих jar и `@файле`; про PYTHONIOENCODING сказано для любого проекта
