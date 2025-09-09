#!/usr/bin/env python
# coding: utf-8

# # Neural Network Training for Gymnastics Scheduling Optimization
# 
# This notebook trains neural network models to optimize gymnastics class scheduling using historical data and constraints.

# In[1]:


# Import libraries
import sys
import argparse
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Check if running in Jupyter notebook
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

# Setup argument parsing with Jupyter compatibility
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

# Initialize arguments
args = setup_args()
print(f"Training configuration:")
print(f"  Data path: {args.data_path}")
print(f"  Model output: {args.model_output}")
print(f"  Epochs: {args.epochs}")
print(f"  Batch size: {args.batch_size}")
print(f"  Learning rate: {args.learning_rate}")
print(f"  Verbose: {args.verbose}")


# In[2]:


# Create output directory if it doesn't exist
os.makedirs(args.model_output, exist_ok=True)
print(f"Model output directory: {os.path.abspath(args.model_output)}")


# In[3]:


# Import application modules (if available)
try:
    # Add application to path
    sys.path.append(os.path.abspath(args.data_path))

    # Import application components
    from data_processor import DataDrivenProcessor
    from enhanced_scheduler import EnhancedStrictConstraintScheduler

    print("Successfully imported application modules")
    APP_AVAILABLE = True

except ImportError as e:
    print(f"Could not import application modules: {e}")
    print("Will use synthetic data for demonstration")
    APP_AVAILABLE = False


# In[4]:


# Define neural network model components
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, optimizers
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import classification_report, confusion_matrix

    print(f"Using TensorFlow version: {tf.__version__}")
    TF_AVAILABLE = True

except ImportError:
    print("TensorFlow not available, installing...")
    get_ipython().system('pip install tensorflow scikit-learn')

    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, optimizers
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import classification_report, confusion_matrix

    TF_AVAILABLE = True


# In[5]:


# Data loading and preparation
def load_training_data():
    """Load and prepare training data"""

    if APP_AVAILABLE:
        print("Loading data from application...")
        try:
            # Initialize data processor
            processor = DataDrivenProcessor()
            data = processor.load_and_process_data()

            # Extract features for training
            features = []
            labels = []

            # Process feasible assignments as training examples
            for assignment in data['feasible_assignments']:
                # Feature vector: coach_id, level_encoded, day_encoded, time_encoded, branch_encoded
                feature = [
                    assignment['coach_id'],
                    hash(assignment['level']) % 1000,  # Simple encoding
                    hash(assignment['day']) % 7,
                    int(assignment['start_time'].replace(':', '')) / 2400,  # Normalize time
                    hash(assignment['branch']) % 100,
                    assignment['duration'] / 120,  # Normalize duration
                    assignment['capacity'] / 10,   # Normalize capacity
                ]
                features.append(feature)

                # Label: 1 if popular timeslot, 0 otherwise
                labels.append(1 if assignment['is_popular'] else 0)

            return np.array(features), np.array(labels), data

        except Exception as e:
            print(f"Error loading application data: {e}")
            print("Falling back to synthetic data")

    # Generate synthetic data for demonstration
    print("Generating synthetic training data...")
    np.random.seed(42)

    n_samples = 1000
    n_features = 7

    # Generate random features
    features = np.random.randn(n_samples, n_features)

    # Generate labels based on simple rules (simulation)
    labels = np.random.choice([0, 1], size=n_samples, p=[0.3, 0.7])  # More popular slots

    return features, labels, None

# Load the data
X, y, app_data = load_training_data()
print(f"Loaded training data: {X.shape[0]} samples, {X.shape[1]} features")
print(f"Label distribution: {np.bincount(y)}")


# In[6]:


# Prepare data for training
def prepare_data(X, y, test_size=0.2, random_state=42):
    """Prepare data for neural network training"""

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    if args.verbose:
        print(f"Training set: {X_train_scaled.shape}")
        print(f"Test set: {X_test_scaled.shape}")
        print(f"Feature scaling applied")

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler

# Prepare the data
X_train, X_test, y_train, y_test, scaler = prepare_data(X, y)
print(f"Data preparation complete")


# In[7]:


# Define neural network architecture
def create_scheduling_model(input_dim, learning_rate=0.001):
    """Create neural network model for scheduling optimization"""

    model = models.Sequential([
        layers.Dense(128, activation='relu', input_shape=(input_dim,)),
        layers.Dropout(0.3),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(32, activation='relu'),
        layers.Dense(1, activation='sigmoid')  # Binary classification
    ])

    # Compile model
    model.compile(
        optimizer=optimizers.Adam(learning_rate=learning_rate),
        loss='binary_crossentropy',
        metrics=['accuracy', 'precision', 'recall']
    )

    if args.verbose:
        model.summary()

    return model

