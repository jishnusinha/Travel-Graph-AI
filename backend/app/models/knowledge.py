"""Terra knowledge corpus tables. Shared across users. User-owned rows enforce user_id."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UTCDateTime as DateTime


def _uuid() -> str:
    return str(uuid4())


class Destination(Base, TimestampMixin):
    __tablename__ = "destinations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="city")
    aliases: Mapped[list[Any]] = mapped_column(JSON, default=list)
    region: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(120), default="India")
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coordinate_status: Mapped[str] = mapped_column(String(64), default="unknown")
    wikidata_qid: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    wikivoyage_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    wikipedia_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    osm_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    osm_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    cover_image_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    themes: Mapped[list[Any]] = mapped_column(JSON, default=list)
    source_status: Mapped[str] = mapped_column(String(64), default="pending")


class Attraction(Base, TimestampMixin):
    __tablename__ = "attractions"
    __table_args__ = (UniqueConstraint("destination_id", "name", name="uq_attraction_dest_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="poi")
    aliases: Mapped[list[Any]] = mapped_column(JSON, default=list)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geometry_kind: Mapped[str] = mapped_column(String(32), default="point")
    osm_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    osm_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    coordinate_status: Mapped[str] = mapped_column(String(64), default="unknown")
    source_refs: Mapped[list[Any]] = mapped_column(JSON, default=list)


class KnowledgeSnapshot(Base, TimestampMixin):
    __tablename__ = "knowledge_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    manifest_checksum: Mapped[str] = mapped_column(String(64), default="")
    state: Mapped[str] = mapped_column(String(16), default="staged", index=True)
    embedding_model: Mapped[str] = mapped_column(String(200), default="")
    embedding_revision: Mapped[str] = mapped_column(String(64), default="")
    embedding_dim: Mapped[int] = mapped_column(Integer, default=0)
    embedding_kind: Mapped[str] = mapped_column(String(64), default="unavailable")
    corpus_version: Mapped[str] = mapped_column(String(64), default="")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "source_type", "revision_id", "title", name="uq_doc_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("knowledge_snapshots.id", ondelete="CASCADE"), index=True)
    destination_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    page_id: Mapped[str] = mapped_column(String(64), default="")
    revision_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    canonical_url: Mapped[str] = mapped_column(String(500), default="")
    permalink: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    license_name: Mapped[str] = mapped_column(String(200), default="")
    credit: Mapped[str] = mapped_column(Text, default="")
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeChunk(Base, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("knowledge_snapshots.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True)
    section_path: Mapped[str] = mapped_column(String(300), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    start_offset: Mapped[int] = mapped_column(Integer, default=0)
    end_offset: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    topic: Mapped[str] = mapped_column(String(64), default="")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ChunkDestination(Base):
    __tablename__ = "chunk_destinations"
    __table_args__ = (UniqueConstraint("chunk_id", "destination_id", name="uq_chunk_dest"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), index=True)


class DestinationImage(Base, TimestampMixin):
    __tablename__ = "destination_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), index=True)
    snapshot_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    local_path: Mapped[str] = mapped_column(String(500), default="")
    author: Mapped[str] = mapped_column(String(300), default="")
    license_name: Mapped[str] = mapped_column(String(200), default="")
    license_url: Mapped[str] = mapped_column(String(500), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    alt: Mapped[str] = mapped_column(String(300), default="")
    attribution: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")


class TravelCostEstimate(Base, TimestampMixin):
    __tablename__ = "travel_cost_estimates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), index=True)
    snapshot_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    low_inr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    high_inr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    basis: Mapped[str] = mapped_column(String(32), default="per_person")
    origin: Mapped[str] = mapped_column(String(120), default="")
    season: Mapped[str] = mapped_column(String(64), default="")
    method: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String(32), default="low")
    checked_at: Mapped[str] = mapped_column(String(32), default="")


class KnowledgeEntity(Base, TimestampMixin):
    __tablename__ = "knowledge_entities"
    __table_args__ = (UniqueConstraint("snapshot_id", "external_key", name="uq_entity_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    snapshot_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    external_key: Mapped[str] = mapped_column(String(200), default="")
    aliases: Mapped[list[Any]] = mapped_column(JSON, default=list)
    ref_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class KnowledgeRelationship(Base, TimestampMixin):
    __tablename__ = "knowledge_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    snapshot_id: Mapped[str] = mapped_column(String(64), index=True)
    subject_id: Mapped[str] = mapped_column(String(36), index=True)
    predicate: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), index=True)
    evidence_chunk_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    method: Mapped[str] = mapped_column(String(64), default="")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class IngestionRun(Base, TimestampMixin):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    snapshot_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    failures: Mapped[list[Any]] = mapped_column(JSON, default=list)


class SavedDestination(Base, TimestampMixin):
    __tablename__ = "saved_destinations"
    __table_args__ = (UniqueConstraint("user_id", "destination_id", name="uq_saved_dest"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), index=True)


class RetrievalRun(Base, TimestampMixin):
    __tablename__ = "retrieval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    node_id: Mapped[str] = mapped_column(String(64), default="")
    query_redacted: Mapped[str] = mapped_column(Text, default="")
    intent: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    snapshot_id: Mapped[str] = mapped_column(String(64), default="")
    strategy_requested: Mapped[str] = mapped_column(String(64), default="")
    strategy_applied: Mapped[str] = mapped_column(String(64), default="")
    config_hash: Mapped[str] = mapped_column(String(64), default="")
    timings_ms: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    warnings: Mapped[list[Any]] = mapped_column(JSON, default=list)


class RetrievalHitRow(Base, TimestampMixin):
    __tablename__ = "retrieval_hits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    retrieval_run_id: Mapped[str] = mapped_column(ForeignKey("retrieval_runs.id", ondelete="CASCADE"), index=True)
    chunk_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(32), default="")
    rank: Mapped[int] = mapped_column(Integer, default=0)
    raw_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_kind: Mapped[str] = mapped_column(String(32), default="")
    chosen: Mapped[int] = mapped_column(Integer, default=0)
    rejection_reason: Mapped[str] = mapped_column(String(120), default="")


class Citation(Base, TimestampMixin):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    snapshot_id: Mapped[str] = mapped_column(String(64), index=True)
    chunk_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    section_path: Mapped[str] = mapped_column(String(300), default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    permalink: Mapped[str] = mapped_column(String(500), default="")
    license_name: Mapped[str] = mapped_column(String(200), default="")
    source_type: Mapped[str] = mapped_column(String(64), default="")
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    trip_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    retrieval_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
