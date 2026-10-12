# Changelog: windows-shell-dev

What changed in this skill, when and why. New entries go to the end. The skill was made by the user; its history before the
marketplace is not recorded here.

## 2026-10-12 | Added to the marketplace
What: the user's skill added to the plugin writing-and-scripts unchanged.
Why: the user's decision to keep all skills in one marketplace shared by projects.

## 2026-10-12 | Test .cmd files stored byte-exact
What: `.gitattributes` of the marketplace keeps `*.cmd`, `*.bat` and `*.ps1` byte-exact.
Why: with core.autocrlf the regression `.cmd` files were stored with LF, and the tests compare bytes.
Checked: 12/12 regression tests.

## 2026-10-12 | Fixes from the plugin check
What: every bundled-script call uses the skill folder variable; crlf_edit.py `replace` reads bytes, keeps CRLF and exits 1 when
nothing would change or lone LF would appear; Validate-Embedded.ps1 reads `\"` as a quote, warns when nothing was validated and
exits 2 for a missing file; setup_pwsh.sh refuses outside Linux and the text gives the Windows way; `python` instead of `python3`.
Why: an independent check (plugin-check, 2026-10-12): about 15 calls `python scripts/x.py` failed from the project folder,
crlf_edit wrote bare LF into a CRLF file with exit 0, Validate-Embedded gave a false BAD on `\"` and a green result for a file
without any PowerShell, setup_pwsh.sh installed a Linux build on Windows.
Checked: 12/12 regression tests; the recheck repeated every case.

## 2026-10-12 | One-line commands; UTF-8 output of Validate-Embedded.ps1
What: every command is one line; Validate-Embedded.ps1 writes UTF-8 when its output goes to a pipe and restores the console
encoding on every exit.
Why: the recheck (plugin-recheck, 2026-10-12): PowerShell rejects a trailing backslash (`Missing expression after unary operator
'--'`) although the text promised Git Bash and PowerShell alike; through a pipe the localized parser messages arrived in cp866.
Checked: the old and the new validator on the same broken file (garbage before, readable text after); 12/12 regression tests.
