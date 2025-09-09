# Neural Network Training for Gymnastics Scheduling

## Overview

The `NN_train.ipynb` notebook trains neural network models to optimize gymnastics class scheduling using historical data and constraints. This notebook is designed to work seamlessly in both Jupyter notebook environments and command-line execution.

## Key Features

### Jupyter Compatibility Fix

The notebook includes a comprehensive fix for the common Jupyter argument parsing issue:

- **Problem**: Jupyter kernels pass arguments like `--f=path/to/kernel.json` which cause `argparse` to fail with "unrecognized arguments" error
- **Solution**: Smart argument parsing that detects the execution environment and handles Jupyter-specific arguments gracefully

### Argument Parsing

The notebook supports the following command-line arguments:

- `--data_path`: Path to data directory (default: `./application`)
- `--model_output`: Directory to save trained models (default: `./models`)
- `--epochs`: Number of training epochs (default: 100)
- `--batch_size`: Training batch size (default: 32)
- `--learning_rate`: Learning rate (default: 0.001)
- `--verbose`: Enable verbose output (default: True)

### Environment Detection

The notebook automatically detects whether it's running in:
- Jupyter notebook environment (uses default parameters)
- Command-line interface (parses arguments with Jupyter compatibility)

## Usage

### In Jupyter Notebook

Simply run all cells in the notebook. The argument parsing will automatically use default values.

### From Command Line

```bash
# Use defaults
python NN_train.ipynb  # (after converting to .py)

# Custom parameters
python NN_train.py --epochs 200 --batch_size 64 --learning_rate 0.0005
```

### Converting and Running

```bash
# Convert notebook to Python script
jupyter nbconvert --to python NN_train.ipynb

# Execute the notebook
jupyter nbconvert --execute NN_train.ipynb

# Run with custom arguments (after conversion)
python NN_train.py --epochs 150
```

## Technical Details

### Jupyter Argument Handling

The fix uses several techniques to handle Jupyter arguments:

1. **Environment Detection**: Uses `get_ipython()` to detect Jupyter environment
2. **Graceful Parsing**: Uses `parse_known_args()` instead of `parse_args()` 
3. **Argument Filtering**: Filters out Jupyter-specific arguments (those starting with `--f=`, containing 'kernel', or 'jupyter')
4. **Fallback Mechanism**: Falls back to defaults if argument parsing fails

### Error Prevention

The solution prevents these common Jupyter errors:
- `SystemExit: 2` from unrecognized arguments
- `error: unrecognized arguments: --f=...` messages
- Notebook execution failures due to argument parsing

## Model Output

The notebook generates:
- `scheduling_model.h5`: Trained neural network model
- `feature_scaler.pkl`: Feature scaling parameters
- `model_metadata.txt`: Training metadata and performance metrics

## Dependencies

Required packages:
- `tensorflow` (or will be installed automatically)
- `scikit-learn`
- `pandas`
- `numpy`
- `matplotlib` (optional, for plotting)

## Architecture

The neural network uses:
- Input layer matching the feature dimensions
- Hidden layers: 128 → 64 → 32 neurons with ReLU activation
- Dropout layers (0.3) for regularization
- Output layer with sigmoid activation for binary classification
- Adam optimizer with configurable learning rate

## Integration

This notebook is designed to integrate with the gymnastics scheduling system:
- Loads data from the application's data processor
- Trains models to predict popular timeslots
- Saves models for use in the enhanced scheduler
- Supports both synthetic and real application data