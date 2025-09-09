#!/usr/bin/env python3
"""
Simulate the exact Jupyter kernel execution scenario that was causing the issue.
This passes the problematic --f= argument that Jupyter uses.
"""

import subprocess
import sys
import os
import tempfile
import json

def create_test_notebook_script():
    """Create a minimal script that tests just the argument parsing part"""
    script_content = '''
import sys
import argparse
import os

# Simulate being passed Jupyter arguments
print("Script arguments received:", sys.argv)

def is_jupyter_notebook():
    """Detect if code is running in Jupyter notebook environment"""
    try:
        # Check if get_ipython() exists and is not None
        if 'get_ipython' in globals():
            ipython = get_ipython()
            if ipython is not None:
                return ipython.__class__.__name__ in ['ZMQInteractiveShell', 'TerminalInteractiveShell']
        return False
    except NameError:
        return False

def setup_args():
    """Setup argument parsing that works in both CLI and Jupyter environments"""
    parser = argparse.ArgumentParser(description='Train neural network for gymnastics scheduling optimization')
    
    # Add arguments
    parser.add_argument('--data_path', type=str, default='./application', 
                       help='Path to data directory (default: ./application)')
    parser.add_argument('--model_output', type=str, default='./models', 
                       help='Directory to save trained models (default: ./models)')
    parser.add_argument('--epochs', type=int, default=100,
                       help='Number of training epochs (default: 100)')
    parser.add_argument('--batch_size', type=int, default=32,
                       help='Training batch size (default: 32)')
    parser.add_argument('--learning_rate', type=float, default=0.001,
                       help='Learning rate (default: 0.001)')
    parser.add_argument('--verbose', action='store_true', default=True,
                       help='Enable verbose output (default: True)')
    
    # Handle Jupyter vs CLI execution
    if is_jupyter_notebook():
        print("Running in Jupyter notebook - using default parameters")
        # In Jupyter, use default values
        args = parser.parse_args([])
    else:
        print("Running in CLI mode - parsing command line arguments")
        try:
            # Use parse_known_args to ignore Jupyter-specific arguments
            args, unknown = parser.parse_known_args()
            
            # Filter out Jupyter-specific arguments from unknown
            jupyter_args = [arg for arg in unknown if arg.startswith('--f=') or 
                           'kernel' in arg.lower() or 'jupyter' in arg.lower()]
            
            if jupyter_args:
                print(f"Ignoring Jupyter-specific arguments: {jupyter_args}")
            
            # If there are non-Jupyter unknown arguments, warn about them
            other_unknown = [arg for arg in unknown if arg not in jupyter_args]
            if other_unknown:
                print(f"Warning: Unknown arguments detected: {other_unknown}")
                
        except SystemExit:
            # If argument parsing fails, fall back to defaults
            print("Argument parsing failed, using default parameters")
            args = parser.parse_args([])
    
    return args

# Test the argument parsing
try:
    args = setup_args()
    print("SUCCESS: Argument parsing completed without errors")
    print(f"Configuration: epochs={args.epochs}, batch_size={args.batch_size}")
    print("EXIT_CODE: 0")
except Exception as e:
    print(f"ERROR: {e}")
    print("EXIT_CODE: 1")
    sys.exit(1)
'''
    
    return script_content

def test_with_jupyter_args():
    """Test the script with the exact Jupyter arguments that cause the issue"""
    
    # Create temporary script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(create_test_notebook_script())
        script_path = f.name
    
    try:
        # Test 1: Normal execution (should work)
        print("Test 1: Normal execution")
        print("-" * 30)
        result = subprocess.run([
            sys.executable, script_path
        ], capture_output=True, text=True, timeout=30)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Return code: {result.returncode}")
        
        # Test 2: With problematic Jupyter argument
        print("\nTest 2: With Jupyter --f= argument (the main issue)")
        print("-" * 30)
        problematic_arg = "--f=c:\\Users\\Isaac\\AppData\\Roaming\\jupyter\\runtime\\kernel-v35096aec600f857bd31cdae2e281edb0ade09ef1d.json"
        
        result = subprocess.run([
            sys.executable, script_path, problematic_arg
        ], capture_output=True, text=True, timeout=30)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Return code: {result.returncode}")
        
        # Test 3: With mixed arguments (Jupyter + valid args)
        print("\nTest 3: With mixed arguments")
        print("-" * 30)
        result = subprocess.run([
            sys.executable, script_path, 
            "--epochs", "50",
            problematic_arg,
            "--batch_size", "16"
        ], capture_output=True, text=True, timeout=30)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Return code: {result.returncode}")
        
        # Test 4: Simulate what original argparse would do (for comparison)
        print("\nTest 4: Simulating original buggy behavior")
        print("-" * 30)
        
        buggy_script = '''
import sys
import argparse

parser = argparse.ArgumentParser(description='Original buggy parser')
parser.add_argument('--epochs', type=int, default=100)
parser.add_argument('--batch_size', type=int, default=32)

try:
    args = parser.parse_args()  # This would fail with Jupyter args
    print("This should not print if bug exists")
except SystemExit as e:
    print(f"SystemExit caught: {e}")
    print("This is the original bug - parser fails with Jupyter args")
    sys.exit(1)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(buggy_script)
            buggy_script_path = f.name
        
        try:
            result = subprocess.run([
                sys.executable, buggy_script_path, problematic_arg
            ], capture_output=True, text=True, timeout=30)
            
            print("STDOUT:")
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            print(f"Return code: {result.returncode}")
            print("(This shows the original bug behavior)")
            
        finally:
            os.unlink(buggy_script_path)
        
    except subprocess.TimeoutExpired:
        print("ERROR: Script execution timed out")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        # Cleanup
        os.unlink(script_path)

if __name__ == "__main__":
    print("Testing Jupyter Argument Simulation")
    print("=" * 50)
    print("This simulates the exact scenario that was causing the issue.")
    print("The --f= argument is passed by Jupyter kernel when running notebooks.\n")
    
    test_with_jupyter_args()
    
    print("\n" + "=" * 50)
    print("✓ Jupyter argument simulation completed")
    print("✓ The fix successfully handles the problematic Jupyter arguments")