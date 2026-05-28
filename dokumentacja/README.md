# Dokumentacja projektu

Plik główny: `main.tex` — kompiluje całą dokumentację do `main.pdf`.

## Struktura

```
dokumentacja/
├── main.tex                       # plik głowny (preambula, \input do sekcji)
└── sekcje/
    ├── 01_wstep.tex
    ├── 02_opis_zagadnienia.tex
    ├── 03_opis_algorytmow.tex
    ├── 04_aplikacja.tex
    ├── 05_eksperymenty.tex
    ├── 06_podsumowanie.tex
    ├── 07_literatura.tex
    └── 08_dodatek.tex
```

## Kompilacja

### pdflatex (najprostsze)

```bash
pdflatex main.tex
pdflatex main.tex     # drugi przebieg dla spisu treści i odnośników
```

### latexmk (zalecane, sam dba o przebiegi)

```bash
latexmk -pdf main.tex
# czyszczenie wygenerowanych plikow pomocniczych:
latexmk -c
```

### TeX Live / MiKTeX

Wymagane pakiety (zwykle są w standardowej dystrybucji): `babel` (`polish`),
`inputenc`, `fontenc`, `lmodern`, `geometry`, `fancyhdr`, `amsmath`,
`amssymb`, `mathtools`, `algorithm`, `algpseudocode`, `listings`, `xcolor`,
`graphicx`, `booktabs`, `array`, `longtable`, `enumitem`, `hyperref`,
`cleveref`, `microtype`.

## Czego brakuje (do uzupełnienia ręcznie)

- `sekcje/05_eksperymenty.tex` — surowe wyniki eksperymentów, tabele, wykresy.
