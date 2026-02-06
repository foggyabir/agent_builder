from pathlib import Path
from typing import Optional, Tuple, Union

def is_path_safe(working_directory:Union[str, Path], user_path: Union[str, Path]) -> Tuple[bool, Optional[Path]]:
        """
        Checks if a user-provided path is safe and returns the safety status 
        and the resolved Path object.
        
        Returns: (is_safe: bool, resolved_path: Path | None)
        """
        try:
            if isinstance(user_path, str):
                user_path_obj = Path(user_path)
            elif isinstance(user_path, Path):
                user_path_obj = user_path
            else:
                return False, None
        except Exception:
            return False, None
        
        if user_path_obj.is_absolute():
            return False, None
        
        try:
            full_path = (working_directory / user_path_obj).resolve(strict=False)
            is_safe = full_path.is_relative_to(working_directory)
            
            if is_safe:
                return True, full_path
            else:
                return False, None
                
        except Exception:
            return False, None