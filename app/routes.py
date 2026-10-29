from fastapi import APIRouter, Path, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import StudentDB
from app.schemas import StudentCreate, StudentUpdate, StudentResponse

router = APIRouter()

SORT_FIELDS = ["marks", "age", "name"]
SORT_ORDER  = ["asc", "desc"]


@router.get("/student/{student_id}", response_model=StudentResponse, tags=["GET ROUTE"])
def get_student(
    student_id: str = Path(..., description="The Id of the student"),
    db: Session = Depends(get_db)
):
    student = db.get(StudentDB, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail=f"Student with the Id '{student_id}' not found")
    return student


@router.post("/CreateStudent", response_model=StudentResponse, status_code=201, tags=["POST ROUTES"])
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    if db.get(StudentDB, student.id):
        raise HTTPException(status_code=400, detail=f"Student with the Id '{student.id}' already exists")

    new_student = StudentDB(**student.model_dump())
    db.add(new_student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Email '{student.email}' is already used by another student")

    db.refresh(new_student)
    return new_student


@router.put("/UpdateStudent/{student_id}", tags=["PUT ROUTES"])
def update_student(
    student_update: StudentUpdate,
    student_id: str = Path(..., description="The Id of the student"),
    db: Session = Depends(get_db)
):
    student = db.get(StudentDB, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail=f"Student with the Id '{student_id}' does not exist")

    for key, value in student_update.model_dump(exclude_unset=True).items():
        setattr(student, key, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Email '{student.email}' is already used by another student")

    db.refresh(student)
    return student


@router.delete("/DeleteStudent/{student_id}", tags=["DELETE ROUTE"])
def delete_student(
    student_id: str = Path(..., description="The Id of the student"),
    db: Session = Depends(get_db)
):
    student = db.get(StudentDB, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail=f"Student with the Id '{student_id}' not found")

    db.delete(student)
    db.commit()
    return {"message": f"Student '{student_id}' deleted successfully"}


@router.get("/students", tags=["GET ROUTE"])
def get_all(
    course:   str | None = Query(None, description="Filter by course", examples=["Python"]),
    sort_by:  str | None = Query(None, description="Sort by marks, age or name"),
    order:    str        = Query("asc", description="asc or desc", examples=["desc"]),
    page:     int        = Query(1, ge=1, description="Page number (starts at 1)"),
    limit:    int        = Query(2, ge=1, le=100, description="Students per page (1-100)"),
    db: Session = Depends(get_db)
):
    if sort_by and sort_by not in SORT_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by '{sort_by}', choose from {SORT_FIELDS}")
    if order not in SORT_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid order '{order}', choose from {SORT_ORDER}")

    query = db.query(StudentDB)

    if course:
        query = query.filter(func.lower(StudentDB.course) == course.lower())

    total_students = query.count()

    if sort_by:
        column = getattr(StudentDB, sort_by)
        query = query.order_by(column.desc() if order == "desc" else column.asc())
    else:
        query = query.order_by(StudentDB.id)

    students = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "page": page,
        "limit": limit,
        "total_students": total_students,
        "students": students
    }
