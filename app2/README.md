# Flask Timetabling Application

A Flask web application for generating and managing gym class timetables with optimization algorithms.

## Features

- User authentication and management
- Branch and level management
- Coach scheduling and preferences
- Optimized timetable generation
- Data upload and processing

## Requirements

- Python 3.8+
- Virtual environment (recommended)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd fyp/app2
```

### 2. Create and activate virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy the example environment file and configure as needed:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration settings.

### 5. Initialize the database

```bash
python init_db.py
```

### 6. Run the application

```bash
python main.py
```

The application will be available at `http://localhost:5000`

## Development

### Running tests

```bash
pytest
```

### Code formatting

```bash
black application/
```

### Code linting

```bash
flake8 application/
```

## Project Structure

```
app2/
├── application/           # Main application package
│   ├── __init__.py       # App factory
│   ├── config.cfg        # Configuration file
│   ├── models.py         # Database models
│   ├── forms.py          # WTForms
│   ├── routes/           # Route blueprints
│   ├── services/         # Business logic services
│   ├── utils/            # Utility functions
│   ├── static/           # Static files (CSS, JS)
│   └── templates/        # Jinja2 templates
├── instance/             # Instance-specific files
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Configuration

The application uses Flask's configuration system. Key settings are in `application/config.cfg`:

- `SECRET_KEY`: Flask secret key for sessions
- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `DEBUG`: Enable/disable debug mode

## Database

The application uses SQLite by default. The database file is created automatically when you run the initialization script.

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Ensure you've activated your virtual environment and installed all requirements
2. **Database errors**: Run the database initialization script
3. **Port conflicts**: Change the port in `main.py` if 5000 is already in use

### Getting Help

If you encounter issues:

1. Check the console output for error messages
2. Ensure all dependencies are installed correctly
3. Verify your Python version is 3.8+
4. Check that your virtual environment is activated