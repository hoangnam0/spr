# -*- coding: utf-8 -*-
import sys
import os
import struct
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QFileDialog, QListWidget, QMessageBox,
                            QTabWidget, QScrollArea, QSplitter, QAction, QMenu, QToolBar,
                            QSpinBox, QGridLayout, QGroupBox, QStatusBar, QLineEdit,
                            QRadioButton, QButtonGroup, QCheckBox, QSlider, QColorDialog,
                            QDialog, QFormLayout)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import Qt, QSize, QTimer, QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import qRgba
# hoặc
from PyQt5.QtGui import *

class ASFHeader:
    """Structure for ASF file header"""
    def __init__(self):
        self.signature = "ASF"  # File signature
        self.version = 1.0      # ASF version
        self.frame_count = 0    # Number of frames
        self.width = 0          # Width
        self.height = 0         # Height
        self.direction_count = 0  # Number of animation directions


class SPRHeader:
    """Structure for SPR file header"""
    def __init__(self):
        self.signature = "SPR"  # File signature
        self.version = 1.0      # SPR version
        self.frame_count = 0    # Number of frames
        self.width = 0          # Width
        self.height = 0         # Height
        self.direction_count = 0  # Number of directions


class ASFFrame:
    """Information for a frame in ASF file"""
    def __init__(self):
        self.direction = 0      # Frame direction (0-7)
        self.image_data = None  # Image data
        self.delay = 100        # Display time (ms)
        self.x_offset = 0       # X offset
        self.y_offset = 0       # Y offset
        # Additional properties from screenshot
        self.shadow_enabled = False  # Enable shadow
        self.shadow_x_offset = 0     # Shadow X offset
        self.shadow_y_offset = 0     # Shadow Y offset
        self.shadow_transparency = 120   # Shadow transparency (0-255)
        self.shadow_color = QColor(0, 0, 0, 128)  # Shadow color


class FrameAdjustmentDialog(QDialog):
    """Dialog for advanced frame adjustments"""
    def __init__(self, parent=None, frame=None):
        super().__init__(parent)
        self.frame = frame
        self.setWindowTitle("Frame Details")
        self.setMinimumWidth(400)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout(self)
        
        # Transparency slider
        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setRange(0, 255)
        self.transparency_slider.setValue(self.frame.shadow_transparency if self.frame else 120)
        layout.addRow("Transparency:", self.transparency_slider)
        
        # Shadow color picker
        self.color_btn = QPushButton("Choose Shadow Color")
        self.color_btn.clicked.connect(self.choose_shadow_color)
        layout.addRow("Shadow Color:", self.color_btn)
        
        # Lock offset checkbox
        self.lock_offset = QCheckBox("Lock Offset")
        layout.addRow("", self.lock_offset)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.ok_btn)
        buttons_layout.addWidget(self.cancel_btn)
        layout.addRow("", buttons_layout)
    
    def choose_shadow_color(self):
        if self.frame:
            color = QColorDialog.getColor(self.frame.shadow_color, self, "Choose Shadow Color")
            if color.isValid():
                self.frame.shadow_color = color


