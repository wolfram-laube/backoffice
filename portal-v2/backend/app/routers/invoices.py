"""
Invoices API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
import httpx
import os

from ..db.database import get_db
from ..models.models import User, Invoice, Timesheet, Customer
from ..auth.jwt import get_current_user, get_current_admin

router = APIRouter()


# Pydantic schemas
class InvoiceCreate(BaseModel):
    customer_id: int
    issue_date: date
    due_date: Optional[date] = None
    timesheet_ids: List[int]
    tax_rate: float = 20.0
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    customer_id: int
    issue_date: date
    due_date: Optional[date]
    subtotal: float
    tax_rate: float
    tax_amount: float
    total: float
    status: str
    pdf_url: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    pdf_url: Optional[str] = None


def generate_invoice_number(db: Session, issue_date: date) -> str:
    """Generate invoice number: BW-YYYY-NNN"""
    year = issue_date.year
    count = db.query(Invoice).filter(
        Invoice.invoice_number.like(f"BW-{year}-%")
    ).count()
    return f"BW-{year}-{count + 1:03d}"


async def trigger_pdf_generation(invoice_id: int, invoice_number: str):
    """Trigger GitLab Pipeline to generate PDF"""
    gitlab_token = os.getenv("GITLAB_TOKEN")
    project_id = os.getenv("GITLAB_PROJECT_ID", "77555895")
    
    if not gitlab_token:
        print(f"Warning: GITLAB_TOKEN not set, skipping PDF generation for {invoice_number}")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            # Trigger pipeline with invoice variable
            response = await client.post(
                f"https://gitlab.com/api/v4/projects/{project_id}/pipeline",
                headers={"PRIVATE-TOKEN": gitlab_token},
                json={
                    "ref": "main",
                    "variables": [
                        {"key": "INVOICE_ID", "value": str(invoice_id)},
                        {"key": "INVOICE_NUMBER", "value": invoice_number},
                    ]
                }
            )
            if response.status_code == 201:
                print(f"Pipeline triggered for invoice {invoice_number}")
            else:
                print(f"Failed to trigger pipeline: {response.text}")
    except Exception as e:
        print(f"Error triggering pipeline: {e}")


# API Endpoints
@router.get("/", response_model=List[InvoiceResponse])
async def list_invoices(
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all invoices"""
    query = db.query(Invoice)
    
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if status:
        query = query.filter(Invoice.status == status)
    
    return query.order_by(Invoice.issue_date.desc()).all()


@router.post("/", response_model=InvoiceResponse)
async def create_invoice(
    invoice_data: InvoiceCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)  # Admin only
):
    """Create a new invoice from timesheets"""
    # Verify customer
    customer = db.query(Customer).filter(Customer.id == invoice_data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get timesheets
    timesheets = db.query(Timesheet).filter(
        Timesheet.id.in_(invoice_data.timesheet_ids),
        Timesheet.customer_id == invoice_data.customer_id,
        Timesheet.is_invoiced == False,
        Timesheet.is_billable == True
    ).all()
    
    if not timesheets:
        raise HTTPException(status_code=400, detail="No billable timesheets found")
    
    # Calculate totals
    subtotal = sum(t.hours * (t.hourly_rate or 0) for t in timesheets)
    tax_amount = subtotal * (invoice_data.tax_rate / 100)
    total = subtotal + tax_amount
    
    # Generate invoice number
    invoice_number = generate_invoice_number(db, invoice_data.issue_date)
    
    # Create invoice
    invoice = Invoice(
        invoice_number=invoice_number,
        customer_id=invoice_data.customer_id,
        issue_date=invoice_data.issue_date,
        due_date=invoice_data.due_date,
        subtotal=subtotal,
        tax_rate=invoice_data.tax_rate,
        tax_amount=tax_amount,
        total=total,
        status="draft",
        notes=invoice_data.notes,
    )
    
    db.add(invoice)
    db.flush()  # Get ID
    
    # Mark timesheets as invoiced
    for timesheet in timesheets:
        timesheet.is_invoiced = True
        timesheet.invoice_id = invoice.id
    
    db.commit()
    db.refresh(invoice)
    
    # Trigger PDF generation in background
    background_tasks.add_task(trigger_pdf_generation, invoice.id, invoice.invoice_number)
    
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific invoice"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    update: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update invoice (status, notes, etc.)"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    for field, value in update.dict(exclude_unset=True).items():
        setattr(invoice, field, value)
    
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}")
async def cancel_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Cancel an invoice (can only cancel draft invoices)"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Can only cancel draft invoices")
    
    # Unmark timesheets
    timesheets = db.query(Timesheet).filter(Timesheet.invoice_id == invoice_id).all()
    for timesheet in timesheets:
        timesheet.is_invoiced = False
        timesheet.invoice_id = None
    
    invoice.status = "cancelled"
    db.commit()
    
    return {"message": "Invoice cancelled"}


@router.post("/{invoice_id}/regenerate-pdf")
async def regenerate_pdf(
    invoice_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Regenerate PDF for an invoice"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    background_tasks.add_task(trigger_pdf_generation, invoice.id, invoice.invoice_number)
    return {"message": "PDF generation triggered"}
