import logging
from langchain_core.tools import BaseTool

class ToolBase(BaseTool):
    logger:logging.Logger = logging.getLogger(name=__name__)