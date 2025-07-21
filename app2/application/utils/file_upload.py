"""
File upload handling utilities for CSV data import.
"""
import os
import pandas as pd
from werkzeug.utils import secure_filename
from typing import Dict, List, Tuple, Optional
from flask import current_app


class FileUploadHandler:
    """Handle file uploads and validation for CSV data."""
    
    ALLOWED_EXTENSIONS = {'csv'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    def __init__(self, upload_folder='/tmp/uploads'):
        """Initialize with upload folder."""
        self.upload_folder = upload_folder
        self.ensure_upload_folder()
    
    def ensure_upload_folder(self):
        """Create upload folder if it doesn't exist."""
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        return ('.' in filename and 
                filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS)
    
    def validate_file_size(self, file) -> bool:
        """Validate file size."""
        # Reset file position to get accurate size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)  # Reset position for later reading
        return size <= self.MAX_FILE_SIZE
    
    def save_uploaded_file(self, file, filename: str) -> str:
        """Save uploaded file and return filepath."""
        if not self.allowed_file(filename):
            raise ValueError(f"File type not allowed: {filename}")
        
        if not self.validate_file_size(file):
            raise ValueError("File size exceeds 5MB limit")
        
        secure_name = secure_filename(filename)
        filepath = os.path.join(self.upload_folder, secure_name)
        file.save(filepath)
        return filepath
    
    def validate_csv_structure(self, filepath: str, expected_columns: List[str]) -> Tuple[bool, str, Optional[pd.DataFrame]]:
        """
        Validate CSV structure and return validation result.
        
        Returns:
            Tuple of (is_valid, message, dataframe)
        """
        try:
            df = pd.read_csv(filepath)
            
            # Check if file is empty
            if df.empty:
                return False, "CSV file is empty", None
            
            # Check for required columns
            missing_columns = set(expected_columns) - set(df.columns)
            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}", None
            
            # Check for completely empty rows
            if df.isnull().all(axis=1).any():
                return False, "CSV contains completely empty rows", None
            
            return True, "CSV structure is valid", df
            
        except pd.errors.EmptyDataError:
            return False, "CSV file is empty or corrupted", None
        except pd.errors.ParserError as e:
            return False, f"CSV parsing error: {str(e)}", None
        except Exception as e:
            return False, f"Error reading CSV: {str(e)}", None
    
    def preview_csv_data(self, filepath: str, max_rows: int = 10) -> Dict:
        """Generate preview data for CSV file."""
        try:
            df = pd.read_csv(filepath)
            
            preview_data = {
                'columns': df.columns.tolist(),
                'total_rows': len(df),
                'sample_data': df.head(max_rows).to_dict('records'),
                'data_types': df.dtypes.to_dict()
            }
            
            return preview_data
            
        except Exception as e:
            return {'error': f"Error previewing CSV: {str(e)}"}
    
    def get_coaches_csv_columns(self) -> List[str]:
        """Get expected columns for coaches CSV."""
        return [
            'coach_name', 'residential_area', 'assigned_branch', 
            'position', 'status', 'BearyTots', 'Jolly', 'Bubbly', 
            'Lively', 'Flexi', 'Level_1', 'Level_2', 'Level_3', 
            'Level_4', 'Advance', 'Free'
        ]
    
    def get_availability_csv_columns(self) -> List[str]:
        """Get expected columns for availability CSV."""
        return ['coach_name', 'day', 'period', 'available']
    
    def get_enrollment_csv_columns(self) -> List[str]:
        """Get expected columns for enrollment CSV."""
        return ['Branch', 'Level Category Base', 'Count']
    
    def get_branch_config_csv_columns(self) -> List[str]:
        """Get expected columns for branch configuration CSV."""
        return ['branch', 'max_classes_per_slot']
    
    def cleanup_file(self, filepath: str):
        """Remove uploaded file after processing."""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            current_app.logger.warning(f"Could not cleanup file {filepath}: {e}")


class CSVDataProcessor:
    """Process CSV data for import into database."""
    
    def __init__(self):
        """Initialize the processor."""
        pass
    
    def process_coaches_csv(self, df: pd.DataFrame) -> List[Dict]:
        """Process coaches CSV data into database format."""
        coaches_data = []
        
        for _, row in df.iterrows():
            coach_data = {
                'name': str(row['coach_name']).strip(),
                'residential_area': str(row['residential_area']).strip(),
                'position': str(row['position']).strip(),
                'status': str(row['status']).strip(),
                'assigned_branches': [str(row['assigned_branch']).strip()] if pd.notna(row['assigned_branch']) else [],
                'preferred_levels': []
            }
            
            # Extract level preferences
            level_mapping = {
                'BearyTots': 'Tots', 'Jolly': 'Jolly', 'Bubbly': 'Bubbly',
                'Lively': 'Lively', 'Flexi': 'Flexi', 'Level_1': 'L1',
                'Level_2': 'L2', 'Level_3': 'L3', 'Level_4': 'L4',
                'Advance': 'Advance', 'Free': 'Free'
            }
            
            for csv_col, level_name in level_mapping.items():
                if csv_col in row and pd.notna(row[csv_col]) and row[csv_col]:
                    coach_data['preferred_levels'].append(level_name)
            
            coaches_data.append(coach_data)
        
        return coaches_data
    
    def process_availability_csv(self, df: pd.DataFrame) -> List[Dict]:
        """Process availability CSV data into database format."""
        availability_data = []
        
        day_mapping = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
        
        for _, row in df.iterrows():
            coach_name = str(row['coach_name']).strip()
            day_name = str(row['day']).strip().upper()
            period = str(row['period']).strip().upper()
            available = bool(row['available']) if pd.notna(row['available']) else True
            
            if day_name in day_mapping:
                availability_data.append({
                    'coach_name': coach_name,
                    'day': day_mapping[day_name],
                    'am': period == 'AM',
                    'available': available
                })
        
        return availability_data
    
    def process_enrollment_csv(self, df: pd.DataFrame) -> List[Dict]:
        """Process enrollment CSV data."""
        enrollment_data = []
        
        for _, row in df.iterrows():
            enrollment_data.append({
                'branch': str(row['Branch']).strip(),
                'level': str(row['Level Category Base']).strip(),
                'count': int(row['Count']) if pd.notna(row['Count']) else 0
            })
        
        return enrollment_data
    
    def process_branch_config_csv(self, df: pd.DataFrame) -> List[Dict]:
        """Process branch configuration CSV data."""
        branch_config_data = []
        
        for _, row in df.iterrows():
            branch_config_data.append({
                'branch': str(row['branch']).strip(),
                'max_classes': int(row['max_classes_per_slot']) if pd.notna(row['max_classes_per_slot']) else 4
            })
        
        return branch_config_data