#!/usr/bin/env python3
import argparse
import os
from windows_vm import WindowsVM

def main():
    parser = argparse.ArgumentParser(description="Windows Virtual Machine Manager")
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new VM")
    create_parser.add_argument("--name", default="WindowsVM", help="Name of the VM")
    create_parser.add_argument("--memory", default="4096", help="Memory allocation in MB")
    create_parser.add_argument("--disk", default="50G", help="Disk size (e.g. 50G)")
    create_parser.add_argument("--iso", required=True, help="Path to Windows ISO file")
    create_parser.add_argument("--path", help="Directory to store VM files")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the VM")
    start_parser.add_argument("--name", default="WindowsVM", help="Name of the VM")
    start_parser.add_argument("--path", help="Directory where VM files are stored")
    start_parser.add_argument("--iso", help="Path to Windows ISO file (for boot)")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the VM")
    stop_parser.add_argument("--name", default="WindowsVM", help="Name of the VM")
    stop_parser.add_argument("--path", help="Directory where VM files are stored")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete the VM")
    delete_parser.add_argument("--name", default="WindowsVM", help="Name of the VM")
    delete_parser.add_argument("--path", help="Directory where VM files are stored")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize VM
    vm = WindowsVM(
        vm_name=args.name,
        memory=args.memory if hasattr(args, 'memory') else "4096",
        disk_size=args.disk if hasattr(args, 'disk') else "50G",
        iso_path=args.iso if hasattr(args, 'iso') else None,
        vm_path=args.path if hasattr(args, 'path') else None
    )
    
    # Execute command
    if args.command == "create":
        vm.create()
    elif args.command == "start":
        vm.start()
    elif args.command == "stop":
        vm.stop()
    elif args.command == "delete":
        vm.delete()

if __name__ == "__main__":
    main() 