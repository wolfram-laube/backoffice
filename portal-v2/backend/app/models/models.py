"""
Database Models
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))
    gitlab_id = Column(String(100), unique=True, index=True)
    avatar_url = Column(String(500))
    role = Column(String(50), default="user")  # admin, user, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    timesheets = relationship("Timesheet", back_populates="user")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    company = Column(String(255))
    email = Column(String(255))
    address = Column(Text)
    hourly_rate = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    projects = relationship("Project", back_populates="customer")
    timesheets = relationship("Timesheet", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    hourly_rate = Column(Float)  # Override customer rate if set
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="projects")
    timesheets = relationship("Timesheet", back_populates="project")


class Timesheet(Base):
    __tablename__ = "timesheets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"))
    date = Column(Date, nullable=False)
    hours = Column(Float, nullable=False)
    description = Column(Text)
    hourly_rate = Column(Float)  # Rate at time of entry
    is_billable = Column(Boolean, default=True)
    is_invoiced = Column(Boolean, default=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="timesheets")
    customer = relationship("Customer", back_populates="timesheets")
    project = relationship("Project", back_populates="timesheets")
    invoice = relationship("Invoice", back_populates="timesheets")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date)
    subtotal = Column(Float, default=0)
    tax_rate = Column(Float, default=20)  # Austrian VAT 20%
    tax_amount = Column(Float, default=0)
    total = Column(Float, default=0)
    status = Column(String(50), default="draft")  # draft, sent, paid, cancelled
    pdf_url = Column(String(500))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    timesheets = relationship("Timesheet", back_populates="invoice")
