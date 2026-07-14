import uuid as uuid_pkg
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from app.models.institution import Mode

if TYPE_CHECKING:
    from app.models.institution import Institution


class Course(SQLModel, table=True):
    """Course model."""

    id: UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    institution_id: UUID = Field(foreign_key="institution.id", nullable=False)
    course_name: str | None = Field(default=None, max_length=200, nullable=True)
    option_a_bucket: str | None = Field(default=None, max_length=200)
    option_b_bucket: str | None = Field(default=None, max_length=200)
    option_c_bucket: str | None = Field(default=None, max_length=200)
    option_d_bucket: str | None = Field(default=None, max_length=200)
    cbcs: bool | None = Field(default=None, nullable=True)
    revised_intake: int | None = Field(default=None)
    mode: Mode | None = Field(default=None, nullable=True)

    institution: Optional["Institution"] = Relationship(
        back_populates="courses"
    )

    @property
    def name(self) -> str:
        """Compute a display name from course details."""
        parts = []
        for part in [
            self.course_name,
            self.option_a_bucket,
            self.option_b_bucket,
            self.option_c_bucket,
            self.option_d_bucket,
        ]:
            if part:
                parts.append(part)
        return " ".join(parts) if parts else ""
