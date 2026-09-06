"""Testa o ciclo dos avisos sem iniciar a janela ou o instalador do aplicativo."""
import ast
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from types import SimpleNamespace
import traceback
import unittest

import flet as ft


class Picker:
    def __init__(self, on_result=None):
        self.on_result = on_result

    def pick_files(self):
        pass

    get_directory_path = pick_files
    save_file = pick_files


source = Path(__file__).resolve().parents[1] / "ALL_FOR_ONE.py"
tree = ast.parse(source.read_text(encoding="utf-8-sig"))
names = {"PluginOperation", "operation_logger", "operation_command", "OperationFilePicker"}
scope = dict(ft=ft, ContextVar=ContextVar, wraps=wraps, traceback=traceback,
             _active_operation=ContextVar("test_operation", default=None),
             _CompatibleFilePicker=Picker)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))
                             and n.name in names], type_ignores=[]), str(source), "exec"), scope)


class NotificationsTest(unittest.TestCase):
    def setUp(self):
        self.dialogs = []
        self.page = SimpleNamespace(open=self.dialogs.append, close=lambda d: self.dialogs.remove(d))
        self.log = scope["operation_logger"](lambda *a, **kw: None)
        self.picker = scope["OperationFilePicker"]

    def run_action(self, callback):
        scope["operation_command"](callback, self.page, "pt_BR", "Extrair", self.log)()

    def event(self, picker, selected=True):
        picker.on_result(SimpleNamespace(files=[SimpleNamespace(path="example")] if selected else [], path=None))

    def test_waits_for_processing_and_closes(self):
        picker = self.picker(on_result=lambda e: self.log("Concluído"))
        self.run_action(picker.pick_files)
        self.assertEqual(self.dialogs, [])
        self.event(picker)
        self.assertEqual(len(self.dialogs), 1)
        self.assertEqual(self.dialogs[0].title.value, "Processo concluído")
        self.dialogs[0].actions[0].on_click(None)
        self.assertEqual(self.dialogs, [])

    def test_logged_error_survives_success_summary(self):
        def process(e):
            self.log("Arquivo inválido", color="#EF4444")
            self.log("Fim do lote")
        picker = self.picker(on_result=process)
        self.run_action(picker.pick_files)
        self.event(picker)
        self.assertIn("erros", self.dialogs[0].title.value)
        self.assertIn("Arquivo inválido", self.dialogs[0].content.value)

    def test_exception(self):
        def process():
            raise ValueError("Falha de leitura")
        self.run_action(process)
        self.assertIn("Falha de leitura", self.dialogs[0].content.value)

    def test_cancel(self):
        picker = self.picker(on_result=lambda e: self.log("Cancelado"))
        self.run_action(picker.pick_files)
        self.event(picker, False)
        self.assertEqual(self.dialogs, [])

    def test_two_selections(self):
        second = self.picker(on_result=lambda e: self.log("Importado"))
        first = self.picker(on_result=lambda e: second.pick_files())
        self.run_action(first.pick_files)
        self.event(first)
        self.assertEqual(self.dialogs, [])
        self.event(second)
        self.assertEqual(len(self.dialogs), 1)

    def test_independent_operations(self):
        first = self.picker(on_result=lambda e: self.log("Erro", color="#EF4444"))
        second = self.picker(on_result=lambda e: self.log("OK"))
        self.run_action(first.pick_files)
        self.run_action(second.pick_files)
        self.event(second)
        self.event(first)
        self.assertEqual(self.dialogs[0].title.value, "Processo concluído")
        self.assertIn("erros", self.dialogs[1].title.value)


if __name__ == "__main__":
    unittest.main()
