from pydantic import BaseModel, Field

class FileDependency(BaseModel):
    internal_deps: list[str] = Field(..., description="List of internal file dependencies (relative paths).")
    external_deps: list[str] = Field(..., description="List of external dependencies (e.g., libraries).")