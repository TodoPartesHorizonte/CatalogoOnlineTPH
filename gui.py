# Importar torch y easyocr al inicio en el hilo principal para evitar conflictos de DLLs (WinError 1114) con tkinter/customtkinter
try:
    import easyocr
except Exception:
    pass

import os
import sys
import json
import queue
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

# Importar el script generator para llamar a sus funciones directamente
import generator

class LogStream:
    """Clase para redirigir la salida estándar de sys.stdout a una cola de Tkinter."""
    def __init__(self, log_queue):
        self.log_queue = log_queue
        
    def write(self, text):
        self.log_queue.put(text)
        
    def flush(self):
        pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de Ventana
        self.title("TODO PARTES Horizonte - Gestor de Catálogo")
        self.geometry("840x780")
        self.minsize(800, 700)

        # Establecer apariencia oscura y tema naranja
        ctk.set_appearance_mode("dark")
        
        # Colas para hilos seguros
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        
        self.stdout_orig = sys.stdout
        self.stderr_orig = sys.stderr

        # Datos en memoria para el editor de catálogo
        self.editor_products_in_memory = []
        self.editor_entries = {}
        self.editor_current_page = 0
        self.editor_page_size = 40
        self.newly_added_product_ids = []

        # Configurar rejilla principal de la ventana
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Cabecera fija
        self.grid_rowconfigure(1, weight=1) # El contenedor de pestañas se expande

        # --- CABECERA ---
        self.header_frame = ctk.CTkFrame(self, height=75, corner_radius=0, fg_color="#121216")
        self.header_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="TODO PARTES HORIZONTE", 
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#ff6a00"
        )
        self.title_label.grid(row=0, column=0, pady=(10, 1))
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame, 
            text="Administración y Sincronización del Catálogo Online", 
            font=ctk.CTkFont(size=11, weight="normal"),
            text_color="#a0a0a8"
        )
        self.subtitle_label.grid(row=1, column=0, pady=(0, 10))

        # --- CONTENEDOR DE PESTAÑAS (TABVIEW) ---
        self.tabview = ctk.CTkTabview(self, fg_color="transparent")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 5))
        
        # Definir las pestañas
        self.tabview.add("Sincronización")
        self.tabview.add("Editor de Catálogo")
        
        # Enlazar evento al cambiar de pestaña
        self.tabview.configure(command=self.on_tab_changed)

        # Configurar layouts de pestañas
        self.setup_sincronizacion_tab()
        self.setup_editor_tab()

        # Cargar valores guardados al iniciar
        self.load_config_values()
        
        # Cargar vista previa del calibrador OCR inicial si existe
        self.load_ocr_preview_image()

        # Iniciar polling de la cola de logs y progreso
        self.update_log_widget()

    # --- MAQUETACIÓN DE PESTAÑA: SINCRONIZACIÓN ---
    def setup_sincronizacion_tab(self):
        tab = self.tabview.tab("Sincronización")
        tab.grid_columnconfigure(0, weight=1) # Columna izquierda (Formulario y calibrador)
        tab.grid_columnconfigure(1, weight=1, minsize=370) # Columna derecha (Consola, Progreso, Botones)
        tab.grid_rowconfigure(0, weight=1)

        # Columna Izquierda: Scrollable Frame para Ajustes + Calibrador
        self.left_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.left_scroll.grid(row=0, column=0, sticky="nsew", padx=(5, 10), pady=5)
        self.left_scroll.grid_columnconfigure(0, weight=1)

        # Frame de Ajustes Básicos
        self.config_frame = ctk.CTkFrame(self.left_scroll)
        self.config_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.config_frame.grid_columnconfigure(0, weight=1)
        self.config_frame.grid_columnconfigure(1, weight=0)

        # Campos del formulario
        self.lbl_origen = ctk.CTkLabel(self.config_frame, text="Carpeta de Origen (Fotos):", font=ctk.CTkFont(weight="bold"))
        self.lbl_origen.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 2))
        
        self.entry_origen = ctk.CTkEntry(self.config_frame, placeholder_text="Seleccione la carpeta con las fotos...")
        self.entry_origen.grid(row=1, column=0, sticky="ew", padx=(15, 5), pady=(0, 10))
        
        self.btn_origen = ctk.CTkButton(
            self.config_frame, text="Buscar Carpeta", width=120, fg_color="#ff6a00", hover_color="#e05e00",
            font=ctk.CTkFont(weight="bold"), command=self.browse_origen_folder
        )
        self.btn_origen.grid(row=1, column=1, sticky="e", padx=(5, 15), pady=(0, 10))

        self.lbl_logo = ctk.CTkLabel(self.config_frame, text="Logotipo de la Empresa (Opcional):", font=ctk.CTkFont(weight="bold"))
        self.lbl_logo.grid(row=2, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 2))
        
        self.entry_logo = ctk.CTkEntry(self.config_frame, placeholder_text="Seleccione el archivo del logo (PNG, JPG)...")
        self.entry_logo.grid(row=3, column=0, sticky="ew", padx=(15, 5), pady=(0, 10))
        
        self.btn_logo = ctk.CTkButton(
            self.config_frame, text="Seleccionar Logo", width=120, fg_color="#ff6a00", hover_color="#e05e00",
            font=ctk.CTkFont(weight="bold"), command=self.browse_logo_file
        )
        self.btn_logo.grid(row=3, column=1, sticky="e", padx=(5, 15), pady=(0, 10))

        # Enlaces Rápidos
        self.lbl_whatsapp = ctk.CTkLabel(self.config_frame, text="WhatsApp (ej: 584242116375):", font=ctk.CTkFont(weight="bold"))
        self.lbl_whatsapp.grid(row=4, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 2))
        self.entry_whatsapp = ctk.CTkEntry(self.config_frame, placeholder_text="Ej: 584242116375")
        self.entry_whatsapp.grid(row=5, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 10))

        self.lbl_instagram = ctk.CTkLabel(self.config_frame, text="Instagram URL:", font=ctk.CTkFont(weight="bold"))
        self.lbl_instagram.grid(row=6, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 2))
        self.entry_instagram = ctk.CTkEntry(self.config_frame, placeholder_text="https://instagram.com/nombre")
        self.entry_instagram.grid(row=7, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 10))

        self.lbl_facebook = ctk.CTkLabel(self.config_frame, text="Facebook URL:", font=ctk.CTkFont(weight="bold"))
        self.lbl_facebook.grid(row=8, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 2))
        self.entry_facebook = ctk.CTkEntry(self.config_frame, placeholder_text="https://facebook.com/pagina")
        self.entry_facebook.grid(row=9, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 10))

        self.lbl_maps = ctk.CTkLabel(self.config_frame, text="Google Maps URL:", font=ctk.CTkFont(weight="bold"))
        self.lbl_maps.grid(row=10, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 2))
        self.entry_maps = ctk.CTkEntry(self.config_frame, placeholder_text="Enlace de Google Maps...")
        self.entry_maps.grid(row=11, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 10))

        self.lbl_reviews = ctk.CTkLabel(self.config_frame, text="Enlace Reseñas Google:", font=ctk.CTkFont(weight="bold"))
        self.lbl_reviews.grid(row=12, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 2))
        self.entry_reviews = ctk.CTkEntry(self.config_frame, placeholder_text="Enlace para dejar opiniones...")
        self.entry_reviews.grid(row=13, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))

        # --- SECCIÓN: CALIBRADOR VISUAL OCR ---
        self.calibrator_frame = ctk.CTkFrame(self.left_scroll)
        self.calibrator_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=10)
        self.calibrator_frame.grid_columnconfigure(0, weight=1)

        self.lbl_calibrator_title = ctk.CTkLabel(self.calibrator_frame, text="Calibración Visual del Área OCR", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ff6a00")
        self.lbl_calibrator_title.grid(row=0, column=0, sticky="w", padx=15, pady=(12, 10))

        # Etiqueta de la imagen de vista previa
        self.ocr_preview_label = ctk.CTkLabel(
            self.calibrator_frame, text="Presione 'Previsualizar Recorte' para cargar imagen",
            fg_color="#0a0a0c", corner_radius=8, height=270
        )
        self.ocr_preview_label.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))

        # Controles de Sliders
        self.slider_frame = ctk.CTkFrame(self.calibrator_frame, fg_color="transparent")
        self.slider_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.slider_frame.grid_columnconfigure(1, weight=1)

        # Límite superior
        self.lbl_slider_top = ctk.CTkLabel(self.slider_frame, text="Límite Superior OCR %:", font=ctk.CTkFont(weight="bold"), width=150, anchor="w")
        self.lbl_slider_top.grid(row=0, column=0, sticky="w", pady=5)
        
        self.slider_ocr_top = ctk.CTkSlider(self.slider_frame, from_=0.0, to=1.0, number_of_steps=100, command=self.on_top_slider_move)
        self.slider_ocr_top.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        self.entry_ocr_top = ctk.CTkEntry(self.slider_frame, width=50)
        self.entry_ocr_top.grid(row=0, column=2, sticky="e", pady=5)

        # Límite inferior
        self.lbl_slider_bottom = ctk.CTkLabel(self.slider_frame, text="Límite Inferior OCR %:", font=ctk.CTkFont(weight="bold"), width=150, anchor="w")
        self.lbl_slider_bottom.grid(row=1, column=0, sticky="w", pady=5)
        
        self.slider_ocr_bottom = ctk.CTkSlider(self.slider_frame, from_=0.0, to=1.0, number_of_steps=100, command=self.on_bottom_slider_move)
        self.slider_ocr_bottom.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        self.entry_ocr_bottom = ctk.CTkEntry(self.slider_frame, width=50)
        self.entry_ocr_bottom.grid(row=1, column=2, sticky="e", pady=5)

        # Botón para actualizar previsualización
        self.btn_preview_ocr = ctk.CTkButton(
            self.calibrator_frame, text="Previsualizar Recorte", fg_color="#ff6a00", hover_color="#e05e00",
            font=ctk.CTkFont(weight="bold"), command=self.start_ocr_preview_thread
        )
        self.btn_preview_ocr.grid(row=3, column=0, sticky="ew", padx=15, pady=(5, 15))


        # Columna Derecha: Panel de Consola, Progreso y Botones de Acción
        self.right_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 5), pady=5)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1) # Consola se estira
        
        # Botones Superiores Rápidos
        self.quick_btn_frame = ctk.CTkFrame(self.right_frame)
        self.quick_btn_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 10))
        self.quick_btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.btn_save = ctk.CTkButton(
            self.quick_btn_frame, text="Guardar Ajustes", height=38, fg_color="#2b2b36", hover_color="#3d3d4d",
            command=self.save_config
        )
        self.btn_save.grid(row=0, column=0, padx=(12, 6), pady=12, sticky="ew")

        self.btn_clear = ctk.CTkButton(
            self.quick_btn_frame, text="Eliminar Catálogo Viejo", height=38, fg_color="#d9534f", hover_color="#c9302c",
            font=ctk.CTkFont(weight="bold"), command=self.clear_old_catalog
        )
        self.btn_clear.grid(row=0, column=1, padx=(6, 12), pady=12, sticky="ew")

        # Área de Consola
        self.log_frame = ctk.CTkFrame(self.right_frame)
        self.log_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        self.lbl_log = ctk.CTkLabel(self.log_frame, text="Consola de Sincronización y Salida:", font=ctk.CTkFont(weight="bold"))
        self.lbl_log.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        self.txt_log = ctk.CTkTextbox(self.log_frame, fg_color="#0a0a0c", border_color="#1c1c24", border_width=1)
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.txt_log.configure(state="disabled")

        # --- SECCIÓN: BARRA DE PROGRESO DE SINCRONIZACIÓN ---
        self.progress_frame = ctk.CTkFrame(self.right_frame)
        self.progress_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Estado: En espera de procesamiento", font=ctk.CTkFont(size=11), anchor="w")
        self.progress_label.grid(row=0, column=0, sticky="ew", padx=15, pady=(8, 2))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, progress_color="#ff6a00")
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.progress_bar.set(0.0)

        # Botones Principales de Procesamiento Abajo
        self.action_btn_frame = ctk.CTkFrame(self.right_frame)
        self.action_btn_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=(10, 5))
        self.action_btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_generate = ctk.CTkButton(
            self.action_btn_frame, text="Generar Catálogo (Procesar)", height=45, fg_color="#ff6a00", hover_color="#e05e00",
            font=ctk.CTkFont(weight="bold"), command=self.start_catalog_generation
        )
        self.btn_generate.grid(row=0, column=0, padx=(15, 8), pady=12, sticky="ew")

        self.btn_publish = ctk.CTkButton(
            self.action_btn_frame, text="Publicar en GitHub Pages", height=45, fg_color="#25d366", hover_color="#1f9c4d",
            font=ctk.CTkFont(weight="bold"), command=self.start_github_publish
        )
        self.btn_publish.grid(row=0, column=1, padx=(8, 15), pady=12, sticky="ew")

    # --- MAQUETACIÓN DE PESTAÑA: EDITOR DE CATÁLOGO ---
    def setup_editor_tab(self):
        tab = self.tabview.tab("Editor de Catálogo")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1) # El frame scrollable central se expande

        # 1. Buscador superior
        self.search_frame = ctk.CTkFrame(tab)
        self.search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.entry_editor_search = ctk.CTkEntry(self.search_frame, placeholder_text="Buscar repuesto en el editor por nombre o categoría...")
        self.entry_editor_search.grid(row=0, column=0, sticky="ew", padx=(15, 5), pady=(12, 6))
        
        # Enlazar la tecla Enter al buscador
        self.entry_editor_search.bind("<Return>", lambda event: self.trigger_editor_search())

        self.btn_editor_search = ctk.CTkButton(
            self.search_frame, text="Buscar", width=100, fg_color="#ff6a00", hover_color="#e05e00",
            font=ctk.CTkFont(weight="bold"), command=self.trigger_editor_search
        )
        self.btn_editor_search.grid(row=0, column=1, padx=(5, 5), pady=(12, 6))

        self.btn_editor_clear = ctk.CTkButton(
            self.search_frame, text="Limpiar", width=100, fg_color="#2b2b36", hover_color="#3d3d4d",
            command=self.clear_editor_search
        )
        self.btn_editor_clear.grid(row=0, column=2, padx=(5, 15), pady=(12, 6))

        # Checkbox para mostrar solo nuevos
        self.var_only_new = tk.BooleanVar(value=False)
        self.chk_only_new = ctk.CTkCheckBox(
            self.search_frame, text="Mostrar solo repuestos nuevos (agregados/modificados en esta sesión)",
            variable=self.var_only_new, command=self.trigger_only_new_toggle,
            fg_color="#ff6a00", hover_color="#e05e00"
        )
        self.chk_only_new.grid(row=1, column=0, columnspan=3, sticky="w", padx=15, pady=(0, 10))

        # 2. Scrollable Frame Central
        self.editor_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.editor_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.editor_scroll.grid_columnconfigure(0, weight=1)

        # 3. Panel de Paginación
        self.pagination_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.pagination_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        self.pagination_frame.grid_columnconfigure((0, 2), weight=1)

        self.btn_prev_page = ctk.CTkButton(
            self.pagination_frame, text="◀ Anterior", width=120, fg_color="#2b2b36", hover_color="#3d3d4d",
            font=ctk.CTkFont(weight="bold"), command=self.prev_page
        )
        self.btn_prev_page.grid(row=0, column=0, padx=20, pady=5, sticky="e")

        self.lbl_page_info = ctk.CTkLabel(
            self.pagination_frame, text="Página 1 de 1", font=ctk.CTkFont(weight="bold")
        )
        self.lbl_page_info.grid(row=0, column=1, padx=20, pady=5)

        self.btn_next_page = ctk.CTkButton(
            self.pagination_frame, text="Siguiente ▶", width=120, fg_color="#2b2b36", hover_color="#3d3d4d",
            font=ctk.CTkFont(weight="bold"), command=self.next_page
        )
        self.btn_next_page.grid(row=0, column=2, padx=20, pady=5, sticky="w")

        # 4. Panel Inferior de Acciones
        self.editor_actions_frame = ctk.CTkFrame(tab)
        self.editor_actions_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=(10, 5))
        self.editor_actions_frame.grid_columnconfigure(0, weight=1)

        self.lbl_editor_status = ctk.CTkLabel(self.editor_actions_frame, text="Cargando productos...", font=ctk.CTkFont(weight="bold"))
        self.lbl_editor_status.grid(row=0, column=0, sticky="w", padx=20, pady=15)

        self.btn_editor_save = ctk.CTkButton(
            self.editor_actions_frame, text="Guardar Cambios del Editor", height=42, width=220, fg_color="#ff6a00", hover_color="#e05e00",
            font=ctk.CTkFont(weight="bold"), command=self.save_editor_changes
        )
        self.btn_editor_save.grid(row=0, column=1, padx=20, pady=15)

    # --- CONTROL DE LAS PESTAÑAS (TABS) ---
    def on_tab_changed(self):
        current_tab = self.tabview.get()
        if current_tab == "Editor de Catálogo":
            self.load_editor_data()

    # --- CONTROL DE ARCHIVOS Y CARPETAS ---
    def browse_origen_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar Carpeta Origen de Fotos")
        if folder:
            self.entry_origen.delete(0, tk.END)
            self.entry_origen.insert(0, os.path.normpath(folder))
            # Regenerar vista previa con la nueva carpeta
            self.start_ocr_preview_thread()

    def browse_logo_file(self):
        file = filedialog.askopenfilename(
            title="Seleccionar Imagen de Logotipo",
            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if file:
            self.entry_logo.delete(0, tk.END)
            self.entry_logo.insert(0, os.path.normpath(file))

    def clear_old_catalog(self):
        if messagebox.askyesno("Eliminar Catálogo Viejo", "¿Estás seguro de que deseas eliminar el catálogo actual?\n\nEsto borrará la base de datos (products.js) y todas las imágenes procesadas (.webp) de la carpeta web, forzando una reconstrucción completa en la próxima generación."):
            try:
                js_path = Path("web/products.js")
                if js_path.exists():
                    os.remove(js_path)
                
                assets_dir = Path("web/assets")
                if assets_dir.exists():
                    for item in assets_dir.iterdir():
                        # Conservar el logo si existe y no borrar la carpeta
                        if item.is_file() and not item.name.startswith("logo."):
                            os.remove(item)
                            
                self.write_to_log("Catálogo viejo eliminado correctamente.\nSe borraron la base de datos y los archivos WebP locales.\nListo para una reconstrucción completa.\n")
                
                # Limpiar el editor si está abierto
                self.editor_products_in_memory = []
                self.render_editor_list()
                
                # Resetear vista previa de calibración
                preview_file_path = assets_dir / "ocr_crop_preview.jpg"
                if preview_file_path.exists():
                    os.remove(preview_file_path)
                self.load_ocr_preview_image()
                
                messagebox.showinfo("Éxito", "El catálogo viejo ha sido eliminado correctamente.")
            except Exception as e:
                self.write_to_log(f"Error al limpiar el catálogo: {e}\n")
                messagebox.showerror("Error", f"No se pudo limpiar el catálogo: {e}")

    # --- LECTURA Y ESCRITURA DE AJUSTES ---
    def load_config_values(self):
        config = generator.load_config()
        self.entry_origen.insert(0, config.get("catalogo_origen_path", ""))
        self.entry_whatsapp.insert(0, config.get("whatsapp_number", ""))
        self.entry_logo.insert(0, config.get("logo_path", ""))
        self.entry_instagram.insert(0, config.get("instagram_url", ""))
        self.entry_facebook.insert(0, config.get("facebook_url", ""))
        self.entry_maps.insert(0, config.get("maps_url", ""))
        self.entry_reviews.insert(0, config.get("reviews_url", ""))
        
        # Sliders y entries de OCR
        crop_top = config.get("ocr_crop_top", 0.33)
        crop_bottom = config.get("ocr_crop_bottom", 0.55)
        
        self.slider_ocr_top.set(crop_top)
        self.slider_ocr_bottom.set(crop_bottom)
        
        self.entry_ocr_top.delete(0, tk.END)
        self.entry_ocr_top.insert(0, f"{crop_top:.2f}")
        
        self.entry_ocr_bottom.delete(0, tk.END)
        self.entry_ocr_bottom.insert(0, f"{crop_bottom:.2f}")
        
        self.write_to_log("Configuración cargada correctamente.\n")

    def save_config(self, show_msg=True):
        try:
            # Validar que sean flotantes válidos
            crop_top = float(self.entry_ocr_top.get().strip() or "0.33")
            crop_bottom = float(self.entry_ocr_bottom.get().strip() or "0.55")
        except ValueError:
            self.write_to_log("[Error] Los límites de recorte OCR deben ser números válidos (ej: 0.33 y 0.55).\n")
            if show_msg:
                messagebox.showerror("Error", "Los límites de recorte OCR deben ser números válidos (ej: 0.33 y 0.55).")
            return False

        config = {
            "catalogo_origen_path": self.entry_origen.get().strip(),
            "whatsapp_number": self.entry_whatsapp.get().strip(),
            "logo_path": self.entry_logo.get().strip(),
            "instagram_url": self.entry_instagram.get().strip(),
            "facebook_url": self.entry_facebook.get().strip(),
            "maps_url": self.entry_maps.get().strip(),
            "reviews_url": self.entry_reviews.get().strip(),
            "ocr_crop_top": crop_top,
            "ocr_crop_bottom": crop_bottom
        }
        
        # Guardar en config.json
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Actualizar rápidamente products.js con los nuevos enlaces y logo
            generator.update_js_links(config)
            
            if show_msg:
                self.write_to_log("Ajustes guardados y aplicados directamente en el catálogo.\n")
                messagebox.showinfo("Éxito", "Los ajustes se han guardado y aplicado de inmediato en el catálogo.")
            return True
        except Exception as e:
            self.write_to_log(f"Error al guardar la configuración: {e}\n")
            if show_msg:
                messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")
            return False

    # --- CONTROLADORES DE SLIDERS DE CALIBRACIÓN OCR ---
    def on_top_slider_move(self, val):
        self.entry_ocr_top.delete(0, tk.END)
        self.entry_ocr_top.insert(0, f"{val:.2f}")

    def on_bottom_slider_move(self, val):
        self.entry_ocr_bottom.delete(0, tk.END)
        self.entry_ocr_bottom.insert(0, f"{val:.2f}")

    def load_ocr_preview_image(self):
        """Intenta cargar la imagen de vista previa generada de ocr_crop_preview.jpg"""
        preview_path = Path("web/assets/ocr_crop_preview.jpg")
        if preview_path.exists():
            try:
                pil_img = Image.open(preview_path)
                # Redimensionar para encajar visualmente (proporción 4:3 en ancho de 360px)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(360, 270))
                self.ocr_preview_label.configure(image=ctk_img, text="")
                self.ocr_preview_label.image = ctk_img # Conservar referencia
            except Exception as e:
                self.ocr_preview_label.configure(text=f"Error cargando vista previa: {e}", image=None)
        else:
            self.ocr_preview_label.configure(text="Seleccione la carpeta origen de fotos\ny presione 'Previsualizar Recorte'", image=None)

    def start_ocr_preview_thread(self):
        """Genera y carga la previsualización del OCR en segundo plano."""
        self.btn_preview_ocr.configure(state="disabled", text="Generando...")
        thread = threading.Thread(target=self.run_ocr_preview, daemon=True)
        thread.start()

    def run_ocr_preview(self):
        try:
            # Obtener primera imagen del catálogo
            first_img = generator.get_first_product_image()
            if not first_img:
                self.write_to_log("[Calibrador OCR] No se encontraron imágenes en la carpeta origen para la calibración.\n")
                self.after(0, lambda: messagebox.showwarning("Aviso", "No se encontraron fotos en la carpeta origen para calibrar el OCR. Por favor seleccione una carpeta que contenga imágenes."))
                return

            try:
                crop_top = float(self.entry_ocr_top.get().strip() or "0.33")
                crop_bottom = float(self.entry_ocr_bottom.get().strip() or "0.55")
            except ValueError:
                self.write_to_log("[Calibrador OCR] Valores de margen inválidos.\n")
                return

            assets_dir = Path("web/assets")
            assets_dir.mkdir(parents=True, exist_ok=True)
            preview_path = assets_dir / "ocr_crop_preview.jpg"
            
            # Generar
            generator.generate_crop_preview(first_img, crop_top, crop_bottom, preview_path)
            
            # Recargar en pantalla
            self.after(0, self.load_ocr_preview_image)
        except Exception as e:
            self.write_to_log(f"[Calibrador OCR] Error al generar la vista previa: {e}\n")
        finally:
            self.after(0, lambda: self.btn_preview_ocr.configure(state="normal", text="Previsualizar Recorte"))

    # --- SISTEMA DE LOGS Y PROGRESO ---
    def write_to_log(self, text):
        self.txt_log.configure(state="normal")
        self.txt_log.insert(tk.END, text)
        self.txt_log.see(tk.END)
        self.txt_log.configure(state="disabled")

    def update_log_widget(self):
        """Pulla las colas de logs y progreso para actualizar la interfaz de forma segura."""
        # 1. Procesar logs de consola
        while not self.log_queue.empty():
            try:
                text = self.log_queue.get_nowait()
                self.write_to_log(text)
            except queue.Empty:
                break
                
        # 2. Procesar barra de progreso
        while not self.progress_queue.empty():
            try:
                current, total, status = self.progress_queue.get_nowait()
                
                # Calcular porcentaje
                fraction = 0.0
                if total > 0:
                    fraction = current / total
                
                self.progress_bar.set(fraction)
                self.progress_label.configure(text=f"Estado: {status} ({current}/{total})")
            except queue.Empty:
                break
                
        # Volver a llamar a esta función en 100ms
        self.after(100, self.update_log_widget)

    # --- PROCESAMIENTO EN SEGUNDO PLANO (SINCRONIZACIÓN) ---
    def start_catalog_generation(self):
        # Guardar configuración antes de correr
        if not self.save_config(show_msg=False):
            return

        # Desactivar botones para evitar ejecuciones concurrentes
        self.btn_generate.configure(state="disabled", text="Procesando...")
        self.btn_clear.configure(state="disabled")
        self.btn_publish.configure(state="disabled")
        self.btn_save.configure(state="disabled")
        
        self.progress_bar.set(0.0)
        self.progress_label.configure(text="Estado: Iniciando...")

        self.write_to_log("\n===================================================\n")
        self.write_to_log("INICIANDO PROCESAMIENTO DE IMÁGENES Y OCR...\n")
        self.write_to_log("===================================================\n")

        # Redirigir la salida estándar de Python a la interfaz
        sys.stdout = LogStream(self.log_queue)
        sys.stderr = LogStream(self.log_queue)

        # Iniciar el hilo del generador
        thread = threading.Thread(target=self.run_generation)
        thread.daemon = True
        thread.start()

    def run_generation(self):
        try:
            # Callback interno de progreso que escribe en la cola
            def on_progress(current, total, status_text):
                self.progress_queue.put((current, total, status_text))
            
            # Ejecutar el generador pasándole el callback
            newly_processed_ids = generator.sync_catalog(progress_callback=on_progress)
            if newly_processed_ids is None:
                newly_processed_ids = []
        except Exception as e:
            print(f"\nERROR durante la ejecución: {e}")
            newly_processed_ids = []
        finally:
            # Restaurar salida estándar
            sys.stdout = self.stdout_orig
            sys.stderr = self.stderr_orig
            
            # Reactivar la UI en el hilo principal
            self.after(0, lambda: self.finish_generation(newly_processed_ids))

    def finish_generation(self, newly_processed_ids):
        self.btn_generate.configure(state="normal", text="Generar Catálogo (Procesar)")
        self.btn_clear.configure(state="normal")
        self.btn_publish.configure(state="normal")
        self.btn_save.configure(state="normal")
        
        # Recargar la vista previa de la primera imagen tras el procesamiento por si cambió
        self.load_ocr_preview_image()
        
        # Guardar los IDs nuevos/modificados
        self.newly_added_product_ids = newly_processed_ids
        
        if newly_processed_ids:
            # Activar el check de solo nuevos
            self.var_only_new.set(True)
            # Cambiar a la pestaña del Editor
            self.tabview.set("Editor de Catálogo")
            self.load_editor_data()
            
            # Mostrar alerta informativa
            messagebox.showinfo(
                "Nuevos Repuestos Sincronizados",
                f"¡Se han añadido/modificado {len(newly_processed_ids)} productos en el catálogo!\n\n"
                "Hemos activado automáticamente el filtro 'Mostrar solo repuestos nuevos' en el Editor para que puedas revisar y corregir el OCR directamente."
            )
        else:
            self.var_only_new.set(False)
            if self.tabview.get() == "Editor de Catálogo":
                self.load_editor_data()

        self.write_to_log("\n===================================================\n")
        self.write_to_log("PROCESO TERMINADO EN LOCAL.\n")
        self.write_to_log("===================================================\n")

    # --- PUBLICACIÓN EN GITHUB EN SEGUNDO PLANO ---
    def start_github_publish(self):
        # Verificar si Git está inicializado
        if not os.path.exists("web/.git"):
            self.write_to_log("\n[ERROR] Git no está inicializado en la carpeta 'web'.\n")
            self.write_to_log("Por favor, realiza la configuración inicial de Git antes de subir.\n")
            messagebox.showerror("Error", "Git no está inicializado en la carpeta 'web'. Revisa la configuración de Git en la consola.")
            return

        self.btn_generate.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        self.btn_publish.configure(state="disabled", text="Publicando...")
        self.btn_save.configure(state="disabled")

        self.write_to_log("\n===================================================\n")
        self.write_to_log("SUBIENDO ACTUALIZACIONES A GITHUB PAGES...\n")
        self.write_to_log("===================================================\n")

        thread = threading.Thread(target=self.run_publish)
        thread.daemon = True
        thread.start()

    def run_publish(self):
        try:
            # Comandos git secuenciales
            commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", "Actualizacion desde Administrador de Catalogo"],
                ["git", "push", "origin", "main", "--force"]
            ]
            
            web_path = os.path.abspath("web")
            
            for cmd in commands:
                self.log_queue.put(f"Ejecutando: {' '.join(cmd)}\n")
                process = subprocess.Popen(
                    cmd, 
                    cwd=web_path, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    shell=True # Necesario en Windows para resolver PATH de Git
                )
                stdout, stderr = process.communicate()
                
                if stdout.strip():
                    self.log_queue.put(f"{stdout}\n")
                if stderr.strip() and process.returncode != 0: # Mostrar stderrs solo si hay error
                    self.log_queue.put(f"[Alerta/Error]: {stderr}\n")
                
                if process.returncode != 0:
                    if cmd[1] == "commit" and "nothing to commit" in stdout + stderr:
                        self.log_queue.put("No hay cambios nuevos para guardar en el commit.\n")
                    else:
                        self.log_queue.put(f"El comando falló con código {process.returncode}\n")
                        
        except Exception as e:
            self.log_queue.put(f"\nERROR al publicar en GitHub: {e}\n")
        finally:
            self.after(0, self.finish_publish)

    def finish_publish(self):
        self.btn_generate.configure(state="normal")
        self.btn_clear.configure(state="normal")
        self.btn_publish.configure(state="normal", text="Publicar en GitHub Pages")
        self.btn_save.configure(state="normal")
        self.write_to_log("\n===================================================\n")
        self.write_to_log("PROCESO DE SUBIDA COMPLETADO.\n")
        self.write_to_log("Tu sitio web tardará 1-2 minutos en actualizarse en internet.\n")
        self.write_to_log("===================================================\n")
        messagebox.showinfo("Éxito", "¡El catálogo ha sido publicado en GitHub Pages! Los cambios estarán visibles en internet en 1-2 minutos.")

    # --- LÓGICA DE CONTROL: EDITOR DE CATÁLOGO (TAB 2) ---
    def load_editor_data(self):
        """Carga la base de datos completa de products.js en memoria."""
        self.editor_current_page = 0
        self.lbl_editor_status.configure(text="Cargando productos del catálogo...")
        
        # Ejecutar carga en un hilo ligero para que no se trabe el cambio de pestaña
        def run_load():
            try:
                data = generator.read_catalog_js()
                if data and "products" in data:
                    self.editor_products_in_memory = data["products"]
                    status_text = f"Cargados {len(self.editor_products_in_memory)} productos. Escribe para buscar."
                else:
                    self.editor_products_in_memory = []
                    status_text = "Catálogo vacío. Genere el catálogo primero."
                
                # Volver a renderizar en el hilo principal
                self.after(0, lambda: self.render_editor_list())
                self.after(0, lambda: self.lbl_editor_status.configure(text=status_text))
            except Exception as e:
                self.after(0, lambda: self.lbl_editor_status.configure(text=f"Error al cargar base de datos: {e}"))
        
        threading.Thread(target=run_load, daemon=True).start()

    def save_current_entries_to_memory(self):
        """Guarda en memoria las descripciones editadas en los campos actualmente visibles."""
        if not hasattr(self, 'editor_entries') or not self.editor_entries:
            return 0
        edited_count = 0
        for product_id, entry in self.editor_entries.items():
            try:
                new_desc = entry.get().strip().upper()
                product = next((p for p in self.editor_products_in_memory if p["id"] == product_id), None)
                if product and product["description"] != new_desc:
                    product["description"] = new_desc
                    # Regenerar keywords
                    product["keywords"] = generator.generate_keywords(new_desc, product["category"])
                    edited_count += 1
            except Exception:
                pass
        return edited_count

    def prev_page(self):
        self.save_current_entries_to_memory()
        if self.editor_current_page > 0:
            self.editor_current_page -= 1
            query = self.entry_editor_search.get().strip()
            self.render_editor_list(query)

    def next_page(self):
        self.save_current_entries_to_memory()
        query = self.entry_editor_search.get().strip()
        normalized_query = query.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        
        filtered = []
        for p in self.editor_products_in_memory:
            desc_norm = p["description"].lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            cat_norm = p["category"].lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            
            if not query or normalized_query in desc_norm or normalized_query in cat_norm:
                filtered.append(p)
                
        total_found = len(filtered)
        max_pages = (total_found + self.editor_page_size - 1) // self.editor_page_size
        
        if self.editor_current_page < max_pages - 1:
            self.editor_current_page += 1
            self.render_editor_list(query)

    def trigger_editor_search(self):
        self.save_current_entries_to_memory()
        self.editor_current_page = 0
        query = self.entry_editor_search.get().strip()
        self.render_editor_list(query)

    def clear_editor_search(self):
        self.save_current_entries_to_memory()
        self.editor_current_page = 0
        self.entry_editor_search.delete(0, tk.END)
        self.render_editor_list()

    def trigger_only_new_toggle(self):
        self.editor_current_page = 0
        query = self.entry_editor_search.get().strip()
        self.render_editor_list(query)

    def delete_product_action(self, product_id, category):
        if messagebox.askyesno(
            "Confirmar Eliminación", 
            f"¿Estás seguro de que deseas eliminar permanentemente este repuesto del catálogo?\n\n"
            f"ID: {product_id}\nCategoría: {category}\n\n"
            "Esto borrará la imagen original de la carpeta de origen y el archivo WebP optimizado del catálogo web."
        ):
            success, msg = generator.delete_product(product_id, category)
            if success:
                # Remover de memoria local de la UI
                self.editor_products_in_memory = [p for p in self.editor_products_in_memory if p["id"] != product_id]
                if product_id in self.newly_added_product_ids:
                    self.newly_added_product_ids.remove(product_id)
                
                self.write_to_log(f"\n[Editor] Repuesto {product_id} ({category}) eliminado con éxito.\n")
                
                # Refrescar listado
                query = self.entry_editor_search.get().strip()
                self.render_editor_list(query)
                messagebox.showinfo("Éxito", "El repuesto se ha eliminado correctamente del catálogo y de la carpeta origen.")
            else:
                self.write_to_log(f"\n[Editor] Error al eliminar {product_id}: {msg}\n")
                messagebox.showerror("Error", f"No se pudo eliminar el repuesto: {msg}")

    def render_editor_list(self, query=""):
        """Dibuja en pantalla los repuestos coincidentes con la búsqueda, paginados."""
        # Limpiar scroll frame de items anteriores
        for widget in self.editor_scroll.winfo_children():
            widget.destroy()

        self.editor_entries = {}
        
        # Si no hay productos cargados en memoria
        if not self.editor_products_in_memory:
            lbl_empty = ctk.CTkLabel(
                self.editor_scroll, text="No hay repuestos registrados en el catálogo.\nSincroniza tus imágenes primero en la pestaña 'Sincronización'.",
                font=ctk.CTkFont(size=13, slant="italic")
            )
            lbl_empty.grid(row=0, column=0, pady=40, sticky="ew")
            self.lbl_editor_status.configure(text="Catálogo vacío.")
            self.lbl_page_info.configure(text="Página 0 de 0")
            self.btn_prev_page.configure(state="disabled")
            self.btn_next_page.configure(state="disabled")
            return

        # Normalizar query para búsqueda flexible
        normalized_query = query.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")

        # Filtrar productos en memoria
        filtered = []
        only_new = self.var_only_new.get()
        for p in self.editor_products_in_memory:
            # Filtro de repuestos nuevos
            if only_new and p["id"] not in self.newly_added_product_ids:
                continue

            desc_norm = p["description"].lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            cat_norm = p["category"].lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            
            if not query or normalized_query in desc_norm or normalized_query in cat_norm:
                filtered.append(p)

        # Mostrar estado y calcular paginación
        total_found = len(filtered)
        
        if total_found == 0:
            lbl_no_res = ctk.CTkLabel(
                self.editor_scroll, 
                text="No se encontraron repuestos que coincidan con los filtros activos." if only_new else "No se encontraron repuestos que coincidan con la búsqueda.",
                font=ctk.CTkFont(size=13, slant="italic")
            )
            lbl_no_res.grid(row=0, column=0, pady=30, sticky="ew")
            self.lbl_editor_status.configure(text="Sin coincidencias.")
            self.lbl_page_info.configure(text="Página 0 de 0")
            self.btn_prev_page.configure(state="disabled")
            self.btn_next_page.configure(state="disabled")
            return

        # Calcular rango de página actual
        start_idx = self.editor_current_page * self.editor_page_size
        end_idx = min(start_idx + self.editor_page_size, total_found)
        
        page_products = filtered[start_idx:end_idx]
        total_pages = (total_found + self.editor_page_size - 1) // self.editor_page_size
        
        # Actualizar info e interactividad de botones de paginación
        self.lbl_page_info.configure(text=f"Página {self.editor_current_page + 1} de {total_pages}")
        self.btn_prev_page.configure(state="normal" if self.editor_current_page > 0 else "disabled")
        self.btn_next_page.configure(state="normal" if self.editor_current_page < total_pages - 1 else "disabled")

        status_prefix = "Nuevos: " if only_new else ""
        self.lbl_editor_status.configure(
            text=f"Mostrando {status_prefix}{start_idx + 1}-{end_idx} de {total_found} productos (Búsqueda: '{query}')" if query else f"Mostrando {status_prefix}{start_idx + 1}-{end_idx} de {total_found} productos."
        )

        # Renderizar los coincidentes de la página
        for idx, product in enumerate(page_products):
            # Frame contenedor para la fila
            item_frame = ctk.CTkFrame(self.editor_scroll, fg_color="#181820", corner_radius=10)
            item_frame.grid(row=idx, column=0, sticky="ew", padx=10, pady=6)
            item_frame.grid_columnconfigure(1, weight=1)
            item_frame.grid_columnconfigure(2, weight=0)
            item_frame.grid_rowconfigure(0, weight=1)

            # Columna 0: Cargar miniatura WebP local
            img_path = Path("web/assets") / f"{product['id']}.webp"
            loaded_img = None
            if img_path.exists():
                try:
                    pil_img = Image.open(img_path)
                    loaded_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(56, 70))
                except Exception:
                    pass

            if loaded_img:
                lbl_img = ctk.CTkLabel(item_frame, image=loaded_img, text="")
                lbl_img.image = loaded_img # Conservar referencia
                lbl_img.grid(row=0, column=0, padx=(12, 10), pady=8)
            else:
                lbl_img = ctk.CTkLabel(item_frame, text="Sin foto", width=56, height=70, fg_color="#0a0a0c", corner_radius=6, font=ctk.CTkFont(size=10))
                lbl_img.grid(row=0, column=0, padx=(12, 10), pady=8)

            # Columna 1: Datos y Casilla de Entrada
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=8)
            info_frame.grid_columnconfigure(0, weight=1)

            # Categoría resaltada en naranja
            lbl_cat = ctk.CTkLabel(info_frame, text=product["category"].upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color="#ff6a00", anchor="w")
            lbl_cat.grid(row=0, column=0, sticky="w", pady=(0, 2))

            # Entry para editar descripción
            entry_desc = ctk.CTkEntry(info_frame, placeholder_text="Descripción del repuesto...")
            entry_desc.insert(0, product["description"])
            entry_desc.grid(row=1, column=0, sticky="ew", pady=(2, 0))

            # Guardar referencia del entry
            self.editor_entries[product["id"]] = entry_desc

            # Columna 2: Botón Eliminar
            btn_delete = ctk.CTkButton(
                item_frame, text="Eliminar", width=80, fg_color="#d9534f", hover_color="#c9302c",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda p_id=product["id"], p_cat=product["category"]: self.delete_product_action(p_id, p_cat)
            )
            btn_delete.grid(row=0, column=2, padx=15, pady=8)

    def save_editor_changes(self):
        """Guarda de forma segura los cambios del editor de vuelta a products.js."""
        if not self.editor_products_in_memory:
            return

        # Deshabilitar botón temporalmente
        self.btn_editor_save.configure(state="disabled", text="Guardando...")
        
        # Asegurar que guardamos los cambios de la página actual en la memoria antes de persistir
        self.save_current_entries_to_memory()

        # Ejecutar guardado en segundo plano
        def run_save():
            try:
                # 1. Cargar el JSON de products.js original para conservar número de WhatsApp, logo, etc.
                catalog_data = generator.read_catalog_js()
                if not catalog_data:
                    # Si por alguna razón no existía, crear estructura básica
                    config = generator.load_config()
                    catalog_data = {
                        "whatsapp_number": config.get("whatsapp_number", "584242116375"),
                        "use_custom_logo": "",
                        "instagram_url": config.get("instagram_url", ""),
                        "facebook_url": config.get("facebook_url", ""),
                        "maps_url": config.get("maps_url", ""),
                        "reviews_url": config.get("reviews_url", ""),
                        "total_products": len(self.editor_products_in_memory),
                        "products": self.editor_products_in_memory
                    }
                else:
                    # Reemplazar la lista de productos y actualizar conteo
                    catalog_data["products"] = self.editor_products_in_memory
                    catalog_data["total_products"] = len(self.editor_products_in_memory)

                # 2. Escribir de vuelta en products.js
                write_success = generator.write_catalog_js(catalog_data)
                
                if write_success:
                    self.write_to_log("\n[Editor] Se guardaron los cambios del editor en products.js.\n")
                    msg = "Se han guardado con éxito las ediciones de los repuestos en el catálogo."
                    self.after(0, lambda: messagebox.showinfo("Éxito", msg))
                else:
                    self.after(0, lambda: messagebox.showerror("Error", "No se pudo escribir los cambios en products.js."))

                # Volver a cargar el editor para refrescar
                self.after(0, self.load_editor_data)

            except Exception as e:
                self.write_to_log(f"\n[Editor] Error al guardar cambios: {e}\n")
                self.after(0, lambda: messagebox.showerror("Error", f"Error al guardar cambios: {e}"))
            finally:
                self.after(0, lambda: self.btn_editor_save.configure(state="normal", text="Guardar Cambios del Editor"))

        threading.Thread(target=run_save, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
