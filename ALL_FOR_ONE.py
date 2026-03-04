import os
import sys
import traceback
import threading
import json
import urllib.request
import urllib.error
import hashlib
import subprocess
import time
import importlib.util
from importlib.metadata import version, PackageNotFoundError
import xml.etree.ElementTree as _element_tree

sys.dont_write_bytecode = True
sys.modules.setdefault("xmltree", _element_tree)

# ==============================================================================
# 1. VERIFICAÇÃO DE AMBIENTE E INSTALADOR AUTOMÁTICO (Roda antes do Flet)
# ==============================================================================
def check_and_install_dependencies():
    required_flet = "0.28.3"
    flet_url = "https://github.com/flet-dev/flet/releases/download/v0.28.3/flet-0.28.3-py3-none-any.whl"
   
    try:
        installed_flet = version("flet")
    except PackageNotFoundError:
        installed_flet = None
    if installed_flet != required_flet:
        print(f"\n=======================================================")
        print(f" ⚠️ WARNING: Recommended Flet version not found! ")
        print(f" Installed : {installed_flet}")
        print(f" Recommended : {required_flet}")
        print(f"=======================================================")
       
        try:
            ans = input("\nDownload and install the recommended version? (y/n): ").strip().lower()
            if ans in ['y', 'yes', 's', 'sim']:
                print("\nDownloading and installing via pip... Please wait.")
                subprocess.check_call([sys.executable, "-m", "pip", "install", flet_url])
                print("\n✅ Installation complete! Restarting application...\n")
               
                # Reinicia o aplicativo com a nova versão instalada na mesma janela
                subprocess.Popen([sys.executable] + sys.argv)
                sys.exit(0)
            else:
                print("Proceeding with current version. (Note: Fallback compatibility mode ON)\n")
        except Exception:
            print("Proceeding...\n")
# Dispara o escudo ANTES da importação principal
check_and_install_dependencies()
# Só importamos de forma segura agora
import flet as ft
plugin_cache = {}
# ==============================================================================
# CAMADA DE COMPATIBILIDADE FLET 0.28.x ↔ 0.81+ & MONKEY PATCH PARA PLUGINS
# ==============================================================================
try:
    FLET_VERSION = tuple(map(int, getattr(ft, "__version__", "0.28.0").split(".")))
except Exception:
    FLET_VERSION = (0, 28, 0)
IS_MODERN = FLET_VERSION >= (0, 80, 0)
# ---------- CONSTANTES DE ALINHAMENTO ----------
if IS_MODERN:
    MAIN_START = getattr(ft.MainAxisAlignment, "START", "start")
    MAIN_CENTER = getattr(ft.MainAxisAlignment, "CENTER", "center")
    MAIN_END = getattr(ft.MainAxisAlignment, "END", "end")
    MAIN_SPACE_BETWEEN = getattr(ft.MainAxisAlignment, "SPACE_BETWEEN", "spaceBetween")
    CROSS_START = getattr(ft.CrossAxisAlignment, "START", "start")
    CROSS_CENTER = getattr(ft.CrossAxisAlignment, "CENTER", "center")
    CROSS_STRETCH = getattr(ft.CrossAxisAlignment, "STRETCH", "stretch")
    ALIGN_CENTER = getattr(ft.Alignment, "CENTER", ft.Alignment(0, 0))
    ALIGN_BOTTOM_LEFT = getattr(ft.Alignment, "BOTTOM_LEFT", ft.Alignment(-1, 1))
    ALIGN_TOP_CENTER = getattr(ft.Alignment, "TOP_CENTER", ft.Alignment(0, -1))
    ALIGN_BOTTOM_CENTER = getattr(ft.Alignment, "BOTTOM_CENTER", ft.Alignment(0, 1))
    FIT_COVER = getattr(getattr(ft, "ImageFit", None), "COVER", "cover")
