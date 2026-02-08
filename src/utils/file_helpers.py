"""
File Helper Utilities
Common file operations and utilities
"""
from pathlib import Path
import json
import yaml
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def load_yaml(filepath: Path) -> Dict[str, Any]:
    """
    Load YAML configuration file
    
    Args:
        filepath: Path to YAML file
        
    Returns:
        Dictionary with configuration
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(data: Dict[str, Any], filepath: Path) -> None:
    """
    Save data to YAML file
    
    Args:
        data: Data to save
        filepath: Path to save to
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_json(filepath: Path) -> Any:
    """
    Load JSON file
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Loaded data
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, filepath: Path, indent: int = 2) -> None:
    """
    Save data to JSON file
    
    Args:
        data: Data to save
        filepath: Path to save to
        indent: JSON indentation
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def ensure_dir(directory: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        directory: Directory path
        
    Returns:
        The directory path
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_client_data_dir(client_name: str, base_dir: Optional[Path] = None) -> Path:
    """
    Get the data directory for a specific client
    
    Args:
        client_name: Name of the client
        base_dir: Base data directory (default: ./data)
        
    Returns:
        Path to client's data directory
    """
    if base_dir is None:
        base_dir = Path('data')
    
    client_dir = base_dir / client_name
    ensure_dir(client_dir)
    
    return client_dir


def get_client_raw_dir(client_name: str, base_dir: Optional[Path] = None) -> Path:
    """
    Get the raw data directory for a specific client
    
    Args:
        client_name: Name of the client
        base_dir: Base data directory
        
    Returns:
        Path to client's raw data directory
    """
    client_dir = get_client_data_dir(client_name, base_dir)
    raw_dir = client_dir / 'raw'
    ensure_dir(raw_dir)
    
    return raw_dir


def get_client_analyzed_dir(client_name: str, base_dir: Optional[Path] = None) -> Path:
    """
    Get the analyzed data directory for a specific client
    
    Args:
        client_name: Name of the client
        base_dir: Base data directory
        
    Returns:
        Path to client's analyzed data directory
    """
    client_dir = get_client_data_dir(client_name, base_dir)
    analyzed_dir = client_dir / 'analyzed'
    ensure_dir(analyzed_dir)
    
    return analyzed_dir


def list_clients(base_dir: Optional[Path] = None) -> list:
    """
    List all client directories
    
    Args:
        base_dir: Base data directory
        
    Returns:
        List of client names
    """
    if base_dir is None:
        base_dir = Path('data')
    
    if not base_dir.exists():
        return []
    
    return [d.name for d in base_dir.iterdir() if d.is_dir()]
