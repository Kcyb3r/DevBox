import os
import subprocess
import platform
import time
from pathlib import Path

class WindowsVM:
    def __init__(self, vm_name="WindowsVM", memory="4096", disk_size="50G", 
                 iso_path=None, vm_path=None):
        """
        Initialize a Windows VM instance
        
        Args:
            vm_name: Name of the virtual machine
            memory: RAM allocation in MB
            disk_size: Disk size (e.g. "50G")
            iso_path: Path to Windows ISO file
            vm_path: Directory to store VM files
        """
        self.vm_name = vm_name
        self.memory = memory
        self.disk_size = disk_size
        self.iso_path = iso_path
        
        if vm_path:
            self.vm_path = Path(vm_path)
        else:
            self.vm_path = Path.home() / "VirtualMachines" / vm_name
            
        self.disk_path = self.vm_path / f"{vm_name}.qcow2"
        self.vm_running = False
        
        # Detect the virtualization tool based on platform
        self.virtualization_tool = self._detect_virtualization_tool()
    
    def _detect_virtualization_tool(self):
        """Detect the appropriate virtualization tool based on the platform"""
        system = platform.system().lower()
        
        if system == "windows":
            # Check for Hyper-V or VirtualBox
            try:
                subprocess.run(["powershell", "Get-Command", "Get-VM"], 
                              check=True, capture_output=True)
                return "hyperv"
            except subprocess.CalledProcessError:
                return "virtualbox"
        elif system == "darwin":  # macOS
            return "virtualbox"
        else:  # Linux
            # Check for KVM
            if os.path.exists("/dev/kvm"):
                return "qemu"
            else:
                return "virtualbox"
    
    def create(self):
        """Create a new Windows VM"""
        if not self.iso_path:
            raise ValueError("Windows ISO path is required to create a VM")
        
        # Create VM directory if it doesn't exist
        os.makedirs(self.vm_path, exist_ok=True)
        
        if self.virtualization_tool == "qemu":
            return self._create_qemu()
        elif self.virtualization_tool == "hyperv":
            return self._create_hyperv()
        elif self.virtualization_tool == "virtualbox":
            return self._create_virtualbox()
        else:
            raise NotImplementedError(f"Virtualization tool {self.virtualization_tool} not supported")
    
    def _create_qemu(self):
        """Create VM using QEMU/KVM"""
        # Create disk image
        subprocess.run([
            "qemu-img", "create", "-f", "qcow2", 
            str(self.disk_path), self.disk_size
        ], check=True)
        
        print(f"Created Windows VM disk at {self.disk_path}")
        return True
    
    def _create_hyperv(self):
        """Create VM using Hyper-V"""
        # Create VM using PowerShell
        ps_commands = [
            f"New-VM -Name '{self.vm_name}' -MemoryStartupBytes {self.memory}MB -Generation 2 -Path '{self.vm_path}'",
            f"New-VHD -Path '{self.disk_path}' -SizeBytes {self.disk_size.replace('G', '000000000')} -Dynamic",
            f"Add-VMHardDiskDrive -VMName '{self.vm_name}' -Path '{self.disk_path}'",
            f"Add-VMDvdDrive -VMName '{self.vm_name}' -Path '{self.iso_path}'",
            f"Set-VMFirmware -VMName '{self.vm_name}' -EnableSecureBoot Off",
            f"Set-VMFirmware -VMName '{self.vm_name}' -FirstBootDevice (Get-VMDvdDrive -VMName '{self.vm_name}')"
        ]
        
        for cmd in ps_commands:
            subprocess.run(["powershell", "-Command", cmd], check=True)
        
        print(f"Created Windows VM '{self.vm_name}' using Hyper-V")
        return True
    
    def _create_virtualbox(self):
        """Create VM using VirtualBox"""
        # Create VM
        subprocess.run([
            "VBoxManage", "createvm", "--name", self.vm_name,
            "--ostype", "Windows10_64", "--register",
            "--basefolder", str(self.vm_path)
        ], check=True)
        
        # Set memory and CPU
        subprocess.run([
            "VBoxManage", "modifyvm", self.vm_name,
            "--memory", self.memory, "--cpus", "2"
        ], check=True)
        
        # Create and attach disk
        subprocess.run([
            "VBoxManage", "createmedium", "disk",
            "--filename", str(self.disk_path),
            "--size", self.disk_size.replace("G", "000")
        ], check=True)
        
        # Add SATA controller
        subprocess.run([
            "VBoxManage", "storagectl", self.vm_name,
            "--name", "SATA Controller", "--add", "sata"
        ], check=True)
        
        # Attach disk to SATA controller
        subprocess.run([
            "VBoxManage", "storageattach", self.vm_name,
            "--storagectl", "SATA Controller",
            "--port", "0", "--device", "0", "--type", "hdd",
            "--medium", str(self.disk_path)
        ], check=True)
        
        # Add IDE controller and attach ISO
        subprocess.run([
            "VBoxManage", "storagectl", self.vm_name,
            "--name", "IDE Controller", "--add", "ide"
        ], check=True)
        
        subprocess.run([
            "VBoxManage", "storageattach", self.vm_name,
            "--storagectl", "IDE Controller",
            "--port", "0", "--device", "0", "--type", "dvddrive",
            "--medium", str(self.iso_path)
        ], check=True)
        
        print(f"Created Windows VM '{self.vm_name}' using VirtualBox")
        return True
    
    def start(self):
        """Start the Windows VM"""
        if self.virtualization_tool == "qemu":
            # Start VM with QEMU
            cmd = [
                "qemu-system-x86_64", 
                "-enable-kvm", 
                "-m", self.memory,
                "-smp", "cores=2,threads=2",  # Better CPU configuration
                "-cpu", "host",  # Use host CPU model for better performance
                "-drive", f"file={self.disk_path},format=qcow2,if=virtio",  # Use virtio for better disk performance
            ]
            
            # Add ISO if specified
            if self.iso_path:
                cmd.extend(["-cdrom", self.iso_path])
                # Force boot from CD if it's likely a fresh install
                if os.path.exists(self.disk_path) and os.path.getsize(self.disk_path) < 1000000000:
                    cmd.extend(["-boot", "d"])
                    print("Booting from ISO for installation...")
                else:
                    print("ISO provided but booting from disk first...")
            else:
                print("No ISO provided, booting from disk...")
            
            # Add display and network with better performance
            cmd.extend([
                "-display", "gtk,grab-on-hover=on",
                "-vga", "virtio",  # Better graphics performance
                "-device", "virtio-net,netdev=net0",
                "-netdev", "user,id=net0",
                "-usb",
                "-device", "usb-tablet",  # Better mouse integration
            ])
            
            # Run in foreground for better visibility of issues
            print(f"Starting QEMU with command: {' '.join(cmd)}")
            print("Windows VM is starting. This may take a few minutes, especially for first boot...")
            
            # Use Popen with stdout/stderr redirection to see any errors
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if process started successfully
            if process.poll() is None:
                print("QEMU process started successfully. VM window should appear shortly.")
            else:
                stdout, stderr = process.communicate(timeout=5)
                print(f"Error starting VM: {stderr}")
                return False
            
        elif self.virtualization_tool == "hyperv":
            # Start VM with Hyper-V
            subprocess.run(["powershell", "-Command", f"Start-VM -Name '{self.vm_name}'"], check=True)
            
        elif self.virtualization_tool == "virtualbox":
            # Start VM with VirtualBox
            subprocess.run(["VBoxManage", "startvm", self.vm_name], check=True)
        
        self.vm_running = True
        print(f"Started Windows VM '{self.vm_name}'")
        return True
    
    def stop(self):
        """Stop the Windows VM"""
        if not self.vm_running:
            print(f"VM '{self.vm_name}' is not running")
            return False
        
        if self.virtualization_tool == "qemu":
            # This is a simplified approach - in a real implementation, you'd want to
            # use a more graceful shutdown method
            subprocess.run(["pkill", "-f", f"qemu-system-x86_64.*{self.disk_path}"], check=False)
            
        elif self.virtualization_tool == "hyperv":
            subprocess.run(["powershell", "-Command", f"Stop-VM -Name '{self.vm_name}' -Force"], check=True)
            
        elif self.virtualization_tool == "virtualbox":
            subprocess.run(["VBoxManage", "controlvm", self.vm_name, "acpipowerbutton"], check=True)
        
        self.vm_running = False
        print(f"Stopped Windows VM '{self.vm_name}'")
        return True
    
    def delete(self):
        """Delete the Windows VM and its files"""
        # First stop the VM if it's running
        if self.vm_running:
            self.stop()
            time.sleep(2)  # Give it time to stop
        
        if self.virtualization_tool == "qemu":
            # For QEMU, just delete the disk file
            if os.path.exists(self.disk_path):
                os.remove(self.disk_path)
                
        elif self.virtualization_tool == "hyperv":
            # Remove VM using Hyper-V PowerShell
            subprocess.run(["powershell", "-Command", f"Remove-VM -Name '{self.vm_name}' -Force"], check=True)
            
            # Delete disk file
            if os.path.exists(self.disk_path):
                os.remove(self.disk_path)
                
        elif self.virtualization_tool == "virtualbox":
            # Unregister and delete VM
            subprocess.run(["VBoxManage", "unregistervm", self.vm_name, "--delete"], check=True)
        
        # Remove VM directory if it exists and is empty
        try:
            os.rmdir(self.vm_path)
        except (OSError, FileNotFoundError):
            pass
        
        print(f"Deleted Windows VM '{self.vm_name}'")
        return True 