else:
    MAIN_START = "start"
    MAIN_CENTER = "center"
    MAIN_END = "end"
    MAIN_SPACE_BETWEEN = "spaceBetween"
    CROSS_START = "start"
    CROSS_CENTER = "center"
    CROSS_STRETCH = "stretch"
    ALIGN_CENTER = getattr(ft, "alignment", ft).center if hasattr(ft, "alignment") else ft.Alignment(0, 0)
    ALIGN_BOTTOM_LEFT = getattr(ft, "alignment", ft).bottom_left if hasattr(ft, "alignment") else ft.Alignment(-1, 1)
    ALIGN_TOP_CENTER = getattr(ft, "alignment", ft).top_center if hasattr(ft, "alignment") else ft.Alignment(0, -1)
    ALIGN_BOTTOM_CENTER = getattr(ft, "alignment", ft).bottom_center if hasattr(ft, "alignment") else ft.Alignment(0, 1)
    FIT_COVER = "cover"
# ---------- WRAPPERS VISUAIS ----------
def _icon_val(icon_name):
    if isinstance(icon_name, str):
        try: return getattr(ft.Icons, icon_name.upper())
        except AttributeError: pass
    return icon_name
def compat_icon(icon_name, color=None, size=None):
    if IS_MODERN: return ft.Icon(icon=_icon_val(icon_name), color=color, size=size)
    return ft.Icon(name=icon_name, color=color, size=size)
def compat_icon_button(icon_name, icon_color=None, icon_size=None, on_click=None):
    if IS_MODERN: return ft.IconButton(icon=_icon_val(icon_name), icon_color=icon_color, icon_size=icon_size, on_click=on_click)
    return ft.IconButton(icon=icon_name, icon_color=icon_color, icon_size=icon_size, on_click=on_click)
def compat_padding_symmetric(horizontal=0, vertical=0):
    if IS_MODERN: return getattr(ft, "Padding")(left=horizontal, right=horizontal, top=vertical, bottom=vertical)
    return getattr(ft, "padding").symmetric(horizontal=horizontal, vertical=vertical)
def compat_padding_only(left=0, top=0, right=0, bottom=0):
    if IS_MODERN: return getattr(ft, "Padding")(left=left, top=top, right=right, bottom=bottom)
    return getattr(ft, "padding").only(left=left, top=top, right=right, bottom=bottom)
def compat_border_all(width, color):
    if IS_MODERN:
        bs = getattr(ft, "BorderSide")(width=width, color=color)
        return getattr(ft, "Border")(top=bs, right=bs, bottom=bs, left=bs)
    return getattr(ft, "border").all(width, color)
def compat_dropdown_option(text_val):
    try: return getattr(ft.dropdown, "Option")(key=text_val, text=text_val)
    except Exception: return getattr(ft.dropdown, "Option")(text_val)
def compat_dropdown(**kwargs):
    on_change_handler = kwargs.pop("on_change", None)
    dd = ft.Dropdown(**kwargs)
    if on_change_handler:
        if IS_MODERN and hasattr(dd, "on_select"): dd.on_select = on_change_handler
        else: dd.on_change = on_change_handler
    return dd
def compat_window_props(page, w, h, always_on_top):
    if hasattr(page, "window"):
        page.window.width, page.window.height, page.window.always_on_top = w, h, always_on_top
    else:
        page.window_width, page.window_height, page.window_always_on_top = w, h, always_on_top
def compat_run(main_fn):
    if hasattr(ft, "run"): ft.run(main_fn)
    else: ft.app(target=main_fn)
