from pydantic import BaseModel


class Surface(BaseModel):
    """
    Describes the application surface where an artifact can run.
    """

    type: str
    vendor: str
    tenant: str
    base_url: str
    version: str