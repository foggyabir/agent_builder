from pydantic import BaseModel, Field

class FileDependency(BaseModel):
    target_file_path: str = Field(..., description="File path which you are going to analyze.")
    internal_deps: list[str] = Field(..., description="List of internal file dependencies (relative paths).")
    external_deps: list[str] = Field(..., description="List of external dependencies (e.g., libraries).")
    type_of_file:str = Field(..., description="What this file represents in terms of architecture, e.g.: Bootstrap,Component,EntryComponent,Service,Module,Routing,Guard,Resolver,Interceptor,Pipe,Directive,DynamicLoader,State,Facade,Model,Interface,Enum,InjectionToken,LegacyHttp,Adapter,Utility,Constant,Environment,Initializer,Barrel,Metadata,LibraryEntry,Polyfill,Platform,Renderer,ChangeDetection,Spec,Mock,TestSetup,SystemConfig,Html,Css,Other")
    name:str = Field(..., description="Name of the architectural component such as name of the component/service etc.")