# ---------- MONKEY PATCH FLET FILEPICKER PARA PLUGINS ----------
# Esta classe falsa substitui o `ft.FilePicker` original. Assim, qualquer plugin externo
# que usar "ft.FilePicker(on_result=X)" será interceptado aqui e não vai travar na versão 0.80+.
OriginalFilePicker = ft.FilePicker
class ModernFilePickerWrapper(ft.Container):
    def __init__(self, on_result=None, **kwargs):
        super().__init__(width=0, height=0, visible=False)
        self.on_result = on_result
        self._fp = OriginalFilePicker()
    def did_mount(self):
        super().did_mount()
        # Injerta o serviço real por debaixo dos panos ao ser adicionado no overlay
        if hasattr(self.page, "services"):
            if self._fp not in self.page.services:
                self.page.services.append(self._fp)
                self.page.update()
    class MockEvent:
        def __init__(self, files, path):
            self.files = files
            self.path = path
    def pick_files(self, allowed_extensions=None, **kwargs):
        if not self.page: return
        async def _pick():
            try:
                files = await self._fp.pick_files(allowed_extensions=allowed_extensions, **kwargs)
                if self.on_result: self.on_result(self.MockEvent(files, None))
                self.page.update()
            except Exception as e:
                print("FP Pick Error:", e)
        self.page.run_task(_pick)
    def get_directory_path(self, dialog_title=None, **kwargs):
        if not self.page: return
        async def _dir():
            try:
                path = await self._fp.get_directory_path(dialog_title=dialog_title, **kwargs)
                if self.on_result: self.on_result(self.MockEvent(None, path))
                self.page.update()
            except Exception as e:
                print("FP Dir Error:", e)
        self.page.run_task(_dir)
    def save_file(self, dialog_title=None, file_name=None, **kwargs):
        if not self.page: return
        async def _save():
            try:
                path = await self._fp.save_file(dialog_title=dialog_title, file_name=file_name, **kwargs)
                if self.on_result: self.on_result(self.MockEvent(None, path))
                self.page.update()
            except Exception as e:
                print("FP Save Error:", e)
        self.page.run_task(_save)
if IS_MODERN:
    ft.FilePicker = ModernFilePickerWrapper
# ==============================================================================
# 2. CONFIGURAÇÕES VISUAIS E TRADUÇÕES
# ==============================================================================
COLOR_BG = "#111827"
COLOR_SIDEBAR = "#1F2937"
COLOR_ACCENT = "#2563EB"
COLOR_BORDER = "#374151"
COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"
COLOR_CARD = "#1a2233"
COLOR_PLACEHOLDER = "#273142"
BANNER_HEIGHT = 100
REPO_API_URL = "https://api.github.com/repos/TicoDoido/all_for_one/contents/plugins"
LANG_MAP = {
    "Português (BR)": "pt_BR",
    "English (US)": "en_US",
    "Español (ES)": "es_ES"
}
LANG_NAME_BY_CODE = {v: k for k, v in LANG_MAP.items()}
UI_STRINGS = {
    "pt_BR": {
        "title_select": "Selecione um Plugin",
        "desc_empty": "Hub de ferramentas para extrair, converter e reempacotar arquivos de jogos.",
        "sidebar_lang": "IDIOMA",
        "sidebar_tools": "LISTA DE PLUGINS",
        "log_title": "LOG DO SISTEMA",
        "searching": "Atualizando lista...",
        "loading": "Carregando: {name}",
        "update_downloading": "Baixando: {name}...",
        "update_success": "Sincronização concluída!",
        "update_error": "Erro: {err}",
        "config_title": "CONFIGURAÇÕES"
    },
    "en_US": {
        "title_select": "Select a Plugin",
        "desc_empty": "A toolbox hub to extract, convert, and repack game files.",
        "sidebar_lang": "LANGUAGE",
        "sidebar_tools": "PLUGINS LIST",
        "log_title": "SYSTEM LOG",
        "searching": "Refreshing list...",
        "loading": "Loading: {name}",
        "update_downloading": "Downloading: {name}...",
        "update_success": "Sync completed!",
        "update_error": "Error: {err}",
        "config_title": "SETTINGS"
    },
    "es_ES": {
        "title_select": "Selecciona un Plugin",
        "desc_empty": "Centro de herramientas para extraer, convertir y reempaquetar archivos de juegos.",
        "sidebar_lang": "IDIOMA",
        "sidebar_tools": "LISTA DE PLUGINS",
        "log_title": "REGISTRO DEL SISTEMA",
        "searching": "Actualizando lista...",
        "loading": "Cargando: {name}",
        "update_downloading": "Descargando: {name}...",
        "update_success": "¡Sincronización completada!",
        "update_error": "Error: {err}",
        "config_title": "CONFIGURACIÓN"
    }
}
# ==============================================================================
# 3. BACKEND (Plugin Manager)
# ==============================================================================
class PluginManager:
    def __init__(self, log_callback):
        self.current_plugin_options = {}
        self.log_callback = log_callback
        try:
            if getattr(sys, "frozen", False):
                # Em builds onefile (PyInstaller), os recursos externos ficam ao lado do .exe.
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base_path = os.getcwd()
        self.plugin_dir = os.path.join(base_path, "plugins")
        self.banner_dir = os.path.join(base_path, "banners")
    def load_plugin_data(self, plugin_name, language="pt_BR", page=None):
        if plugin_name in plugin_cache:
            module = plugin_cache[plugin_name]
        else:
            candidate_paths = [
                os.path.join(self.plugin_dir, f"{plugin_name}.py"),
                os.path.join(self.plugin_dir, f"{plugin_name}.pyc")
            ]
            plugin_path = next((path for path in candidate_paths if os.path.exists(path)), None)
            if plugin_path is None:
                return None
            try:
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Não foi possível criar loader para: {plugin_path}")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                plugin_cache[plugin_name] = module
            except Exception as e:
                self.log_callback(f"Erro no plugin {plugin_name}: {e}", color=COLOR_LOG_RED)
                return None
        if hasattr(module, "register_plugin"):
            import inspect
            def get_opt(name): return self.current_plugin_options.get(name, {}).get("value")
           
            try:
                sig = inspect.signature(module.register_plugin)
                # Verifica estritamente quantos argumentos o plugin aceita para não crachar a injeção
                if len(sig.parameters) >= 4:
                    res = module.register_plugin(self.log_callback, get_opt, language, page)
                else:
                    res = module.register_plugin(self.log_callback, get_opt, language)
            except Exception as e:
                self.log_callback(f"Erro de interface com o plugin {plugin_name}: {e}", color=COLOR_LOG_RED)
                traceback.print_exc()
                return None
               
            return res() if callable(res) else res
        return None
    def get_all_plugins_list(self):
        if not os.path.exists(self.plugin_dir):
            return []

        plugins = {}
        for filename in os.listdir(self.plugin_dir):
            if filename == "__init__.py" or filename.startswith("__"):
                continue
            if filename.endswith(".py"):
                plugins[filename[:-3]] = ".py"
            elif filename.endswith(".pyc"):
                plugin_name = filename[:-4]
                # Prioriza versão fonte caso ambas existam.
                plugins.setdefault(plugin_name, ".pyc")

        return sorted(plugins.keys())
