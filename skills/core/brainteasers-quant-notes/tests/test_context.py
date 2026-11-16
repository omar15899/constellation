"""Behavioral checks of version selection, source order and honest evidence."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "notes_context", Path(__file__).resolve().parents[1] / "scripts/context.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def manual(self, name: str, body: str = "\\chapter{Inicio}\n") -> Path:
        return self.write(f"{name}/latex/main.tex", "\\documentclass{book}\n"
                          "\\begin{document}\n" + body + "\\end{document}\n")

    def test_relocated_cli_reads_the_active_vault_and_supports_an_explicit_course(self) -> None:
        course = self.root / "05_Projects/Brainteasers_Quant"
        self.write("05_Projects/Brainteasers_Quant/V9_Apuntes/latex/main.tex",
                   "\\documentclass{book}\n\\begin{document}\n\\chapter{Ejemplo}\n")
        cmd = [sys.executable, "-B", str(SPEC.origin)]
        for args, cwd in (([], self.root), ([], course), (["--root", str(course)], self.root)):
            result = subprocess.run(cmd + args, cwd=cwd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["version"], 9)
        absent = subprocess.run(cmd + ["--root", str(self.root / "ausente")],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(absent.returncode, 2)
        self.assertIn("No existe el proyecto", json.loads(absent.stderr)["error"])

    def test_numeric_latest_changes_between_requests(self) -> None:
        self.manual("V2_Taller")
        self.manual("V9_Apuntes")
        self.assertEqual(MODULE.select(self.root).number, 9)
        self.manual("V10_Apuntes")
        self.assertEqual(MODULE.select(self.root).number, 10)

    def test_explicit_older_version_wins(self) -> None:
        older = self.manual("V2_Taller")
        self.manual("V12_Apuntes")
        self.assertEqual(MODULE.select(self.root, older.parents[1]).number, 2)

    def test_same_number_variants_are_not_guessed(self) -> None:
        self.manual("V8_Apuntes")
        self.manual("V8_Apuntes_corregida")
        with self.assertRaises(MODULE.ContextError):
            MODULE.select(self.root)

    def test_bank_and_generated_pdf_do_not_win(self) -> None:
        self.manual("V12_Apuntes")
        self.manual("V99_Repositorio_de_Problemas")
        self.write("V13_Exportacion/manual.pdf", "PDF")
        self.write("asincronas/v100/main.tex", "\\documentclass{beamer}")
        self.assertEqual(MODULE.select(self.root).number, 12)

    def test_new_unrecognized_manual_blocks_fallback(self) -> None:
        self.manual("V12_Apuntes")
        self.write("V13_Apuntes/fuentes/libro.tex", "\\begin{document}")
        with self.assertRaises(MODULE.ContextError):
            MODULE.select(self.root)

    def test_custom_entry_is_supported_without_guessing(self) -> None:
        path = self.write("V13_Apuntes/fuentes/libro.tex", "\\chapter{Nuevo}")
        selection = MODULE.select(self.root, path.parents[1], "fuentes/libro.tex")
        self.assertEqual(selection.entry, path.resolve())

    def test_graph_preserves_order_and_ignores_orphans_and_comments(self) -> None:
        entry = self.manual("V12_Apuntes", "% \\input{curso/omitido}\n"
                            "\\input{curso/b}\n\\input{curso/a}\n")
        self.write("V12_Apuntes/latex/curso/b.tex", "\\chapter{B}\n\\label{cap:b}")
        self.write("V12_Apuntes/latex/curso/a.tex", "\\chapter{A {anidado}}")
        self.write("V12_Apuntes/latex/curso/huerfano.tex", "\\chapter{Huérfano}")
        graph = MODULE.source_graph(entry, entry.parents[1])
        self.assertEqual([item["title"] for item in graph["outline"]], ["B", "A {anidado}"])
        self.assertEqual(graph["labels"][0]["line"], 2)
        self.assertFalse(graph["warnings"])

    def test_dynamic_missing_and_cyclic_inputs_are_reported(self) -> None:
        entry = self.manual("V12_Apuntes", "\\input{main}\n\\input{missing}\n\\input{#1}")
        graph = MODULE.source_graph(entry, entry.parents[1])
        self.assertEqual(len(graph["warnings"]), 3)

    def test_search_has_real_lines_accents_context_and_truncation(self) -> None:
        path = self.write("source.tex", "% equivalencia ignorada\n"
                          "Relación de equivalencia\nClases de equivalencia\n")
        found = MODULE.search([str(path)], ["relacion", "equivalencia"], 1)
        self.assertEqual(found["matching_lines"], 2)
        self.assertEqual(found["matches"][0]["line"], 2)
        self.assertTrue(found["truncated"])

    def test_escaping_percent_preserves_content(self) -> None:
        self.assertEqual(MODULE.uncomment("50\\% válido % oculto\n"),
                         "50\\% válido         \n")

    def test_dependency_cannot_escape_version(self) -> None:
        self.write("outside.tex", "\\chapter{Privado}")
        entry = self.manual("V12_Apuntes", "\\input{../../outside}")
        graph = MODULE.source_graph(entry, entry.parents[1])
        self.assertEqual(len(graph["files"]), 1)
        self.assertTrue(graph["warnings"])

    def test_explicit_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            (self.root / "V13_Apuntes").symlink_to(other, target_is_directory=True)
            with self.assertRaises(MODULE.ContextError):
                MODULE.select(self.root, self.root / "V13_Apuntes")


if __name__ == "__main__":
    unittest.main()
