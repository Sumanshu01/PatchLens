"""SQLAlchemy 2.0 ORM models for PatchLens analysis persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


class BinaryRecord(Base):
    """Represents an uploaded ELF binary on disk."""

    __tablename__ = "binaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    arch: Mapped[str] = mapped_column(String(32), default="x86_64")
    is_stripped: Mapped[bool] = mapped_column(Boolean, default=True)
    entry_point: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (Index("idx_binary_sha256", "sha256"),)


class AnalysisJob(Base):
    """Tracks asynchronous execution state and streaming progress for an analysis."""

    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_stage: Mapped[str] = mapped_column(String(64), default="queued")
    stage_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    binary_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("binaries.id"), nullable=False)
    binary_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("binaries.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    binary_a: Mapped[BinaryRecord] = relationship("BinaryRecord", foreign_keys=[binary_a_id])
    binary_b: Mapped[BinaryRecord] = relationship("BinaryRecord", foreign_keys=[binary_b_id])


class AnalysisResultRecord(Base):
    """Stores full diffing and security patch ranking results keyed by binary pair hash."""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("analysis_jobs.id"), nullable=True
    )
    pair_hash: Mapped[str] = mapped_column(String(130), unique=True, index=True, nullable=False)

    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    ranked_diffs_json: Mapped[str] = mapped_column(Text, nullable=False)
    callgraph_json: Mapped[str] = mapped_column(Text, default="{}")
    details_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
