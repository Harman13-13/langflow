from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from pydantic import field_serializer, field_validator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langflow.services.database.models.flow.model import Flow


class TransactionBase(SQLModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vertex_id: str = Field(nullable=False)
    target_id: Optional[str] = Field(default=None)
    inputs: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    outputs: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    status: str = Field(nullable=False)
    error: Optional[str] = Field(default=None)
    flow_id: UUID = Field(foreign_key="flow.id")

    # Needed for Column(JSON)
    class Config:
        arbitrary_types_allowed = True

    @field_validator("flow_id", mode="before")
    @classmethod
    def validate_flow_id(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            value = UUID(value)
        return value

    @field_serializer("outputs")
    def serialize_outputs(self, data) -> dict:
        paths_to_truncate = [
            (['artifacts', 'data', 'raw'], 'text'),

            (['artifacts', 'text'], 'raw'),
            (['artifacts', 'text'], 'repr'),

            (['artifacts', 'prompt'], 'raw'),
            (['artifacts', 'prompt'], 'repr'),

            (['artifacts', 'data'], 'repr'),

            (['message', 'text'], 'raw'),
            (['message', 'text'], 'repr'),
            (['messsage', 'data', 'raw'], 'text'),

            (['outputs', 'data', 'message'], 'text'),
            (['outputs', 'text'], 'message'),
            (['outputs', 'prompt'], 'message'),
        ]

        for path, key in paths_to_truncate:
            truncate_text(data, path, key)

        return data

class TransactionTable(TransactionBase, table=True):  # type: ignore
    __tablename__ = "transaction"
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    flow: "Flow" = Relationship(back_populates="transactions")


class TransactionReadResponse(TransactionBase):
    transaction_id: UUID
    flow_id: UUID


def truncate_text(data, path: list, key: str):
    """Helper function to safely truncate text in nested dictionaries."""
    target = data
    for p in path:
        if not isinstance(target, dict) or p not in target:
            return  # Exit if path is invalid
        target = target[p]

    if key in target and isinstance(target[key], str):
        target[key] = target[key][:10]
