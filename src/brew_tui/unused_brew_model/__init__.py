"""unused_brew_model: a structural Python translation of real Homebrew's Ruby
class model — accurate to how `brew` is actually organized internally, but not
wired into brew-tui's actual implementation.

    tap.py         -> Library/Homebrew/tap.rb
    spec.py        -> Library/Homebrew/software_spec.rb, resource.rb, download_strategy.rb
    dependency.py  -> Library/Homebrew/dependency.rb, dependency_collector.rb
    formula.py     -> Library/Homebrew/formula.rb
    formulary.py   -> Library/Homebrew/formulary.rb
    installer.py   -> Library/Homebrew/formula_installer.rb (+ bottle-vs-compile
                       policy from PR #10788)
    keg_model.py   -> Library/Homebrew/keg.rb, tab.rb (the Keg/Tab half of
                       keg.rb; the plain `Cellar` path-wrapper half of that same
                       real file stayed live, at src/brew_tui/keg.py)

None of `tui.py` / `e2e.py` / `commands.py`'s real command classes import from
here. The live implementation (`RealCellarReader` + `BrewCLIRunner`, in
db.py/cli_runner.py) gets the same end results a different way: reading
Homebrew's own INSTALL_RECEIPT.json off disk and shelling out to the real
`brew` executable, rather than reimplementing Homebrew's tap-cloning, bottle
resolution, dependency-graph resolution, and pour/compile logic in Python (see
each file's own module docstring for what that would take).

Kept as a reference for that alternative, fully in-process design; moved into
its own subdirectory to make that separation from the live code explicit.
"""
