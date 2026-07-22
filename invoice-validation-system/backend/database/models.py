from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from .core import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True)  # e.g. "Supply" or "Repair"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="PENDING")

    documents = relationship("Document", back_populates="project")
    validation_results = relationship("ValidationResult", back_populates="project")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    document_type = Column(String, index=True)
    file_name = Column(String)
    file_path = Column(String)

    project = relationship("Project", back_populates="documents")


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    rule_name = Column(String)
    status = Column(String)  # e.g., "PASS" or "FAIL"
    message = Column(String)

    project = relationship("Project", back_populates="validation_results")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    field_name = Column(String, index=True)
    field_value = Column(String, index=True)
    page = Column(Integer)
    bbox_x1 = Column(Integer)
    bbox_y1 = Column(Integer)
    bbox_x2 = Column(Integer)
    bbox_y2 = Column(Integer)

    document = relationship("Document")
    project = relationship("Project")