class EnhancedPyAsfTool(QMainWindow):
    """Enhanced version of PyAsfTool with additional features"""
    def __init__(self):
        super().__init__()
        self.current_file = None    # Current file
        self.current_file_type = None  # File type (ASF or SPR)
        self.frames = []        # Frame list
        self.header = ASFHeader() # File header info
        self.current_frame = 0  # Current frame index
        self.is_playing = False # Animation playback state
        self.animation_timer = QTimer() # Timer for animation
        self.animation_timer.timeout.connect(self.next_frame)
        
        # Custom settings
        self.background_color = QColor(128, 128, 128)  # Default background color
        self.lock_offsets = False  # Lock offsets across frames
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("PyAsfTool - ASF/SPR File Tool")
        self.setMinimumSize(900, 700)
        
        # Create menus
        self.create_menus()
        
        # Create toolbar
        self.create_toolbar()
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Parameters
        params_group = QGroupBox("Parameters")
        params_layout = QGridLayout(params_group)
        
        # Width
        params_layout.addWidget(QLabel("Width:"), 0, 0)
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 1000)
        self.width_input.setValue(100)
        self.width_input.valueChanged.connect(self.update_frame_dimensions)
        params_layout.addWidget(self.width_input, 0, 1)
        
        # Height
        params_layout.addWidget(QLabel("Height:"), 0, 2)
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 1000)
        self.height_input.setValue(100)
        self.height_input.valueChanged.connect(self.update_frame_dimensions)
        params_layout.addWidget(self.height_input, 0, 3)
        
        # Direction
        params_layout.addWidget(QLabel("Direction:"), 1, 0)
        self.direction_input = QSpinBox()
        self.direction_input.setRange(1, 8)
        self.direction_input.setValue(1)
        params_layout.addWidget(self.direction_input, 1, 1)
        
        # Read Offset
        params_layout.addWidget(QLabel("Read Offset:"), 1, 2)
        self.read_offset_input = QSpinBox()
        self.read_offset_input.setRange(-999, 999)
        self.read_offset_input.setValue(0)
        params_layout.addWidget(self.read_offset_input, 1, 3)
        
        main_layout.addWidget(params_group)
        
        # Create splitter to divide the interface
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Frame list and controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        frame_list_label = QLabel("Frame list:")
        left_layout.addWidget(frame_list_label)
        
        self.frame_list = QListWidget()
        self.frame_list.itemSelectionChanged.connect(self.on_frame_selected)
        left_layout.addWidget(self.frame_list)
        
        # Frame control buttons
        frame_controls = QWidget()
        frame_controls_layout = QHBoxLayout(frame_controls)
        
        self.add_frame_btn = QPushButton("Add")
        self.add_frame_btn.clicked.connect(self.add_frame)
        frame_controls_layout.addWidget(self.add_frame_btn)
        
        self.remove_frame_btn = QPushButton("Remove")
        self.remove_frame_btn.clicked.connect(self.remove_frame)
        frame_controls_layout.addWidget(self.remove_frame_btn)
        
        self.move_up_btn = QPushButton("Up")
        self.move_up_btn.clicked.connect(self.move_frame_up)
        frame_controls_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("Down")
        self.move_down_btn.clicked.connect(self.move_frame_down)
        frame_controls_layout.addWidget(self.move_down_btn)
        
        left_layout.addWidget(frame_controls)
        
        # Right panel - Display and edit frame
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Tabs for display and edit
        tabs = QTabWidget()
        right_layout.addWidget(tabs)
        
        # Display tab
        display_tab = QWidget()
        display_layout = QVBoxLayout(display_tab)
        
        # Image display area
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_scroll.setWidget(self.image_label)
        display_layout.addWidget(self.image_scroll)
        
        # Animation controls
        animation_controls = QWidget()
        animation_layout = QHBoxLayout(animation_controls)
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_play)
        animation_layout.addWidget(self.play_btn)
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.prev_frame)
        animation_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.next_frame)
        animation_layout.addWidget(self.next_btn)
        
        animation_layout.addStretch()
        
        display_layout.addWidget(animation_controls)
        
        # Add extra frame adjustments
        self.create_frame_adjustments(display_tab, display_layout)
        
        # Edit tab
        edit_tab = QWidget()
        edit_layout = QGridLayout(edit_tab)
        
        # Frame information
        frame_info_group = QGroupBox("Frame Information")
        frame_info_layout = QGridLayout(frame_info_group)
        
        frame_info_layout.addWidget(QLabel("Direction:"), 0, 0)
        self.direction_spin = QSpinBox()
        self.direction_spin.setRange(0, 7)
        self.direction_spin.valueChanged.connect(self.update_frame_direction)
        frame_info_layout.addWidget(self.direction_spin, 0, 1)
        
        frame_info_layout.addWidget(QLabel("Delay (ms):"), 1, 0)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 1000)
        self.delay_spin.valueChanged.connect(self.update_frame_delay)
        frame_info_layout.addWidget(self.delay_spin, 1, 1)
        
        frame_info_layout.addWidget(QLabel("X Offset:"), 2, 0)
        self.x_offset_spin = QSpinBox()
        self.x_offset_spin.setRange(-999, 999)
        self.x_offset_spin.valueChanged.connect(self.update_frame_x_offset)
        frame_info_layout.addWidget(self.x_offset_spin, 2, 1)
        
        frame_info_layout.addWidget(QLabel("Y Offset:"), 3, 0)
        self.y_offset_spin = QSpinBox()
        self.y_offset_spin.setRange(-999, 999)
        self.y_offset_spin.valueChanged.connect(self.update_frame_y_offset)
        frame_info_layout.addWidget(self.y_offset_spin, 3, 1)
        
        edit_layout.addWidget(frame_info_group, 0, 0)
        
        # Shadow settings group
        shadow_group = QGroupBox("Shadow")
        shadow_layout = QGridLayout(shadow_group)
        
        # Shadow options
        self.no_shadow_radio = QRadioButton("No Shadow")
        self.layer1_shadow_radio = QRadioButton("Layer 1")
        self.layer2_shadow_radio = QRadioButton("Layer 2")
        
        shadow_radio_group = QButtonGroup(self)
        shadow_radio_group.addButton(self.no_shadow_radio, 0)
        shadow_radio_group.addButton(self.layer1_shadow_radio, 1)
        shadow_radio_group.addButton(self.layer2_shadow_radio, 2)
        shadow_radio_group.buttonClicked.connect(self.update_shadow_settings)
        
        shadow_layout.addWidget(self.no_shadow_radio, 0, 0)
        shadow_layout.addWidget(self.layer1_shadow_radio, 0, 1)
        shadow_layout.addWidget(self.layer2_shadow_radio, 0, 2)
        
        # Shadow frame options
        self.edit_current_shadow = QCheckBox("Edit current frame and lock")
        self.edit_all_shadows = QCheckBox("Lock adjacent frames")
        
        shadow_layout.addWidget(self.edit_current_shadow, 1, 0, 1, 2)
        shadow_layout.addWidget(self.edit_all_shadows, 1, 2, 1, 1)
        
        # Shadow X/Y offset
        shadow_layout.addWidget(QLabel("Horizontal RAY Offset:"), 2, 0)
        self.shadow_x_offset = QSpinBox()
        self.shadow_x_offset.setRange(-999, 999)
        self.shadow_x_offset.valueChanged.connect(self.update_shadow_x_offset)
        shadow_layout.addWidget(self.shadow_x_offset, 2, 1)
        
        shadow_layout.addWidget(QLabel("Vertical RAY Offset:"), 2, 2)
        self.shadow_doc_offset = QSpinBox()
        self.shadow_doc_offset.setRange(-999, 999)
        self.shadow_doc_offset.valueChanged.connect(self.update_shadow_doc_offset)
        shadow_layout.addWidget(self.shadow_doc_offset, 2, 3)
        
        shadow_layout.addWidget(QLabel("Horizontal Shadow Offset:"), 3, 0)
        self.shadow_x_shadow = QSpinBox()
        self.shadow_x_shadow.setRange(-999, 999)
        self.shadow_x_shadow.valueChanged.connect(self.update_shadow_x_shadow)
        shadow_layout.addWidget(self.shadow_x_shadow, 3, 1)
        
        shadow_layout.addWidget(QLabel("Vertical Shadow Offset:"), 3, 2)
        self.shadow_doc_shadow = QSpinBox()
        self.shadow_doc_shadow.setRange(-999, 999)
        self.shadow_doc_shadow.valueChanged.connect(self.update_shadow_doc_shadow)
        shadow_layout.addWidget(self.shadow_doc_shadow, 3, 3)
        
        shadow_layout.addWidget(QLabel("Global Transparency:"), 4, 0)
        self.transparency_slider = QSpinBox()
        self.transparency_slider.setRange(0, 255)
        self.transparency_slider.setValue(120)
        self.transparency_slider.valueChanged.connect(self.update_shadow_transparency)
        shadow_layout.addWidget(self.transparency_slider, 4, 1)
        
        edit_layout.addWidget(shadow_group, 1, 0)
        
        # Additional features group
        utils_group = QGroupBox("Utilities")
        utils_layout = QGridLayout(utils_group)
        
        # Background color
        utils_layout.addWidget(QLabel("Background Color:"), 0, 0)
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setStyleSheet(f"background-color: {self.background_color.name()}")
        self.bg_color_btn.setFixedWidth(100)
        self.bg_color_btn.clicked.connect(self.choose_background_color)
        utils_layout.addWidget(self.bg_color_btn, 0, 1)
        
        # Pause between frames
        utils_layout.addWidget(QLabel("Transparency Threshold:"), 1, 0)
        self.transparency_threshold = QSpinBox()
        self.transparency_threshold.setRange(0, 255)
        self.transparency_threshold.setValue(0)
        utils_layout.addWidget(self.transparency_threshold, 1, 1)
        
        # File name
        utils_layout.addWidget(QLabel("Filename:"), 2, 0)
        self.filename_input = QLineEdit()
        utils_layout.addWidget(self.filename_input, 2, 1)
        
        # Export buttons
        export_buttons = QWidget()
        export_layout = QHBoxLayout(export_buttons)
        
        self.export_tga_btn = QPushButton("Export TGA")
        self.export_tga_btn.clicked.connect(self.export_tga)
        export_layout.addWidget(self.export_tga_btn)
        
        self.convert_spr_btn = QPushButton("Convert to SPR")
        self.convert_spr_btn.clicked.connect(self.convert_to_spr)
        export_layout.addWidget(self.convert_spr_btn)
        
        utils_layout.addWidget(export_buttons, 3, 0, 1, 2)
        
        edit_layout.addWidget(utils_group, 2, 0)
        
        # Add tabs to tab widget
        tabs.addTab(display_tab, "Display")
        tabs.addTab(edit_tab, "Edit")
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 700])
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Update UI state
        self.update_ui_state()

    def create_frame_adjustments(self, parent_widget, parent_layout):
        """Create frame adjustment controls"""
        frame_adjust_group = QGroupBox("Frame Spacing")
        frame_adjust_layout = QHBoxLayout(frame_adjust_group)
        
        # Frame spacing slider
        self.frame_spacing_slider = QSlider(Qt.Horizontal)
        self.frame_spacing_slider.setRange(1, 200)
        self.frame_spacing_slider.setValue(100)
        self.frame_spacing_slider.valueChanged.connect(self.update_frame_spacing)
        frame_adjust_layout.addWidget(self.frame_spacing_slider)
        
        # Frame spacing value
        self.frame_spacing_value = QLabel("100")
        frame_adjust_layout.addWidget(self.frame_spacing_value)
        
        # Adjust button
        self.adjust_frame_btn = QPushButton("Adjust Coordinates")
        self.adjust_frame_btn.clicked.connect(self.adjust_frame_coordinates)
        frame_adjust_layout.addWidget(self.adjust_frame_btn)
        
        parent_layout.addWidget(frame_adjust_group)
        
        # Offset controls group
        offset_group = QGroupBox("Image Offset")
        offset_layout = QGridLayout(offset_group)
        
        # X Offset
        offset_layout.addWidget(QLabel("Horizontal Offset:"), 0, 0)
        self.frame_x_offset = QSpinBox()
        self.frame_x_offset.setRange(-999, 999)
        self.frame_x_offset.valueChanged.connect(self.update_display_x_offset)
        offset_layout.addWidget(self.frame_x_offset, 0, 1)
        
        # Y Offset
        offset_layout.addWidget(QLabel("Vertical Offset:"), 0, 2)
        self.frame_y_offset = QSpinBox()
        self.frame_y_offset.setRange(-999, 999)
        self.frame_y_offset.valueChanged.connect(self.update_display_y_offset)
        offset_layout.addWidget(self.frame_y_offset, 0, 3)
        
        # Lock offset checkbox
        self.lock_offset_checkbox = QCheckBox("Lock Offset")
        self.lock_offset_checkbox.stateChanged.connect(self.toggle_lock_offsets)
        offset_layout.addWidget(self.lock_offset_checkbox, 0, 4)
        
        # Advanced offset button
        self.advanced_offset_btn = QPushButton("Continue Lock")
        self.advanced_offset_btn.clicked.connect(self.show_advanced_offset_dialog)
        offset_layout.addWidget(self.advanced_offset_btn, 0, 5)
        
        parent_layout.addWidget(offset_group)
    
    def create_menus(self):
        """Create main menu"""
        # File menu
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        
        # Open ASF file
        open_asf_action = QAction("Open ASF", self)
        open_asf_action.triggered.connect(self.open_asf)
        file_menu.addAction(open_asf_action)
        
        # Open SPR file
        open_spr_action = QAction("Open SPR", self)
        open_spr_action.triggered.connect(self.open_spr)
        file_menu.addAction(open_spr_action)
        
        file_menu.addSeparator()
        
        # Save file
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        # Save as
        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Convert ASF to SPR
        convert_asf_to_spr_action = QAction("Convert ASF to SPR", self)
        convert_asf_to_spr_action.triggered.connect(self.convert_to_spr)
        file_menu.addAction(convert_asf_to_spr_action)
        
        # Convert SPR to ASF
        convert_spr_to_asf_action = QAction("Convert SPR to ASF", self)
        convert_spr_to_asf_action.triggered.connect(self.convert_to_asf)
        file_menu.addAction(convert_spr_to_asf_action)
        
        file_menu.addSeparator()
        
        # New file
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Export menu
        export_menu = menu_bar.addMenu("Export")
        
        # Export current frame
        self.export_current_frame_action = QAction("Export Current Frame", self)  # Define as class member
        self.export_current_frame_action.triggered.connect(self.export_current_frame)
        export_menu.addAction(self.export_current_frame_action)
        
        # Export all frames
        self.export_all_frames_action = QAction("Export All Frames", self)  # Define as class member
        self.export_all_frames_action.triggered.connect(self.export_all_frames)
        export_menu.addAction(self.export_all_frames_action)
        
        # Export sprite sheet
        self.export_sprite_sheet_action = QAction("Export Sprite Sheet", self)  # Define as class member
        self.export_sprite_sheet_action.triggered.connect(self.export_sprite_sheet)
        export_menu.addAction(self.export_sprite_sheet_action)
        
        # Export TGA
        self.export_tga_action = QAction("Export TGA", self)  # Define as class member
        self.export_tga_action.triggered.connect(self.export_tga)
        export_menu.addAction(self.export_tga_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        # About
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Open ASF file
        open_asf_action = QAction("Open ASF", self)
        open_asf_action.triggered.connect(self.open_asf)
        toolbar.addAction(open_asf_action)
        
        # Open SPR file
        open_spr_action = QAction("Open SPR", self)
        open_spr_action.triggered.connect(self.open_spr)
        toolbar.addAction(open_spr_action)
        
        # Save file
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Add frame
        add_frame_action = QAction("Add Frame", self)
        add_frame_action.triggered.connect(self.add_frame)
        toolbar.addAction(add_frame_action)
        
        # Remove frame
        remove_frame_action = QAction("Remove Frame", self)
        remove_frame_action.triggered.connect(self.remove_frame)
        toolbar.addAction(remove_frame_action)
        
        # Add Open TGA button
        open_tga_action = QAction("Open TGA", self)
        open_tga_action.triggered.connect(self.open_tga)
        toolbar.addAction(open_tga_action)
    
    def update_frame_spacing(self, value):
        """Update frame spacing"""
        self.frame_spacing_value.setText(str(value))
        # In a real implementation, this might affect frame display or animation timing
    
    def adjust_frame_coordinates(self):
        """Open dialog to adjust frame coordinates"""
        if not self.frames or self.current_frame < 0 or self.current_frame >= len(self.frames):
            return
            
        # Show dialog with frame adjustment options
        QMessageBox.information(self, "Frame Adjustment", "Adjusting frame coordinates")
        
    def update_display_x_offset(self, value):
        """Update X offset for display"""
        if not self.frames or self.current_frame < 0:
            return
            
        self.frames[self.current_frame].x_offset = value
        
        # Apply offset to all frames if locked
        if self.lock_offsets:
            for i, frame in enumerate(self.frames):
                if i != self.current_frame:
                    frame.x_offset = value
        
        # Update display
        self.display_frame(self.current_frame)
        
    def update_display_y_offset(self, value):
        """Update Y offset for display"""
        if not self.frames or self.current_frame < 0:
            return
            
        self.frames[self.current_frame].y_offset = value
        
        # Apply offset to all frames if locked
        if self.lock_offsets:
            for i, frame in enumerate(self.frames):
                if i != self.current_frame:
                    frame.y_offset = value
        
        # Update display
        self.display_frame(self.current_frame)
        
    def toggle_lock_offsets(self, state):
        """Toggle lock offsets across frames"""
        self.lock_offsets = (state == Qt.Checked)
        
    def show_advanced_offset_dialog(self):
        """Show advanced offset options"""
        if not self.frames or self.current_frame < 0:
            return
            
        dialog = FrameAdjustmentDialog(self, self.frames[self.current_frame])
        if dialog.exec_():
            # Apply changes from dialog
            self.display_frame(self.current_frame)
            
    def update_frame_dimensions(self):
        """Update frame dimensions"""
        new_width = self.width_input.value()
        new_height = self.height_input.value()
        
        if not self.frames:
            # Just update header if no frames
            self.header.width = new_width
            self.header.height = new_height
            return
        
        # Ask user for confirmation if there are existing frames
        reply = QMessageBox.question(self, "Resize Frames", 
                                    "Do you want to resize all existing frames?",
                                    QMessageBox.Yes | QMessageBox.No)
                                    
        if reply == QMessageBox.Yes:
            # Update header
            self.header.width = new_width
            self.header.height = new_height
            
            # Resize all frames
            for frame in self.frames:
                if frame.image_data:
                    # Resize image data to new dimensions
                    old_image = QImage.fromData(frame.image_data)
                    new_image = old_image.scaled(new_width, new_height, Qt.KeepAspectRatio)
                    
                    # Convert back to byte array
                    ba = QByteArray()
                    buffer = QBuffer(ba)
                    buffer.open(QIODevice.WriteOnly)
                    new_image.save(buffer, "PNG")
                    frame.image_data = ba.data()
            # Update display
            self.display_frame(self.current_frame)
    
    def update_shadow_settings(self, button):
        """Update shadow settings based on radio button selection"""
        if not self.frames or self.current_frame < 0:
            return
            
        frame = self.frames[self.current_frame]
        
        # Set shadow enabled based on radio button
        frame.shadow_enabled = (button.text() != "No Shadow")
        
        # Update display
        self.display_frame(self.current_frame)
    
    def update_shadow_x_offset(self, value):
        """Update shadow X offset"""
        if not self.frames or self.current_frame < 0:
            return
            
        frame = self.frames[self.current_frame]
        frame.shadow_x_offset = value
        
        # Update display
        self.display_frame(self.current_frame)
    
    def update_shadow_doc_offset(self, value):
        """Update shadow doc offset"""
        # This appears to be a specialized offset setting
        # Implementation would depend on specific file format requirements
        pass
    
    def update_shadow_x_shadow(self, value):
        """Update shadow X shadow value"""
        # This appears to be a specialized shadow setting
        # Implementation would depend on specific file format requirements
        pass
    
    def update_shadow_doc_shadow(self, value):
        """Update shadow doc shadow value"""
        # This appears to be a specialized shadow setting
        # Implementation would depend on specific file format requirements
        pass
    
    def update_shadow_transparency(self, value):
        """Update shadow transparency"""
        if not self.frames or self.current_frame < 0:
            return
            
        frame = self.frames[self.current_frame]
        frame.shadow_transparency = value
        
        # Update shadow color with new transparency
        color = frame.shadow_color
        frame.shadow_color = QColor(color.red(), color.green(), color.blue(), value)
        
        # Update display
        self.display_frame(self.current_frame)
    
    def choose_background_color(self):
        """Choose background color for frame display"""
        color = QColorDialog.getColor(self.background_color, self, "Choose Background Color")
        if color.isValid():
            self.background_color = color
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()}")
            
            # Update display
            self.display_frame(self.current_frame)
    
    def update_frame_direction(self, value):
        """Update direction for current frame"""
        if not self.frames or self.current_frame < 0:
            return
            
        self.frames[self.current_frame].direction = value
    
    def update_frame_delay(self, value):
        """Update delay for current frame"""
        if not self.frames or self.current_frame < 0:
            return
            
        self.frames[self.current_frame].delay = value
    
    def update_frame_x_offset(self, value):
        """Update X offset for current frame"""
        if not self.frames or self.current_frame < 0:
            return
            
        self.frames[self.current_frame].x_offset = value
        
        # Update display offset spinner to match
        self.frame_x_offset.blockSignals(True)
        self.frame_x_offset.setValue(value)  
        self.frame_x_offset.blockSignals(False)
        
        # Update display
        self.display_frame(self.current_frame)
    
    def update_frame_y_offset(self, value):
        """Update Y offset for current frame"""
        if not self.frames or self.current_frame < 0:
            return
            
        self.frames[self.current_frame].y_offset = value
        
        # Update display offset spinner to match
        self.frame_y_offset.blockSignals(True)
        self.frame_y_offset.setValue(value)
        self.frame_y_offset.blockSignals(False)
        
        # Update display
        self.display_frame(self.current_frame)
    
    def new_file(self):
        """Create new file"""
        # Check if there are unsaved changes
        if self.frames and self.check_unsaved_changes():
            return
            
        # Reset to default state
        self.current_file = None
        self.current_file_type = None
        self.frames = []
        self.header = ASFHeader()
        self.current_frame = -1
        
        # Update UI with default values
        self.width_input.setValue(100)
        self.height_input.setValue(100)
        self.direction_input.setValue(1)
        self.frame_list.clear()
        self.image_label.clear()
        self.filename_input.clear()
        
        # Update UI state
        self.update_ui_state()
        self.status_bar.showMessage("New file created")
    
    def check_unsaved_changes(self):
        """Check if there are unsaved changes and prompt user"""
        reply = QMessageBox.question(self, "Unsaved Changes",
                                    "There are unsaved changes. Do you want to save before continuing?",
                                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                                    
        if reply == QMessageBox.Save:
            # Save changes
            self.save_file()
            return False
        elif reply == QMessageBox.Cancel:
            # Cancel operation
            return True
        else:
            # Discard changes
            return False
    
    def open_asf(self):
        """Open ASF file"""
        # Check if there are unsaved changes
        if self.frames and self.check_unsaved_changes():
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Open ASF File", "", "ASF Files (*.asf);;All Files (*)")
        if not file_path:
            return
            
        try:
            self.load_asf_file(file_path)
            self.current_file = file_path
            self.current_file_type = "ASF"
            self.status_bar.showMessage(f"Opened ASF file: {file_path}")
            self.filename_input.setText(os.path.basename(file_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open ASF file: {str(e)}")
    
    def open_spr(self):
        """Open SPR file"""
        # Check if there are unsaved changes
        if self.frames and self.check_unsaved_changes():
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Open SPR File", "", "SPR Files (*.spr);;All Files (*)")
        if not file_path:
            return
            
        try:
            self.load_spr_file(file_path)
            self.current_file = file_path
            self.current_file_type = "SPR"
            self.status_bar.showMessage(f"Opened SPR file: {file_path}")
            self.filename_input.setText(os.path.basename(file_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open SPR file: {str(e)}")
    def open_tga(self):
        """Open TGA file (support both standard TGA and raw BGRA)"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open TGA", "", "TGA Files (*.tga);;All Files (*)")
        if not file_path:
            return

        try:
            with open(file_path, 'rb') as f:
                data = f.read()

            print(f"File size: {len(data)} bytes")
            
            if len(data) < 18:
                raise Exception("File too small - not a valid TGA file")

            # Đọc TGA header
            header = data[:18]
            id_length = header[0]
            color_map_type = header[1]
            image_type = header[2]
            width = int.from_bytes(header[12:14], 'little')
            height = int.from_bytes(header[14:16], 'little')
            bits_per_pixel = header[16]
            image_descriptor = header[17]
            
            print(f"TGA Info: {width}x{height}, {bits_per_pixel}bpp, type={image_type}")

            image = None
            
            # Thử Qt loader trước
            qt_image = QImage()
            if qt_image.loadFromData(data, 'TGA') and not qt_image.isNull():
                print("✓ Loaded with Qt TGA loader")
                image = qt_image
                if image.format() != QImage.Format_RGB888:
                    image = image.convertToFormat(QImage.Format_RGB888)
            else:
                print("Qt loader failed, trying manual decode...")
                # Tính offset để bỏ qua header và ID field
                offset = 18 + id_length
                
                # Bỏ qua color map nếu có
                if color_map_type == 1:
                    color_map_length = int.from_bytes(header[5:7], 'little')
                    color_map_entry_size = header[7]
                    color_map_size = color_map_length * (color_map_entry_size // 8)
                    offset += color_map_size
                
                image_data = data[offset:]
                print(f"Image data size: {len(image_data)} bytes")
                
                # Decode dựa trên loại TGA
                if image_type == 2:  # Uncompressed RGB
                    image = self.decode_tga(image_data, width, height, bits_per_pixel, image_descriptor)
                elif image_type == 10:  # RLE compressed
                    image = self.decode_rle_tga(image_data, width, height, bits_per_pixel, image_descriptor)
                else:
                    # Thử decode như raw BGRA (fallback cho các file đặc biệt)
                    image = self.decode_tga(image_data, width, height, bits_per_pixel, image_descriptor)

            if image and not image.isNull():
                print(f"✓ Successfully decoded: {image.width()}x{image.height()}")
                
                ba = QByteArray()
                buffer = QBuffer(ba)
                buffer.open(QIODevice.WriteOnly)
                
                # Đảm bảo format RGB888 trước khi save
                if image.format() != QImage.Format_RGB888:
                    image = image.convertToFormat(QImage.Format_RGB888)
                    
                if image.save(buffer, 'PNG'):
                    frame = ASFFrame()
                    frame.image_data = ba.data()
                    self.frames.append(frame)
                    self.frame_list.addItem(f"Frame {len(self.frames)}")
                    self.current_frame = len(self.frames) - 1
                    self.frame_list.setCurrentRow(self.current_frame)
                    self.display_frame(self.current_frame)
                    self.status_bar.showMessage(f"Opened TGA file: {file_path}")
                    print("✓ TGA file loaded successfully")
                else:
                    raise Exception("Failed to save as PNG")
            else:
                raise Exception("Failed to decode TGA image")
                    
        except Exception as e:
            print(f"TGA Error: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to open TGA file: {str(e)}")

    def decode_tga(self, image_data, width, height, bits_per_pixel=32, image_descriptor=0):
        """Decode TGA image data"""
        try:
            bytes_per_pixel = bits_per_pixel // 8
            expected_size = width * height * bytes_per_pixel
            
            print(f"Decode TGA: {width}x{height}, {bits_per_pixel}bpp")
            print(f"Expected data size: {expected_size}, actual: {len(image_data)}")
            
            if len(image_data) < expected_size:
                print(f"Warning: Data size mismatch, using available data")
            
            if bits_per_pixel == 32:
                # 32-bit BGRA
                qimage = QImage(width, height, QImage.Format_ARGB32)
                
                for y in range(height):
                    for x in range(width):
                        pixel_idx = (y * width + x) * 4
                        if pixel_idx + 3 < len(image_data):
                            b = image_data[pixel_idx]
                            g = image_data[pixel_idx + 1]
                            r = image_data[pixel_idx + 2]
                            a = image_data[pixel_idx + 3]
                            
                            # Kiểm tra origin (TGA có thể có origin ở dưới)
                            actual_y = height - 1 - y if (image_descriptor & 0x20) == 0 else y
                            qimage.setPixel(x, actual_y, qRgba(r, g, b, a))
                            
            elif bits_per_pixel == 24:
                # 24-bit BGR
                qimage = QImage(width, height, QImage.Format_RGB888)
                
                for y in range(height):
                    for x in range(width):
                        pixel_idx = (y * width + x) * 3
                        if pixel_idx + 2 < len(image_data):
                            b = image_data[pixel_idx]
                            g = image_data[pixel_idx + 1]
                            r = image_data[pixel_idx + 2]
                            
                            actual_y = height - 1 - y if (image_descriptor & 0x20) == 0 else y
                            qimage.setPixel(x, actual_y, qRgb(r, g, b))
            else:
                print(f"Unsupported bit depth: {bits_per_pixel}")
                return None
                
            return qimage
            
        except Exception as e:
            print(f"Decode error: {e}")
            return None

    def decode_rle_tga(self, image_data, width, height, bits_per_pixel, image_descriptor):
        """Decode RLE compressed TGA"""
        try:
            bytes_per_pixel = bits_per_pixel // 8
            pixels = []
            i = 0
            
            print(f"Decoding RLE TGA: {width}x{height}, {bits_per_pixel}bpp")
            
            while i < len(image_data) and len(pixels) < width * height * bytes_per_pixel:
                if i >= len(image_data):
                    break
                    
                packet_header = image_data[i]
                i += 1
                
                if packet_header & 0x80:  # RLE packet
                    count = (packet_header & 0x7F) + 1
                    if i + bytes_per_pixel <= len(image_data):
                        pixel_data = image_data[i:i + bytes_per_pixel]
                        i += bytes_per_pixel
                        
                        # Repeat pixel
                        for _ in range(count):
                            pixels.extend(pixel_data)
                            if len(pixels) >= width * height * bytes_per_pixel:
                                break
                else:  # Raw packet
                    count = (packet_header & 0x7F) + 1
                    for _ in range(count):
                        if i + bytes_per_pixel <= len(image_data):
                            pixels.extend(image_data[i:i + bytes_per_pixel])
                            i += bytes_per_pixel
                        if len(pixels) >= width * height * bytes_per_pixel:
                            break
            
            print(f"RLE decoded {len(pixels)} bytes")
            
            # Tạo QImage từ decoded pixels
            if bits_per_pixel == 32:
                qimage = QImage(width, height, QImage.Format_ARGB32)
                
                for y in range(height):
                    for x in range(width):
                        pixel_idx = (y * width + x) * 4
                        if pixel_idx + 3 < len(pixels):
                            b = pixels[pixel_idx]
                            g = pixels[pixel_idx + 1]
                            r = pixels[pixel_idx + 2]
                            a = pixels[pixel_idx + 3]
                            
                            actual_y = height - 1 - y if (image_descriptor & 0x20) == 0 else y
                            qimage.setPixel(x, actual_y, qRgba(r, g, b, a))
                            
            elif bits_per_pixel == 24:
                qimage = QImage(width, height, QImage.Format_RGB888)
                
                for y in range(height):
                    for x in range(width):
                        pixel_idx = (y * width + x) * 3
                        if pixel_idx + 2 < len(pixels):
                            b = pixels[pixel_idx]
                            g = pixels[pixel_idx + 1]
                            r = pixels[pixel_idx + 2]
                            
                            actual_y = height - 1 - y if (image_descriptor & 0x20) == 0 else y
                            qimage.setPixel(x, actual_y, qRgb(r, g, b))
            else:
                return None
                
            return qimage
            
        except Exception as e:
            print(f"RLE decode error: {e}")
            return None
    
    def load_spr_file(self, file_path):
        """Load SPR file data including TGA images"""
        try:
            with open(file_path, "rb") as f:
                # Read and validate header
                signature = f.read(3).decode('ascii')
                if signature != "SPR":
                    raise ValueError("Invalid SPR file signature")

                # Read header data    
                version = struct.unpack("<f", f.read(4))[0]
                frame_count = struct.unpack("<I", f.read(4))[0]
                width = struct.unpack("<I", f.read(4))[0]
                height = struct.unpack("<I", f.read(4))[0]
                direction_count = struct.unpack("<I", f.read(4))[0]

                # Create header
                self.header = SPRHeader()
                self.header.version = version
                self.header.frame_count = frame_count
                self.header.width = width
                self.header.height = height
                self.header.direction_count = direction_count

                # Update UI
                self.width_input.setValue(width)
                self.height_input.setValue(height)
                self.direction_input.setValue(direction_count)

                # Clear existing frames
                self.frames = []
                self.frame_list.clear()

                # Read frame data
                for i in range(frame_count):
                    frame = ASFFrame()
                    frame.direction = struct.unpack("<I", f.read(4))[0]
                    data_size = struct.unpack("<I", f.read(4))[0]
                    raw_data = f.read(data_size)

                    # Always use manual decode for SPR (do not try QImage.loadFromData with TGA)
                    image = self.decode_tga(raw_data, width, height)
                    if image:
                        ba = QByteArray()
                        buffer = QBuffer(ba)
                        buffer.open(QIODevice.WriteOnly)
                        image.save(buffer, 'PNG')
                        frame.image_data = ba.data()
                        self.frames.append(frame)
                        self.frame_list.addItem(f"Frame {len(self.frames)}")
                    else:
                        print(f"Failed to decode frame {i}")

            # Select first frame if available
            if self.frames:
                self.current_frame = 0
                self.frame_list.setCurrentRow(0)
                self.display_frame(0)

            self.update_ui_state()

        except Exception as e:
            raise Exception(f"Failed to load SPR file: {str(e)}")

    def save_file(self):
        """Save current file"""
        if not self.current_file:
            self.save_file_as()
            return
            
        try:
            if self.current_file_type == "ASF":
                self.save_asf_file(self.current_file)
            elif self.current_file_type == "SPR":
                self.save_spr_file(self.current_file)
            else:
                self.save_file_as()
                return
                
            self.status_bar.showMessage(f"Saved file: {self.current_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
    
    def save_file_as(self):
        """Save file with new name"""
        if self.current_file_type == "ASF" or not self.current_file_type:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save ASF File", "", "ASF Files (*.asf);;All Files (*)")
            if file_path:
                try:
                    self.save_asf_file(file_path)
                    self.current_file = file_path
                    self.current_file_type = "ASF"
                    self.status_bar.showMessage(f"Saved ASF file: {file_path}")
                    self.filename_input.setText(os.path.basename(file_path))
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save ASF file: {str(e)}")
        elif self.current_file_type == "SPR":
            file_path, _ = QFileDialog.getSaveFileName(self, "Save SPR File", "", "SPR Files (*.spr);;All Files (*)")
            if file_path:
                try:
                    self.save_spr_file(file_path)
                    self.current_file = file_path
                    self.current_file_type = "SPR"
                    self.status_bar.showMessage(f"Saved SPR file: {file_path}")
                    self.filename_input.setText(os.path.basename(file_path))
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save SPR file: {str(e)}")
    
    def save_asf_file(self, file_path):
        """Save data to ASF file"""
        if not self.frames:
            QMessageBox.warning(self, "Warning", "No frames to save")
            return
            
        with open(file_path, "wb") as f:
            # Write signature
            f.write("ASF".encode('ascii'))
            
            # Write header
            f.write(struct.pack("<f", self.header.version))
            f.write(struct.pack("<I", len(self.frames)))
            f.write(struct.pack("<I", self.header.width))
            f.write(struct.pack("<I", self.header.height))
            f.write(struct.pack("<I", self.direction_input.value()))
            
            # Write frame data
            for frame in self.frames:
                # Write frame header
                f.write(struct.pack("<I", frame.direction))
                f.write(struct.pack("<i", frame.x_offset))
                f.write(struct.pack("<i", frame.y_offset))
                f.write(struct.pack("<I", frame.delay))
                
                # Write frame data size and data
                if frame.image_data:
                    f.write(struct.pack("<I", len(frame.image_data)))
                    f.write(frame.image_data)
                else:
                    f.write(struct.pack("<I", 0))
    
    def save_spr_file(self, file_path):
        """Save data to SPR file"""
        if not self.frames:
            QMessageBox.warning(self, "Warning", "No frames to save")
            return
            
        with open(file_path, "wb") as f:
            # Write signature
            f.write("SPR".encode('ascii'))
            
            # Write header
            f.write(struct.pack("<f", 1.0))  # Version
            f.write(struct.pack("<I", len(self.frames)))
            f.write(struct.pack("<I", self.header.width))
            f.write(struct.pack("<I", self.header.height))
            f.write(struct.pack("<I", self.direction_input.value()))
            
            # Write frame data
            for frame in self.frames:
                # Write direction
                f.write(struct.pack("<I", frame.direction))
                
                # Write frame data size and data
                if frame.image_data:
                    f.write(struct.pack("<I", len(frame.image_data)))
                    f.write(frame.image_data)
                else:
                    f.write(struct.pack("<I", 0))
    
    def convert_to_spr(self):
        """Convert current ASF file to SPR format"""
        if not self.frames:
            QMessageBox.warning(self, "Warning", "No frames to convert")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save SPR File", "", "SPR Files (*.spr);;All Files (*)")
        if file_path:
            try:
                self.save_spr_file(file_path)
                QMessageBox.information(self, "Success", f"Converted to SPR and saved as: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to convert to SPR: {str(e)}")
    
    def convert_to_asf(self):
        """Convert current SPR file to ASF format"""
        if not self.frames:
            QMessageBox.warning(self, "Warning", "No frames to convert")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save ASF File", "", "ASF Files (*.asf);;All Files (*)")
        if file_path:
            try:
                self.save_asf_file(file_path)
                QMessageBox.information(self, "Success", f"Converted to ASF and saved as: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to convert to ASF: {str(e)}")
    
    def add_frame(self):
        """Add new frame"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.bmp *.tga);;All Files (*)")
        if not file_path:
            return
            
        try:
            # Load image
            image = QImage(file_path)
            
            # Resize image to match header dimensions if needed
            if self.header.width > 0 and self.header.height > 0:
                if image.width() != self.header.width or image.height() != self.header.height:
                    image = image.scaled(self.header.width, self.header.height, Qt.KeepAspectRatio)
            else:
                # Update header dimensions based on first image
                self.header.width = image.width()
                self.header.height = image.height()
                self.width_input.setValue(image.width())
                self.height_input.setValue(image.height())
            
            # Convert to byte array
            ba = QByteArray()
            buffer = QBuffer(ba)
            buffer.open(QIODevice.WriteOnly)
            image.save(buffer, "PNG")
            
            # Create new frame
            frame = ASFFrame()
            frame.image_data = ba.data()
            frame.direction = 0  # Default direction
            frame.delay = 100    # Default delay
            
            # Add to frame list
            self.frames.append(frame)
            self.frame_list.addItem(f"Frame {len(self.frames)}")
            
            # Select new frame
            self.frame_list.setCurrentRow(len(self.frames) - 1)
            
            # Update UI state
            self.update_ui_state()
            self.status_bar.showMessage(f"Added frame from: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add frame: {str(e)}")
    
    def remove_frame(self):
        """Remove selected frame"""
        if not self.frames or self.current_frame < 0:
            return
            
        # Ask for confirmation
        reply = QMessageBox.question(self, "Remove Frame", 
                                    f"Are you sure you want to remove frame {self.current_frame + 1}?",
                                    QMessageBox.Yes | QMessageBox.No)
                                    
        if reply == QMessageBox.Yes:
            # Remove frame
            self.frames.pop(self.current_frame)
            
            # Update list
            self.frame_list.takeItem(self.current_frame)
            
            # Renumber remaining frames
            for i in range(self.frame_list.count()):
                self.frame_list.item(i).setText(f"Frame {i+1}")
            
            # Update current frame
            if self.frames:
                if self.current_frame >= len(self.frames):
                    self.current_frame = len(self.frames) - 1
                self.frame_list.setCurrentRow(self.current_frame)
                self.display_frame(self.current_frame)
            else:
                self.current_frame = -1
                self.image_label.clear()
            
            # Update UI state
            self.update_ui_state()
            self.status_bar.showMessage("Frame removed")
    
    def move_frame_up(self):
        """Move selected frame up in list"""
        if not self.frames or self.current_frame <= 0:
            return
            
        # Swap frames
        self.frames[self.current_frame], self.frames[self.current_frame - 1] = \
            self.frames[self.current_frame - 1], self.frames[self.current_frame]
        
        # Update list
        current_text = self.frame_list.item(self.current_frame).text()
        prev_text = self.frame_list.item(self.current_frame - 1).text()
        
        self.frame_list.item(self.current_frame).setText(prev_text)
        self.frame_list.item(self.current_frame - 1).setText(current_text)
        
        # Update selection
        self.current_frame -= 1
        self.frame_list.setCurrentRow(self.current_frame)
        
        self.status_bar.showMessage("Frame moved up")
    
    def move_frame_down(self):
        """Move selected frame down in list"""
        if not self.frames or self.current_frame >= len(self.frames) - 1:
            return
            
        # Swap frames
        self.frames[self.current_frame], self.frames[self.current_frame + 1] = \
            self.frames[self.current_frame + 1], self.frames[self.current_frame]
        
        # Update list
        current_text = self.frame_list.item(self.current_frame).text()
        next_text = self.frame_list.item(self.current_frame + 1).text()
        
        self.frame_list.item(self.current_frame).setText(next_text)
        self.frame_list.item(self.current_frame + 1).setText(current_text)
        
        # Update selection
        self.current_frame += 1
        self.frame_list.setCurrentRow(self.current_frame)
        
        self.status_bar.showMessage("Frame moved down")
    
    def on_frame_selected(self):
        """Handle frame selection change"""
        selected_items = self.frame_list.selectedItems()
        if selected_items:
            # Get index of selected frame
            index = self.frame_list.row(selected_items[0])
            self.current_frame = index
            
            # Display frame
            self.display_frame(index)
    
    def display_frame(self, index):
        """Display frame with given index"""
        if not self.frames or index < 0 or index >= len(self.frames):
            self.image_label.clear()
            return
            
        frame = self.frames[index]
        
        # Create pixmap from image data
        if frame.image_data:
            # Create base image
            pixmap = QPixmap()
            pixmap.loadFromData(frame.image_data)
            
            # Create final image with background color
            final_image = QImage(pixmap.width(), pixmap.height(), QImage.Format_ARGB32)
            final_image.fill(self.background_color)
            
            # Draw shadow if enabled
            painter = QPainter(final_image)
            
            if frame.shadow_enabled:
                # Create shadow image
                shadow_pixmap = QPixmap()
                shadow_pixmap.loadFromData(frame.image_data)
                
                # Calculate shadow position with offsets
                shadow_x = frame.shadow_x_offset
                shadow_y = frame.shadow_y_offset
                
                # Set shadow color and transparency
                painter.setOpacity(frame.shadow_transparency / 255.0)
                painter.drawPixmap(shadow_x, shadow_y, shadow_pixmap)
                painter.setOpacity(1.0)
            
            # Draw main image with offsets
            painter.drawPixmap(frame.x_offset, frame.y_offset, pixmap)
            painter.end()
            
            # Display final image
            display_pixmap = QPixmap.fromImage(final_image)
            self.image_label.setPixmap(display_pixmap)
            
            # Update UI controls with frame info
            self.update_controls_from_frame(frame)
        else:
            self.image_label.clear()
    
    def update_controls_from_frame(self, frame):
        """Update UI controls based on frame data"""
        # Block signals to avoid feedback loops
        self.direction_spin.blockSignals(True)
        self.delay_spin.blockSignals(True)
        self.x_offset_spin.blockSignals(True)
        self.y_offset_spin.blockSignals(True)
        self.frame_x_offset.blockSignals(True)
        self.frame_y_offset.blockSignals(True)
        self.shadow_x_offset.blockSignals(True)
        self.transparency_slider.blockSignals(True)
        
        # Update control values
        self.direction_spin.setValue(frame.direction)
        self.delay_spin.setValue(frame.delay)
        self.x_offset_spin.setValue(frame.x_offset)
        self.y_offset_spin.setValue(frame.y_offset)
        self.frame_x_offset.setValue(frame.x_offset)
        self.frame_y_offset.setValue(frame.y_offset)
        self.shadow_x_offset.setValue(frame.shadow_x_offset)
        self.transparency_slider.setValue(frame.shadow_transparency)
        
        # Shadow radio buttons
        if frame.shadow_enabled:
            self.layer1_shadow_radio.setChecked(True)
        else:
            self.no_shadow_radio.setChecked(True)
        
        # Re-enable signals
        self.direction_spin.blockSignals(False)
        self.delay_spin.blockSignals(False)
        self.x_offset_spin.blockSignals(False)
        self.y_offset_spin.blockSignals(False)
        self.frame_x_offset.blockSignals(False)
        self.frame_y_offset.blockSignals(False) 
        self.shadow_x_offset.blockSignals(False)
        self.transparency_slider.blockSignals(False)
    
    def toggle_play(self):
        """Toggle animation playback"""
        if not self.frames:
            return
            
        if self.is_playing:
            # Stop animation
            self.animation_timer.stop()
            self.is_playing = False
            self.play_btn.setText("Play")
        else:
            # Start animation
            current_frame = self.frames[self.current_frame]
            self.animation_timer.start(current_frame.delay)
            self.is_playing = True
            self.play_btn.setText("Stop")
    
    def next_frame(self):
        """Show next frame"""
        if not self.frames:
            return
            
        # Increment current frame index
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        
        # Update list selection
        self.frame_list.setCurrentRow(self.current_frame)
        
        # Display frame
        self.display_frame(self.current_frame)
        
        # Update timer interval if playing
        if self.is_playing:
            current_frame = self.frames[self.current_frame]
            self.animation_timer.setInterval(current_frame.delay)
    
    def prev_frame(self):
        """Show previous frame"""
        if not self.frames:
            return
            
        # Decrement current frame index
        self.current_frame = (self.current_frame - 1) % len(self.frames)
        
        # Update list selection
        self.frame_list.setCurrentRow(self.current_frame)
        
        # Display frame
        self.display_frame(self.current_frame)
    
    def export_current_frame(self):
        """Export current frame as image"""
        if not self.frames or self.current_frame < 0:
            return
            
        frame = self.frames[self.current_frame]
        if not frame.image_data:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Frame", "", "PNG Files (*.png);;JPG Files (*.jpg);;All Files (*)")
        if file_path:
            try:
                # Create image from frame data
                image = QImage()
                image.loadFromData(frame.image_data)
                
                # Save image
                image.save(file_path)
                self.status_bar.showMessage(f"Exported frame to: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export frame: {str(e)}")
    def export_all_frames(self):
        """Export all frames as individual images"""
        if not self.frames:
            QMessageBox.warning(self, "Warning", "No frames to export")
            return
			
        directory = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not directory:
            return
			
		# Ask for export format
        formats = ["PNG (*.png)", "JPG (*.jpg)", "BMP (*.bmp)","TGA (*.tga)", "All Supported (*.png *.jpg *.bmp *.tga)"]
        format_dialog = QDialog(self)
        format_dialog.setWindowTitle("Select Export Format")
        format_layout = QVBoxLayout(format_dialog)
		
        format_group = QButtonGroup(format_dialog)
        for i, fmt in enumerate(formats):
            radio = QRadioButton(fmt)
            if i == 0:  # Default to PNG
                radio.setChecked(True)
            format_group.addButton(radio, i)
            format_layout.addWidget(radio)
		
		# Add buttons
        buttons = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(format_dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(format_dialog.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        format_layout.addLayout(buttons)
        
        if format_dialog.exec_() != QDialog.Accepted:
            return
		
		# Get selected format
        selected_format_id = format_group.checkedId()
        if selected_format_id == 0:
            ext = "png"
        elif selected_format_id == 1:
            ext = "jpg"
        elif selected_format_id == 2:
            ext = "bmp"
        else:
            ext = "png"  # Default to PNG
		
        try:
            export_count = 0
            for i, frame in enumerate(self.frames):
                if not frame.image_data:
                    continue
                    
                # Create image from frame data
                image = QImage()
                if not image.loadFromData(frame.image_data):
                    self.status_bar.showMessage(f"Failed to load frame {i}")
                    continue
                
                # Generate filename based on frame index and direction
                file_path = f"{directory}/frame_{i:04d}_dir_{frame.direction}.{ext}"
                
                # Save image
                if image.save(file_path):
                    export_count += 1
                else:
                    self.status_bar.showMessage(f"Failed to save frame {i}")
                    
            if export_count > 0:
                self.status_bar.showMessage(f"Exported {export_count} frames to: {directory}")
            else:
                self.status_bar.showMessage("No frames were exported")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export frames: {str(e)}")

    def export_sprite_sheet(self):
        """Export all frames as a single sprite sheet image"""
        if not self.frames:
            QMessageBox.warning(self, "Warning", "No frames to export")
            return
		
		# Get export path
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Sprite Sheet", "", 
											"PNG Files (*.png);;JPG Files (*.jpg);;All Files (*)")
        if not file_path:
            return
		
        try:
            # Calculate rows and columns for the sprite sheet
            frame_count = len(self.frames)
            cols = min(8, frame_count)  # Maximum 8 columns
            rows = (frame_count + cols - 1) // cols  # Ceiling division
            
            # Create image big enough for all frames
            sprite_sheet = QImage(cols * self.header.width, rows * self.header.height, 
                                QImage.Format_ARGB32)
            sprite_sheet.fill(Qt.transparent)
            
            # Create painter for drawing frames
            painter = QPainter(sprite_sheet)
            
            # Draw each frame onto the sprite sheet
            for i, frame in enumerate(self.frames):
                if not frame.image_data:
                    continue
                    
                # Calculate position in the grid
                row = i // cols
                col = i % cols
                
                # Create image from frame data
                image = QImage()
                if image.loadFromData(frame.image_data):
                    # Draw frame at position
                    painter.drawImage(col * self.header.width, row * self.header.height, image)
                
            painter.end()
            
            # Save sprite sheet
            if sprite_sheet.save(file_path):
                self.status_bar.showMessage(f"Exported sprite sheet to: {file_path}")
            else:
                self.status_bar.showMessage("Failed to save sprite sheet")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export sprite sheet: {str(e)}")

    def export_current_frame(self): 
        """Export current frame as image""" 
        if not self.frames or self.current_frame < 0: 
            QMessageBox.warning(self, "Warning", "No frame to export") 
            return 
        frame = self.frames[self.current_frame] 
        if not frame.image_data: 
            QMessageBox.warning(self, "Warning", "Current frame has no image data") 
            return 
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Frame", "", 
                                        "PNG Files (*.png);;JPG Files (*.jpg);;BMP Files (*.bmp);; TGA File (*.tga);;All Files (*)") 
        if file_path: 
            try:
                # Create image from frame data
                image = QImage()
                image.loadFromData(frame.image_data)
                
                # Save image
                if image.save(file_path):
                    self.status_bar.showMessage(f"Exported frame to: {file_path}")
                else:
                    self.status_bar.showMessage("Failed to save frame")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export frame: {str(e)}")

    def export_tga(self):
        """Export current frame as TGA image""" 
        if not self.frames or self.current_frame < 0: 
            QMessageBox.warning(self, "Warning", "No frame to export") 
            return 
        frame = self.frames[self.current_frame] 
        if not frame.image_data: 
            QMessageBox.warning(self, "Warning", "Current frame has no image data") 
            return 
        file_path, _ = QFileDialog.getSaveFileName(self, "Export TGA", "", "TGA Files (*.tga);;All Files (*)") 
        if not file_path: 
            return
			
        try:
            # Create image from frame data
            image = QImage()
            image.loadFromData(frame.image_data)
            
            # For TGA export, we need to convert to a format suitable for TGA
            # TGA files can be saved directly by QImage in some Qt versions
            if hasattr(QImage, 'Format_RGBA8888'):
                # Convert image to RGBA format
                image = image.convertToFormat(QImage.Format_RGBA8888)
            
            # Save as TGA
            if image.save(file_path, "TGA"):
                self.status_bar.showMessage(f"Exported TGA to: {file_path}")
            else:
                # Fall back to manual TGA export if direct saving fails
                self.status_bar.showMessage("Direct TGA export not supported, trying manual export...")
                self.export_manual_tga(image, file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export TGA: {str(e)}")
			
    def export_manual_tga(self, image, file_path):
        """Manual TGA export when QImage.save() doesn't support TGA format"""
        try:
            width = image.width()
            height = image.height()
            
            # Open file for binary write
            with open(file_path, 'wb') as f:
                # Write TGA header
                # ID Length (1 byte)
                f.write(bytes([0]))
                # Color Map Type (1 byte) - no color map
                f.write(bytes([0]))
                # Image Type (1 byte) - uncompressed true-color
                f.write(bytes([2]))
                # Color Map Specification (5 bytes) - all zeros for no color map
                f.write(bytes([0, 0, 0, 0, 0]))
                # X Origin (2 bytes)
                f.write(struct.pack("<H", 0))
                # Y Origin (2 bytes)
                f.write(struct.pack("<H", 0))
                # Width (2 bytes)
                f.write(struct.pack("<H", width))
                # Height (2 bytes)
                f.write(struct.pack("<H", height))
                # Pixel Depth (1 byte) - 32 bits per pixel (BGRA)
                f.write(bytes([32]))
                # Image Descriptor (1 byte) - top-to-bottom, left-to-right
                f.write(bytes([8]))
                
                # Write pixel data
                for y in range(height):
                    for x in range(width):
                        pixel = image.pixel(x, y)
                        # Get RGBA components
                        red = (pixel >> 16) & 0xFF
                        green = (pixel >> 8) & 0xFF
                        blue = pixel & 0xFF
                        alpha = (pixel >> 24) & 0xFF
                        
                        # Write in BGRA order
                        f.write(bytes([blue, green, red, alpha]))
                
            self.status_bar.showMessage(f"Exported TGA to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export manual TGA: {str(e)}")

    def convert_to_spr(self):
        """Convert current ASF file to SPR format"""
        if not self.frames:
            QMessageBox.warning(self, "Warning", "No frames to convert")
            return 
        file_path, _ = QFileDialog.getSaveFileName(self, "Save SPR File", "", "SPR Files (*.spr);;All Files (*)") 
        if not file_path: 
            return
            
        try:
            # Save as SPR format
            self.save_spr_file(file_path)
            
            # Update status
            self.status_bar.showMessage(f"Converted to SPR: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to convert to SPR: {str(e)}")

    def convert_to_asf(self):
        """Convert current SPR file to ASF format"""
        if not self.frames:
            QMessageBox.warning(self, "Warning", "No frames to convert")
            return
			
        file_path, _ = QFileDialog.getSaveFileName(self, "Save ASF File", "", "ASF Files (*.asf);;All Files (*)") 
        if not file_path:
            return
			
        try:
            # Save as ASF format
            self.save_asf_file(file_path)
            
            # Update status
            self.status_bar.showMessage(f"Converted to ASF: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to convert to ASF: {str(e)}")

    def on_frame_selected(self):
        """Handle frame selection from list"""
        selected_items = self.frame_list.selectedItems()
        if not selected_items:
            return
            
        # Get selected index
        index = self.frame_list.row(selected_items[0])
        if index < 0 or index >= len(self.frames):
            return
            
        # Update current frame
        self.current_frame = index
        
        # Display frame
        self.display_frame(index)
        
        # Update frame controls
        self.update_frame_controls()
        
    def update_ui_state(self):
        """Update UI state based on current data"""
        has_frames = len(self.frames) > 0
        current_frame_valid = self.current_frame >= 0 and self.current_frame < len(self.frames)
        
        # Update frame control buttons
        self.remove_frame_btn.setEnabled(has_frames)
        self.move_up_btn.setEnabled(current_frame_valid and self.current_frame > 0)
        self.move_down_btn.setEnabled(current_frame_valid and self.current_frame < len(self.frames) - 1)
        
        # Update playback controls
        self.play_btn.setEnabled(has_frames)
        self.prev_btn.setEnabled(has_frames)
        self.next_btn.setEnabled(has_frames)
        
        # Update export actions
        self.export_current_frame_action.setEnabled(current_frame_valid)
        self.export_all_frames_action.setEnabled(has_frames)
        self.export_sprite_sheet_action.setEnabled(has_frames)
        self.export_tga_action.setEnabled(current_frame_valid)

    def update_frame_controls(self):
        """Update frame control values"""
        if not self.frames or self.current_frame < 0:
            return
            
        frame = self.frames[self.current_frame]
        
        # Block signals to prevent feedback loops
        self.direction_spin.blockSignals(True)
        self.delay_spin.blockSignals(True)
        self.x_offset_spin.blockSignals(True)
        self.y_offset_spin.blockSignals(True)
        
        # Update control values
        self.direction_spin.setValue(frame.direction)
        self.delay_spin.setValue(frame.delay)
        self.x_offset_spin.setValue(frame.x_offset)
        self.y_offset_spin.setValue(frame.y_offset)
        
        # Re-enable signals
        self.direction_spin.blockSignals(False)
        self.delay_spin.blockSignals(False)
        self.x_offset_spin.blockSignals(False)
        self.y_offset_spin.blockSignals(False)

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About PyASFTool",
            "PyASFTool - ASF/SPR File Editor\n\n"  
            "Version 1.0\n"
            "Copyright \n\n"
            "A tool for editing ASF and SPR animation files.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = EnhancedPyAsfTool()
    window.show()
    sys.exit(app.exec_())
