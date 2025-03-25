#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QFileDialog, QComboBox, QListWidget, QMessageBox,
                            QGroupBox, QFormLayout, QSpinBox, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from windows_vm import WindowsVM

class VMWorker(QThread):
    """Worker thread to perform VM operations without blocking the UI"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, operation, vm):
        super().__init__()
        self.operation = operation
        self.vm = vm
    
    def run(self):
        try:
            result = False
            if self.operation == "create":
                self.progress.emit("Creating VM...")
                result = self.vm.create()
            elif self.operation == "start":
                self.progress.emit("Starting VM...")
                result = self.vm.start()
            elif self.operation == "stop":
                self.progress.emit("Stopping VM...")
                result = self.vm.stop()
            elif self.operation == "delete":
                self.progress.emit("Deleting VM...")
                result = self.vm.delete()
            
            self.finished.emit(result, f"{self.operation.capitalize()} operation completed")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class WindowsVMManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VM Manager")
        self.setMinimumSize(800, 600)
        
        # VM storage directory
        self.vm_base_dir = Path.home() / "VirtualMachines"
        os.makedirs(self.vm_base_dir, exist_ok=True)
        
        # Current VM list
        self.vms = self._scan_vms()
        
        self.init_ui()
    
    def _scan_vms(self):
        """Scan for existing VMs in the VM directory"""
        vms = []
        if self.vm_base_dir.exists():
            for vm_dir in self.vm_base_dir.iterdir():
                if vm_dir.is_dir():
                    vms.append(vm_dir.name)
        return vms
    
    def init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Left panel - VM list and controls
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # VM List
        vm_group = QGroupBox("Virtual Machines")
        vm_layout = QVBoxLayout()
        
        self.vm_list = QListWidget()
        self.vm_list.addItems(self.vms)
        self.vm_list.currentItemChanged.connect(self.on_vm_selected)
        vm_layout.addWidget(self.vm_list)
        
        # VM Controls
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_vm)
        self.start_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_vm)
        self.stop_btn.setEnabled(False)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_vm)
        self.delete_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.delete_btn)
        
        vm_layout.addLayout(control_layout)
        vm_group.setLayout(vm_layout)
        left_layout.addWidget(vm_group)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh VM List")
        refresh_btn.clicked.connect(self.refresh_vms)
        left_layout.addWidget(refresh_btn)
        
        left_panel.setLayout(left_layout)
        
        # Right panel - VM creation and details
        right_panel = QTabWidget()
        
        # Create VM tab
        create_tab = QWidget()
        create_layout = QFormLayout()
        
        self.vm_name = QLineEdit("WindowsVM")
        create_layout.addRow("VM Name:", self.vm_name)
        
        self.memory = QSpinBox()
        self.memory.setRange(1024, 32768)
        self.memory.setValue(4096)
        self.memory.setSingleStep(1024)
        self.memory.setSuffix(" MB")
        create_layout.addRow("Memory:", self.memory)
        
        self.disk_size = QSpinBox()
        self.disk_size.setRange(10, 500)
        self.disk_size.setValue(50)
        self.disk_size.setSuffix(" GB")
        create_layout.addRow("Disk Size:", self.disk_size)
        
        iso_layout = QHBoxLayout()
        self.iso_path = QLineEdit()
        self.iso_path.setPlaceholderText("Path to Windows ISO file")
        iso_browse = QPushButton("Browse")
        iso_browse.clicked.connect(self.browse_iso)
        iso_layout.addWidget(self.iso_path)
        iso_layout.addWidget(iso_browse)
        create_layout.addRow("ISO File:", iso_layout)
        
        create_btn = QPushButton("Create VM")
        create_btn.clicked.connect(self.create_vm)
        create_layout.addRow("", create_btn)
        
        # Status label
        self.status_label = QLabel("")
        create_layout.addRow("Status:", self.status_label)
        
        create_tab.setLayout(create_layout)
        right_panel.addTab(create_tab, "Create VM")
        
        # VM Details tab
        details_tab = QWidget()
        details_layout = QFormLayout()
        
        self.details_name = QLabel("")
        details_layout.addRow("Name:", self.details_name)
        
        self.details_path = QLabel("")
        details_layout.addRow("Path:", self.details_path)
        
        self.details_disk = QLabel("")
        details_layout.addRow("Disk:", self.details_disk)
        
        self.details_status = QLabel("")
        details_layout.addRow("Status:", self.details_status)
        
        # Boot with ISO section
        iso_boot_layout = QHBoxLayout()
        self.boot_iso_path = QLineEdit()
        self.boot_iso_path.setPlaceholderText("Path to ISO for booting")
        boot_iso_browse = QPushButton("Browse")
        boot_iso_browse.clicked.connect(self.browse_boot_iso)
        iso_boot_layout.addWidget(self.boot_iso_path)
        iso_boot_layout.addWidget(boot_iso_browse)
        details_layout.addRow("Boot with ISO:", iso_boot_layout)
        
        boot_with_iso = QPushButton("Start with ISO")
        boot_with_iso.clicked.connect(self.start_with_iso)
        details_layout.addRow("", boot_with_iso)
        
        details_tab.setLayout(details_layout)
        right_panel.addTab(details_tab, "VM Details")
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def browse_iso(self):
        file_dialog = QFileDialog()
        iso_path, _ = file_dialog.getOpenFileName(
            self, "Select Windows ISO", str(Path.home()),
            "ISO Files (*.iso);;All Files (*)"
        )
        if iso_path:
            self.iso_path.setText(iso_path)
    
    def browse_boot_iso(self):
        file_dialog = QFileDialog()
        iso_path, _ = file_dialog.getOpenFileName(
            self, "Select Boot ISO", str(Path.home()),
            "ISO Files (*.iso);;All Files (*)"
        )
        if iso_path:
            self.boot_iso_path.setText(iso_path)
    
    def create_vm(self):
        vm_name = self.vm_name.text()
        memory = str(self.memory.value())
        disk_size = f"{self.disk_size.value()}G"
        iso_path = self.iso_path.text()
        
        if not vm_name:
            QMessageBox.warning(self, "Error", "VM name cannot be empty")
            return
        
        if not iso_path:
            QMessageBox.warning(self, "Error", "Windows ISO path is required")
            return
        
        if not os.path.exists(iso_path):
            QMessageBox.warning(self, "Error", "ISO file does not exist")
            return
        
        # Create VM instance
        vm = WindowsVM(
            vm_name=vm_name,
            memory=memory,
            disk_size=disk_size,
            iso_path=iso_path,
            vm_path=str(self.vm_base_dir / vm_name)
        )
        
        # Create worker thread
        self.worker = VMWorker("create", vm)
        self.worker.progress.connect(self.update_status)
        self.worker.finished.connect(self.on_operation_finished)
        self.worker.start()
    
    def on_vm_selected(self, current, previous):
        if current:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            
            # Update details tab
            vm_name = current.text()
            vm_path = self.vm_base_dir / vm_name
            disk_path = vm_path / f"{vm_name}.qcow2"
            
            self.details_name.setText(vm_name)
            self.details_path.setText(str(vm_path))
            
            if disk_path.exists():
                size_mb = disk_path.stat().st_size / (1024 * 1024)
                self.details_disk.setText(f"{disk_path.name} ({size_mb:.1f} MB used)")
            else:
                self.details_disk.setText("Disk not found")
            
            # Check if VM is running (simplified)
            self.details_status.setText("Unknown")
        else:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
    
    def start_vm(self):
        current_vm = self.vm_list.currentItem()
        if current_vm:
            vm_name = current_vm.text()
            vm = WindowsVM(
                vm_name=vm_name,
                vm_path=str(self.vm_base_dir / vm_name)
            )
            
            self.worker = VMWorker("start", vm)
            self.worker.progress.connect(self.update_status)
            self.worker.finished.connect(self.on_operation_finished)
            self.worker.start()
    
    def start_with_iso(self):
        current_vm = self.vm_list.currentItem()
        if current_vm:
            vm_name = current_vm.text()
            iso_path = self.boot_iso_path.text()
            
            if not iso_path:
                QMessageBox.warning(self, "Error", "Please select an ISO file")
                return
            
            if not os.path.exists(iso_path):
                QMessageBox.warning(self, "Error", "ISO file does not exist")
                return
            
            vm = WindowsVM(
                vm_name=vm_name,
                vm_path=str(self.vm_base_dir / vm_name),
                iso_path=iso_path
            )
            
            self.worker = VMWorker("start", vm)
            self.worker.progress.connect(self.update_status)
            self.worker.finished.connect(self.on_operation_finished)
            self.worker.start()
    
    def stop_vm(self):
        current_vm = self.vm_list.currentItem()
        if current_vm:
            vm_name = current_vm.text()
            vm = WindowsVM(
                vm_name=vm_name,
                vm_path=str(self.vm_base_dir / vm_name)
            )
            vm.vm_running = True  # Assume it's running
            
            self.worker = VMWorker("stop", vm)
            self.worker.progress.connect(self.update_status)
            self.worker.finished.connect(self.on_operation_finished)
            self.worker.start()
    
    def delete_vm(self):
        current_vm = self.vm_list.currentItem()
        if current_vm:
            vm_name = current_vm.text()
            
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete VM '{vm_name}'?\nThis will delete all VM files.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                vm = WindowsVM(
                    vm_name=vm_name,
                    vm_path=str(self.vm_base_dir / vm_name)
                )
                
                self.worker = VMWorker("delete", vm)
                self.worker.progress.connect(self.update_status)
                self.worker.finished.connect(self.on_operation_finished)
                self.worker.start()
    
    def refresh_vms(self):
        self.vms = self._scan_vms()
        self.vm_list.clear()
        self.vm_list.addItems(self.vms)
        self.update_status("VM list refreshed")
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def on_operation_finished(self, success, message):
        if success:
            self.update_status(message)
            self.refresh_vms()
        else:
            QMessageBox.warning(self, "Operation Failed", message)
            self.update_status("Operation failed")

def main():
    app = QApplication(sys.argv)
    window = WindowsVMManager()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
