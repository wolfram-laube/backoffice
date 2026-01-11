"""
Timesheets API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

from ..db.database import get_db
from ..models.models import User, Timesheet, Customer, Project
from ..auth.jwt import get_current_user

router = APIRouter()


# Pydantic schemas
class TimesheetCreate(BaseModel):
    customer_id: int
    project_id: Optional[int] = None
    date: date
    hours: float
    description: Optional[str] = None
    hourly_rate: Optional[float] = None
    is_billable: bool = True


class TimesheetUpdate(BaseModel):
    customer_id: Optional[int] = None
    project_id: Optional[int] = None
    date: Optional[date] = None
    hours: Optional[float] = None
    description: Optional[str] = None
    hourly_rate: Optional[float] = None
    is_billable: Optional[bool] = None


class TimesheetResponse(BaseModel):
    id: int
    user_id: int
    customer_id: int
    project_id: Optional[int]
    date: date
    hours: float
    description: Optional[str]
    hourly_rate: Optional[float]
    is_billable: bool
    is_invoiced: bool
    invoice_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class TimesheetSummary(BaseModel):
    total_hours: float
    total_billable_hours: float
    total_amount: float
    entries_count: int


# API Endpoints
@router.get("/", response_model=List[TimesheetResponse])
async def list_timesheets(
    customer_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    is_invoiced: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List timesheets with optional filters"""
    query = db.query(Timesheet)
    
    # Users can only see their own timesheets unless admin
    if current_user.role != "admin":
        query = query.filter(Timesheet.user_id == current_user.id)
    
    if customer_id:
        query = query.filter(Timesheet.customer_id == customer_id)
    if project_id:
        query = query.filter(Timesheet.project_id == project_id)
    if start_date:
        query = query.filter(Timesheet.date >= start_date)
    if end_date:
        query = query.filter(Timesheet.date <= end_date)
    if is_invoiced is not None:
        query = query.filter(Timesheet.is_invoiced == is_invoiced)
    
    return query.order_by(Timesheet.date.desc()).all()


@router.get("/summary", response_model=TimesheetSummary)
async def get_summary(
    customer_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get timesheet summary"""
    query = db.query(Timesheet)
    
    if current_user.role != "admin":
        query = query.filter(Timesheet.user_id == current_user.id)
    
    if customer_id:
        query = query.filter(Timesheet.customer_id == customer_id)
    if start_date:
        query = query.filter(Timesheet.date >= start_date)
    if end_date:
        query = query.filter(Timesheet.date <= end_date)
    
    timesheets = query.all()
    
    total_hours = sum(t.hours for t in timesheets)
    billable = [t for t in timesheets if t.is_billable]
    total_billable = sum(t.hours for t in billable)
    total_amount = sum(t.hours * (t.hourly_rate or 0) for t in billable)
    
    return TimesheetSummary(
        total_hours=total_hours,
        total_billable_hours=total_billable,
        total_amount=total_amount,
        entries_count=len(timesheets)
    )


@router.post("/", response_model=TimesheetResponse)
async def create_timesheet(
    timesheet: TimesheetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new timesheet entry"""
    # Verify customer exists
    customer = db.query(Customer).filter(Customer.id == timesheet.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get hourly rate
    hourly_rate = timesheet.hourly_rate
    if not hourly_rate:
        if timesheet.project_id:
            project = db.query(Project).filter(Project.id == timesheet.project_id).first()
            if project and project.hourly_rate:
                hourly_rate = project.hourly_rate
        if not hourly_rate:
            hourly_rate = customer.hourly_rate
    
    db_timesheet = Timesheet(
        user_id=current_user.id,
        customer_id=timesheet.customer_id,
        project_id=timesheet.project_id,
        date=timesheet.date,
        hours=timesheet.hours,
        description=timesheet.description,
        hourly_rate=hourly_rate,
        is_billable=timesheet.is_billable,
    )
    
    db.add(db_timesheet)
    db.commit()
    db.refresh(db_timesheet)
    return db_timesheet


@router.get("/{timesheet_id}", response_model=TimesheetResponse)
async def get_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific timesheet entry"""
    timesheet = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check access
    if current_user.role != "admin" and timesheet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return timesheet


@router.put("/{timesheet_id}", response_model=TimesheetResponse)
async def update_timesheet(
    timesheet_id: int,
    update: TimesheetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a timesheet entry"""
    timesheet = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check access
    if current_user.role != "admin" and timesheet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Cannot edit invoiced timesheets
    if timesheet.is_invoiced:
        raise HTTPException(status_code=400, detail="Cannot edit invoiced timesheet")
    
    # Update fields
    for field, value in update.dict(exclude_unset=True).items():
        setattr(timesheet, field, value)
    
    db.commit()
    db.refresh(timesheet)
    return timesheet


@router.delete("/{timesheet_id}")
async def delete_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a timesheet entry"""
    timesheet = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check access
    if current_user.role != "admin" and timesheet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Cannot delete invoiced timesheets
    if timesheet.is_invoiced:
        raise HTTPException(status_code=400, detail="Cannot delete invoiced timesheet")
    
    db.delete(timesheet)
    db.commit()
    return {"message": "Timesheet deleted"}
