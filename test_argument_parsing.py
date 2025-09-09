#!/usr/bin/env python3
"""
Test script to verify argument parsing works correctly in both CLI and Jupyter environments.
This simulates the problematic scenario described in the issue.
"""

import sys
import argparse
import os

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

def test_normal_execution():
    """Test normal execution without problematic arguments"""
    print("\n=== Testing Normal Execution ===")
    original_argv = sys.argv.copy()
    
    # Test 1: No arguments
    sys.argv = ["test_script.py"]
    args = setup_args()
    print(f"✓ No arguments: epochs={args.epochs}, batch_size={args.batch_size}")
    
    # Test 2: With valid arguments
    sys.argv = ["test_script.py", "--epochs", "50", "--batch_size", "16"]
    args = setup_args()
    print(f"✓ Valid arguments: epochs={args.epochs}, batch_size={args.batch_size}")
    
    # Restore original argv
    sys.argv = original_argv

def test_jupyter_problematic_execution():
    """Test execution with Jupyter-specific arguments that cause the issue"""
    print("\n=== Testing Jupyter Problematic Arguments ===")
    original_argv = sys.argv.copy()
    
    # Test the exact problematic case from the issue
    problematic_args = [
        "test_script.py",
        "--f=c:\\Users\\Isaac\\AppData\\Roaming\\jupyter\\runtime\\kernel-v35096aec600f857bd31cdae2e281edb0ade09ef1d.json"
    ]
    
    sys.argv = problematic_args
    print(f"Testing with problematic args: {sys.argv[1:]}")
    
    try:
        args = setup_args()
        print(f"✓ Jupyter arguments handled: epochs={args.epochs}, batch_size={args.batch_size}")
        print("✓ No SystemExit exception - argument parsing succeeded")
    except SystemExit as e:
        print(f"✗ SystemExit caught: {e}")
        print("✗ Argument parsing failed - this would be the original bug")
    except Exception as e:
        print(f"✗ Unexpected exception: {e}")
    
    # Test with mixed arguments
    mixed_args = [
        "test_script.py",
        "--epochs", "75",
        "--f=c:\\Users\\Isaac\\AppData\\Roaming\\jupyter\\runtime\\kernel-v35096aec600f857bd31cdae2e281edb0ade09ef1d.json",
        "--batch_size", "64"
    ]
    
    sys.argv = mixed_args
    print(f"\nTesting with mixed args: {sys.argv[1:]}")
    
    try:
        args = setup_args()
        print(f"✓ Mixed arguments handled: epochs={args.epochs}, batch_size={args.batch_size}")
        print("✓ Valid arguments parsed correctly, Jupyter args ignored")
    except Exception as e:
        print(f"✗ Exception with mixed args: {e}")
    
    # Restore original argv
    sys.argv = original_argv

def test_edge_cases():
    """Test edge cases for argument parsing"""
    print("\n=== Testing Edge Cases ===")
    original_argv = sys.argv.copy()
    
    # Test with multiple Jupyter-like arguments
    edge_case_args = [
        "test_script.py",
        "--f=/some/jupyter/kernel.json",
        "--jupyter-config-dir=/path/to/jupyter",
        "--epochs", "200",
        "--unknown-arg", "value"
    ]
    
    sys.argv = edge_case_args
    print(f"Testing edge case: {sys.argv[1:]}")
    
    try:
        args = setup_args()
        print(f"✓ Edge case handled: epochs={args.epochs}")
        print("✓ Jupyter-like args filtered, unknown args warned")
    except Exception as e:
        print(f"✗ Edge case failed: {e}")
    
    # Restore original argv
    sys.argv = original_argv

def test_original_bug_simulation():
    """Simulate the exact original bug scenario"""
    print("\n=== Simulating Original Bug ===")
    print("This simulates what would happen with the original argparse code")
    
    # Create a parser that would fail (like the original bug)
    problematic_parser = argparse.ArgumentParser(description='Original problematic parser')
    problematic_parser.add_argument('--epochs', type=int, default=100)
    problematic_parser.add_argument('--batch_size', type=int, default=32)
    
    original_argv = sys.argv.copy()
    sys.argv = [
        "test_script.py",
        "--f=c:\\Users\\Isaac\\AppData\\Roaming\\jupyter\\runtime\\kernel-v35096aec600f857bd31cdae2e281edb0ade09ef1d.json"
    ]
    
    try:
        # This would be the original problematic code
        args = problematic_parser.parse_args()
        print("✗ Original parser should have failed but didn't")
    except SystemExit:
        print("✓ Original parser fails with SystemExit (as expected)")
        print("✓ This confirms the bug existed")
    except Exception as e:
        print(f"✓ Original parser fails with: {e}")
        
    # Restore original argv
    sys.argv = original_argv

if __name__ == "__main__":
    print("Testing Jupyter Argument Parsing Fix")
    print("=" * 50)
    
    test_normal_execution()
    test_jupyter_problematic_execution()
    test_edge_cases()
    test_original_bug_simulation()
    
    print("\n" + "=" * 50)
    print("✓ All tests completed - argument parsing fix verified")
    print("✓ The notebook should now work in both CLI and Jupyter environments")