# ==============================================================================
# 4. FUNÇÕES AUXILIARES
# ==============================================================================
def calculate_git_sha(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        size = len(data)
        header = f"blob {size}\0".encode()
        sha1 = hashlib.sha1()
        sha1.update(header + data)
        return sha1.hexdigest()
    except:
        return None
# ==============================================================================
# 5. INTERFACE GRÁFICA
# ==============================================================================
def main(page: ft.Page):
    page.title = "All For One Manager"
    page.theme_mode = "dark"
    page.bgcolor = COLOR_BG
    page.padding = 0
   
    compat_window_props(page, 1150, 850, False)
    state = {"language_code": "pt_BR", "current_plugin": None}
   
    def t(key, **kwargs):
        txt = UI_STRINGS.get(state["language_code"], UI_STRINGS["pt_BR"]).get(key, key)
        return txt.format(**kwargs) if kwargs else txt
    # --- Log ---
    log_column = ft.Column(scroll="always", expand=True)
    log_history = []
    log_buffer = []
    last_update_time = [0]
   
    def log_ui(msg, color=COLOR_LOG_GREEN):
        log_history.append(msg)
        log_buffer.append(msg)
        current_time = time.time()
        if color == COLOR_LOG_RED or (current_time - last_update_time[0]) > 0.1:
            if log_buffer:
                batch_msg = "".join(log_buffer)
                log_column.controls.append(
                    ft.Text(value=batch_msg, font_family="Consolas", color=color, size=11, no_wrap=False)
                )
                log_buffer.clear()
               
                if len(log_column.controls) > 50:
                    log_column.controls.pop(0)
               
                last_update_time[0] = current_time
                page.update()
               
                if IS_MODERN:
                    async def _scroll():
                        try: await log_column.scroll_to(offset=-1, duration=50)
                        except Exception: pass
                    page.run_task(_scroll)
                else:
                    try: log_column.scroll_to(offset=-1, duration=50)
                    except Exception: pass

    def copy_log(_):
        full_log = "".join(log_history).strip() or "(log vazio)"
        try:
            page.set_clipboard(full_log)
            log_ui("\n[INFO] Log copiado para a área de transferência.\n", color=COLOR_LOG_YELLOW)
        except Exception as e:
            log_ui(f"\n[ERRO] Falha ao copiar log: {e}\n", color=COLOR_LOG_RED)
    manager = PluginManager(log_ui)
    # --- Componentes Principais ---
    plugin_content_area = ft.Column(expand=True, scroll="auto", spacing=12)
    plugin_list_view = ft.ListView(expand=True, spacing=2, padding=5)
   
    lbl_title = ft.Text(value=t("title_select"), size=20, weight="black", color="white")
    lbl_desc = ft.Text(value=t("desc_empty"), size=11, color="#E5E7EB")
    # --- Lógica de Foco e Execução ---
    def safe_run_action(action):
        def run_with_focus():
            try:
                try:
                    import win32gui
                    import win32con
                    has_win32 = True
                except:
                    has_win32 = False
               
                action()
                time.sleep(0.2)
               
                if has_win32:
                    def enum_windows_callback(hwnd, windows):
                        if win32gui.IsWindowVisible(hwnd):
                            class_name = win32gui.GetClassName(hwnd)
                            if 'tk' in class_name.lower() or 'Toplevel' in class_name:
                                windows.append(hwnd)
                        return True
                   
                    windows = []
                    win32gui.EnumWindows(enum_windows_callback, windows)
                   
                    for hwnd in windows:
                        win32gui.SetForegroundWindow(hwnd)
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                else:
                    try:
                        import tkinter as tk
                        root = tk._default_root
                        if root:
                            for widget in root.winfo_children():
                                if isinstance(widget, tk.Toplevel):
                                    widget.lift()
                                    widget.focus_force()
                                    widget.attributes('-topmost', True)
                                    widget.after(100, lambda w=widget: w.attributes('-topmost', False))
                    except:
                        pass
                       
            except Exception as e:
                log_ui(f"Erro ao executar ação: {str(e)}", color=COLOR_LOG_RED)
                traceback.print_exc()
       
        threading.Thread(target=run_with_focus, daemon=True).start()
    # --- Sincronização de Plugins ---
    def download_folder_recursive(api_url, local_dir, state_data):
        if not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
       
        with urllib.request.urlopen(req) as r:
            items = json.loads(r.read().decode())
       
        for item in items:
            if item['type'] == 'dir':
                download_folder_recursive(item['url'], os.path.join(local_dir, item['name']), state_data)
            elif item['type'] == 'file':
                local_path = os.path.join(local_dir, item['name'])
                rel_path = os.path.relpath(local_path, manager.plugin_dir)
               
                needs_download = False
                if not os.path.exists(local_path):
                    needs_download = True
                elif state_data.get(rel_path) != item['sha']:
                    local_git_sha = calculate_git_sha(local_path)
                    if local_git_sha != item['sha']:
                        needs_download = True
               
                if needs_download:
                    log_ui(t("update_downloading", name=item['name']), color=COLOR_LOG_YELLOW)
                    urllib.request.urlretrieve(item['download_url'], local_path)
                    state_data[rel_path] = item['sha']
                   
    def sync_plugins():
        try:
            log_ui(t("searching"), color=COLOR_LOG_YELLOW)
            state_file = os.path.join(manager.plugin_dir, "plugins_state.json")
            state_data = {}
           
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
           
            files_to_check = list(state_data.keys())
            for rel_path in files_to_check:
                local_path = os.path.join(manager.plugin_dir, rel_path)
                if not os.path.exists(local_path):
                    log_ui(f"Arquivo deletado localmente: {rel_path}", color=COLOR_LOG_YELLOW)
                    del state_data[rel_path]
           
            download_folder_recursive(REPO_API_URL, manager.plugin_dir, state_data)
           
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=4)
           
            log_ui(t("update_success"))
            refresh_sidebar()
           
        except Exception as e:
            log_ui(t("update_error", err=str(e)), color=COLOR_LOG_RED)
            traceback.print_exc()
    # --- Helper Botão Sleek ---
    def create_sleek_button(label, action):
        return ft.Container(
            content=ft.Row([
                compat_icon(icon_name="play_arrow", color="white", size=16),
                ft.Text(value=label, size=11, weight="bold", color="white", expand=True, text_align="center")
            ], alignment=MAIN_CENTER, spacing=10),
            padding=compat_padding_symmetric(horizontal=20, vertical=12),
            bgcolor=COLOR_BG,
            border=compat_border_all(1, COLOR_ACCENT),
            border_radius=6,
            ink=not IS_MODERN, # Desativa ink no Flet 0.80+ para não bugar a expansão
            expand=True,
            on_click=lambda _: safe_run_action(action),
            on_hover=lambda e: setattr(e.control, "bgcolor", "#1f2c4d" if e.data == "true" else COLOR_BG) or e.control.update()
        )
    # --- Renderização do Plugin ---
    def render_plugin_ui(plugin_file):
        state["current_plugin"] = plugin_file
        plugin_content_area.controls.clear()
        manager.current_plugin_options = {}
        log_ui(t("loading", name=plugin_file))
        data = manager.load_plugin_data(plugin_file, state["language_code"], page)
        if not data: return
        lbl_title.value = data.get('name', '')
        lbl_desc.value = data.get('description', '')
        banner_path = os.path.join(manager.banner_dir, f"{plugin_file}.jpg")
        if os.path.exists(banner_path):
            banner_bg = ft.Image(src=banner_path, width=float("inf"), height=BANNER_HEIGHT, fit=FIT_COVER, border_radius=8)
        else:
            banner_bg = ft.Container(width=float("inf"), height=BANNER_HEIGHT, bgcolor=COLOR_PLACEHOLDER, border_radius=8, alignment=ALIGN_CENTER, content=compat_icon(icon_name="image", color=COLOR_BORDER, size=40))
        banner_stack = ft.Stack(
            controls=[
                banner_bg,
                ft.Container(
                    alignment=ALIGN_BOTTOM_LEFT,
                    padding=compat_padding_only(left=20, top=20, right=20, bottom=10),
                    gradient=getattr(ft, "LinearGradient")(
                        begin=ALIGN_TOP_CENTER,
                        end=ALIGN_BOTTOM_CENTER,
                        colors=["transparent", "#111827"],
                        stops=[0.2, 1.0]
                    ),
                    content=ft.Column([
                        lbl_title,
                        lbl_desc
                    ], spacing=2, tight=True),
                    border_radius=8
                )
            ],
            height=BANNER_HEIGHT
        )
        plugin_content_area.controls.append(banner_stack)
        if 'options' in data and data['options']:
            opts = data['options']
            plugin_content_area.controls.append(ft.Text(value=t("config_title"), size=10, weight="bold", color="grey"))
            for i in range(0, len(opts), 2):
                row = ft.Row(spacing=15, alignment=MAIN_START, vertical_alignment=CROSS_START)
                for j in range(i, min(i + 2, len(opts))):
                    opt = opts[j]
                    radio_group = ft.RadioGroup(content=ft.Column([
                        ft.Radio(value=v, label=v, label_style=getattr(ft, "TextStyle")(size=10) if hasattr(ft, "TextStyle") else None) for v in opt.get('values', [])
                    ], spacing=2))
                    radio_group.value = opt.get('values')[0] if opt.get('values') else None
                    manager.current_plugin_options[opt['name']] = {"control": radio_group, "value": radio_group.value}
                    radio_group.on_change = lambda e, n=opt['name']: manager.current_plugin_options[n].update({"value": e.control.value})
                    card = ft.Container(
                        content=ft.Column([
                            ft.Text(value=opt['label'].upper(), weight="bold", color="#60A5FA", size=9),
                            ft.Divider(height=1, color=COLOR_BORDER),
                            radio_group
                        ], tight=True, spacing=10),
                        padding=12, bgcolor=COLOR_CARD, border_radius=6, border=compat_border_all(1, COLOR_BORDER), expand=True
                    )
                    row.controls.append(card)
                if len(row.controls) == 1: row.controls.append(ft.Container(expand=True))
                plugin_content_area.controls.append(row)
        if 'commands' in data:
            cmds = data['commands']
            for i in range(0, len(cmds), 2):
                row_btns = ft.Row(spacing=10, alignment=MAIN_START, vertical_alignment=CROSS_START)
                for j in range(i, min(i + 2, len(cmds))):
                    row_btns.controls.append(create_sleek_button(cmds[j]['label'], cmds[j]['action']))
                if len(row_btns.controls) == 1: row_btns.controls.append(ft.Container(expand=True))
                plugin_content_area.controls.append(row_btns)
        page.update()
    def refresh_sidebar():
        log_ui(t("searching"))
        plugin_list_view.controls.clear()
        for f in manager.get_all_plugins_list():
            data = manager.load_plugin_data(f, state["language_code"])
            display_name = data.get('name', f) if data else f
           
            item = ft.Container(
                content=ft.Row(
                    controls=[
                        compat_icon(icon_name="extension", color="#60A5FA", size=14),
                        ft.Text(value=display_name, size=11, expand=True, no_wrap=False),
                    ],
                    spacing=8,
                    vertical_alignment=CROSS_START,
                ),
                padding=10, border_radius=6, on_click=lambda e, f=f: render_plugin_ui(f), ink=not IS_MODERN,
                on_hover=lambda e: setattr(e.control, "bgcolor", COLOR_BORDER if e.data == "true" else None) or e.control.update()
            )
            plugin_list_view.controls.append(item)
        page.update()
    def change_lang(e):
        state["language_code"] = LANG_MAP.get(e.control.value, "pt_BR")
        refresh_sidebar()
        if state["current_plugin"]: render_plugin_ui(state["current_plugin"])
    # --- Sidebar ---
    btn_refresh = compat_icon_button(icon_name="refresh", icon_size=18, on_click=lambda _: refresh_sidebar())
    btn_update = compat_icon_button(icon_name="cloud_download", icon_color="#60A5FA", icon_size=18, on_click=lambda _: threading.Thread(target=sync_plugins, daemon=True).start())
    sidebar = ft.Container(
        width=280, bgcolor=COLOR_SIDEBAR, padding=20,
        content=ft.Column(controls=[
            ft.Row([ft.Text(value="ALL FOR ONE", size=16, weight="black", color="#60A5FA"), ft.Row([btn_update, btn_refresh], spacing=0)], alignment=MAIN_SPACE_BETWEEN),
            ft.Divider(height=20, color="transparent"),
            ft.Text(value=t("sidebar_lang"), size=9, weight="bold", color="grey"),
            compat_dropdown(width=240, text_size=11, value=LANG_NAME_BY_CODE["pt_BR"], options=[compat_dropdown_option(n) for n in LANG_MAP.keys()], on_change=change_lang, bgcolor="#374151", border_color="transparent"),
            ft.Divider(height=20, color="transparent"),
            ft.Text(value=t("sidebar_tools"), size=9, weight="bold", color="grey"),
            ft.Container(content=plugin_list_view, expand=True)
        ])
    )
    content = ft.Container(
        expand=True, padding=35,
        content=ft.Column(controls=[
            plugin_content_area,
            ft.Container(height=10),
            ft.Row(
                controls=[
                    ft.Text(value=t("log_title"), size=9, color="grey", weight="bold", expand=True),
                    compat_icon_button(icon_name="content_copy", icon_color="#9CA3AF", icon_size=16, on_click=copy_log),
                ],
                alignment=MAIN_SPACE_BETWEEN,
                vertical_alignment=CROSS_CENTER,
            ),
            ft.Container(height=140, bgcolor="black", border_radius=8, padding=10, content=log_column, border=compat_border_all(1, "#374151"))
        ], horizontal_alignment=CROSS_STRETCH)
    )
    page.add(ft.Row([sidebar, content], expand=True, spacing=0))
    refresh_sidebar()
if __name__ == "__main__":
    compat_run(main)