# Create the model
model = create_scheduling_model(X_train.shape[1], args.learning_rate)
print("Neural network model created")


# In[8]:


# Define callbacks for training
callbacks = [
    keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True,
        verbose=1 if args.verbose else 0
    ),
    keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        min_lr=1e-7,
        verbose=1 if args.verbose else 0
    )
]

print("Training callbacks configured")


# In[9]:


# Train the model
print(f"Starting training for {args.epochs} epochs...")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

history = model.fit(
    X_train, y_train,
    batch_size=args.batch_size,
    epochs=args.epochs,
    validation_data=(X_test, y_test),
    callbacks=callbacks,
    verbose=1 if args.verbose else 0
)

print(f"Training completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# In[10]:


# Evaluate the model
print("Evaluating model performance...")

# Get predictions
y_pred = model.predict(X_test, verbose=0)
y_pred_binary = (y_pred > 0.5).astype(int).flatten()

# Calculate metrics
test_loss, test_accuracy, test_precision, test_recall = model.evaluate(X_test, y_test, verbose=0)

print(f"\nTest Results:")
print(f"  Loss: {test_loss:.4f}")
print(f"  Accuracy: {test_accuracy:.4f}")
print(f"  Precision: {test_precision:.4f}")
print(f"  Recall: {test_recall:.4f}")

# Detailed classification report
if args.verbose:
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred_binary))

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred_binary))


# In[11]:


# Save the trained model and scaler
model_path = os.path.join(args.model_output, 'scheduling_model.h5')
scaler_path = os.path.join(args.model_output, 'feature_scaler.pkl')
metadata_path = os.path.join(args.model_output, 'model_metadata.txt')

# Save model
model.save(model_path)
print(f"Model saved to: {model_path}")

# Save scaler
import pickle
with open(scaler_path, 'wb') as f:
    pickle.dump(scaler, f)
print(f"Scaler saved to: {scaler_path}")

# Save metadata
with open(metadata_path, 'w') as f:
    f.write(f"Model Training Metadata\n")
    f.write(f"======================\n")
    f.write(f"Training Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Training Samples: {len(X_train)}\n")
    f.write(f"Test Samples: {len(X_test)}\n")
    f.write(f"Features: {X_train.shape[1]}\n")
    f.write(f"Epochs: {args.epochs}\n")
    f.write(f"Batch Size: {args.batch_size}\n")
    f.write(f"Learning Rate: {args.learning_rate}\n")
    f.write(f"\nPerformance:\n")
    f.write(f"Test Accuracy: {test_accuracy:.4f}\n")
    f.write(f"Test Precision: {test_precision:.4f}\n")
    f.write(f"Test Recall: {test_recall:.4f}\n")
    f.write(f"Test Loss: {test_loss:.4f}\n")

print(f"Metadata saved to: {metadata_path}")


# In[12]:


# Training summary
print("\n" + "="*60)
print("TRAINING SUMMARY")
print("="*60)
print(f"Environment: {'Jupyter Notebook' if is_jupyter_notebook() else 'CLI'}")
print(f"Data Source: {'Application Data' if APP_AVAILABLE and app_data else 'Synthetic Data'}")
print(f"Training completed successfully!")
print(f"")
print(f"Model Performance:")
print(f"  - Accuracy: {test_accuracy:.1%}")
print(f"  - Precision: {test_precision:.1%}")
print(f"  - Recall: {test_recall:.1%}")
print(f"")
print(f"Files saved:")
print(f"  - Model: {model_path}")
print(f"  - Scaler: {scaler_path}")
print(f"  - Metadata: {metadata_path}")
print("="*60)

# Display training history if available
if args.verbose and 'history' in locals():
    try:
        import matplotlib.pyplot as plt

        # Plot training history
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        # Plot accuracy
        ax1.plot(history.history['accuracy'], label='Training Accuracy')
        ax1.plot(history.history['val_accuracy'], label='Validation Accuracy')
        ax1.set_title('Model Accuracy')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Accuracy')
        ax1.legend()

        # Plot loss
        ax2.plot(history.history['loss'], label='Training Loss')
        ax2.plot(history.history['val_loss'], label='Validation Loss')
        ax2.set_title('Model Loss')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Loss')
        ax2.legend()

        plt.tight_layout()
        plt.show()

    except ImportError:
        print("Matplotlib not available for plotting training history")
    except Exception as e:
        print(f"Could not plot training history: {e}")

